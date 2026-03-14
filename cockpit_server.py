#!/usr/bin/env python3
"""PerformOS local cockpit server (dashboard + planner API)."""

from __future__ import annotations

import argparse
import json
import mimetypes
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from analytics import muscle_groups, planner, training_load
from integrations.apple_calendar import diagnose_apple_calendar, sync_apple_calendar
from pipeline.schema import get_connection, migrate_db


def _json_bytes(obj: dict | list) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


class CockpitHandler(BaseHTTPRequestHandler):
    dashboard_path: Path = Path("reports/dashboard.html")
    db_path: Path = Path("athlete.db")
    planner_window_days: int = 120
    api_token: str = ""

    def _send_json(self, status: int, payload: dict | list) -> None:
        data = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404, "Not Found")
            return
        ctype, _ = mimetypes.guess_type(str(path))
        raw = path.read_bytes()
        if path.suffix.lower() in (".html", ".htm"):
            try:
                token_js = json.dumps(self.api_token, ensure_ascii=False)
                raw = raw.decode("utf-8").replace("__API_TOKEN_JS__", token_js).encode("utf-8")
            except Exception:
                pass
        self.send_response(200)
        self.send_header("Content-Type", ctype or "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _parse_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 64 * 1024:
            return {}
        raw = self.rfile.read(length) if length > 0 else b"{}"
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _require_api_token(self) -> bool:
        expected = (self.api_token or "").strip()
        if not expected:
            return True
        got = (self.headers.get("X-PerformOS-Token") or "").strip()
        return got == expected

    def _auth_or_401(self) -> bool:
        if self._require_api_token():
            return True
        self._send_json(401, {"ok": False, "error": "unauthorized"})
        return False

    def _validate_event_bounds(self, start_at: str, end_at: str) -> tuple[bool, str]:
        if not start_at or not end_at:
            return False, "missing_datetime"
        try:
            s = datetime.fromisoformat(str(start_at).replace("Z", ""))
            e = datetime.fromisoformat(str(end_at).replace("Z", ""))
        except Exception:
            return False, "invalid_datetime"
        if e <= s:
            return False, "end_before_start"
        # Guard absurd durations
        if (e - s).total_seconds() > 60 * 60 * 24 * 3:
            return False, "duration_too_long"
        return True, ""

    def _window_bounds(
        self, start_q: str | None = None, end_q: str | None = None
    ) -> tuple[str, str]:
        if start_q and end_q:
            return start_q, end_q
        start = (date.today() - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00")
        end = (date.today() + timedelta(days=self.planner_window_days)).strftime(
            "%Y-%m-%dT23:59:59"
        )
        return start, end

    def _read_events(self, start_at: str | None = None, end_at: str | None = None) -> list[dict]:
        s, e = self._window_bounds(start_at, end_at)
        return planner.get_planner_events_db(self.db_path, start_at=s, end_at=e)

    def _sync_calendar_soft(self) -> None:
        try:
            sync_apple_calendar(self.db_path, days_ahead=self.planner_window_days)
        except Exception:
            pass

    def _build_artifact(self) -> dict:
        """Aggregate all analytics data into a single artifact payload."""
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        today = date.today()

        # ── Training load (PMC, ACWR, readiness) ──
        daily_tss = training_load.build_daily_tss(conn)
        pmc_series = training_load.compute_pmc(daily_tss, end_date=today)
        today_pmc = pmc_series[-1] if pmc_series else {"ctl": 0, "atl": 0, "tsb": 0, "tss": 0}
        acwr_data = training_load.compute_acwr(daily_tss, end_date=today)

        # ── Health metrics ──
        health = training_load.get_health_metrics(conn)

        # ── Readiness score ──
        readiness = training_load.compute_wakeboard_score(
            hrv_val=health.get("hrv"),
            hrv_baseline=health.get("hrv_baseline"),
            sleep_h=health.get("sleep_h"),
            acwr_val=acwr_data["acwr"],
            rhr_val=health.get("rhr"),
            rhr_baseline=health.get("rhr_baseline"),
            body_battery=health.get("body_battery"),
            freshness={
                "hrv": health.get("hrv_freshness", 1.0),
                "sleep": health.get("sleep_freshness", 1.0),
                "rhr": health.get("rhr_freshness", 1.0),
                "body_battery": health.get("body_battery_freshness", 1.0),
            },
        )

        # ── Running ──
        running = training_load.analyze_running(conn, weeks=12)
        if running:
            running["estimated_10k"] = training_load.estimate_10k_time(
                base_10k_min=running.get("pred_10k_base_min"),
                avg_pace_mpk=running.get("avg_pace"),
                ctl=float(today_pmc.get("ctl", 0) or 0),
                acwr=float(acwr_data.get("acwr", 0) or 0),
                readiness_score=float(readiness.get("score", 0) or 0),
            )

        # ── Muscle groups ──
        muscles_data = muscle_groups.run(db_path=self.db_path, weeks=4, verbose=False)

        # Build opacity map for muscle zones (0-1 scale based on volume vs target)
        muscle_zones: dict[str, float] = {}
        cum = muscles_data.get("cumulative", {})
        for mg, targets in muscle_groups.VOLUME_TARGETS.items():
            spw = float(cum.get(mg, {}).get("sets_per_week", 0))
            hyp = float(targets["hyper"])
            muscle_zones[mg] = round(min(1.0, spw / hyp) if hyp > 0 else 0.0, 2)

        # ── Recent activities ──
        recent_rows = conn.execute("""
            SELECT id, source, type, name, started_at, duration_s,
                   distance_m, calories, avg_hr, tss_proxy
            FROM activities ORDER BY started_at DESC LIMIT 15
        """).fetchall()

        def _fmt_duration(s: int | None) -> str:
            if not s:
                return "—"
            h, rem = divmod(int(s), 3600)
            m, sec = divmod(rem, 60)
            return f"{h}h{m:02d}" if h else f"{m}m{sec:02d}s"

        recent_activities = [
            {
                "id": r[0],
                "source": r[1],
                "type": r[2],
                "name": r[3],
                "started_at": r[4],
                "duration_s": r[5],
                "duration_str": _fmt_duration(r[5]),
                "distance_m": r[6],
                "distance_km": round(r[6] / 1000, 2) if r[6] else None,
                "calories": r[7],
                "avg_hr": r[8],
                "tss": r[9],
            }
            for r in recent_rows
        ]

        # ── Activity hours per week (last 12 weeks) ──
        hours_rows = conn.execute("""
            SELECT strftime('%Y-W%W', started_at) AS week,
                   COALESCE(SUM(duration_s), 0) / 3600.0 AS hours
            FROM activities
            WHERE started_at >= date('now', '-84 days')
            GROUP BY week
            ORDER BY week
        """).fetchall()
        hours_series = [{"week": r[0], "hours": round(r[1], 1)} for r in hours_rows]

        # ── Week summary (current week events) ──
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%dT00:00:00")
        week_end = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%dT23:59:59")
        events = planner.get_planner_events_db(
            self.db_path, start_at=week_start, end_at=week_end
        )
        board = planner.get_board_tasks_db(self.db_path)

        # Category hour sums from events
        cat_hours: dict[str, float] = {}
        for ev in events:
            cat = ev.get("category", "autre")
            start = ev.get("start_at", "")
            end = ev.get("end_at", "")
            try:
                s = datetime.fromisoformat(start.replace("Z", ""))
                e = datetime.fromisoformat(end.replace("Z", ""))
                dur_h = (e - s).total_seconds() / 3600
            except Exception:
                dur_h = 0
            cat_hours[cat] = cat_hours.get(cat, 0) + dur_h

        week_summary = {
            "sante_h": round(cat_hours.get("sport", 0) + cat_hours.get("yoga", 0), 1),
            "travail_h": round(cat_hours.get("travail", 0), 1),
            "relationnel_h": round(cat_hours.get("social", 0), 1),
            "apprentissage_h": round(cat_hours.get("formation", 0), 1),
            "autre_h": round(cat_hours.get("autre", 0) + cat_hours.get("lecon", 0), 1),
        }
        week_summary["total_h"] = round(sum(week_summary.values()), 1)

        # ── PMC series: trim to last 90 days for the artifact ──
        pmc_trimmed = pmc_series[-90:] if len(pmc_series) > 90 else pmc_series

        # ── Totals ──
        total_acts = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        total_km = conn.execute(
            "SELECT COALESCE(SUM(distance_m),0)/1000 FROM activities WHERE distance_m>0"
        ).fetchone()[0]
        strength_count = conn.execute("SELECT COUNT(*) FROM strength_sessions").fetchone()[0]

        conn.close()

        return {
            "ok": True,
            "generated_at": datetime.now().isoformat(),
            "health": health,
            "readiness": readiness,
            "acwr": acwr_data,
            "pmc": {
                "current": {
                    "ctl": today_pmc.get("ctl", 0),
                    "atl": today_pmc.get("atl", 0),
                    "tsb": today_pmc.get("tsb", 0),
                },
                "series": pmc_trimmed,
            },
            "running": running or {},
            "muscles": {
                "zones": muscle_zones,
                "cumulative": cum,
                "weekly_volume": muscles_data.get("weekly_volume", {}),
                "alerts": muscles_data.get("imbalances", []),
                "score": muscles_data.get("muscle_score", 0),
                "targets": {k: dict(v) for k, v in muscle_groups.VOLUME_TARGETS.items()},
                "top_exercises": muscles_data.get("top_exercises", {}),
                "recent_sessions": muscles_data.get("recent_sessions", []),
            },
            "week": {
                "start": week_start[:10],
                "summary": week_summary,
                "events": events,
                "board": board,
            },
            "activities": {
                "recent": recent_activities,
                "hours_series": hours_series,
                "total_count": total_acts,
                "total_km": round(total_km, 0),
                "strength_sessions": strength_count,
            },
        }

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        if path in ("/", "/index.html", "/dashboard"):
            self._send_file(self.dashboard_path)
            return

        if path == "/api/artifact":
            try:
                payload = self._build_artifact()
                self._send_json(200, payload)
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return

        if path == "/api/planner/events":
            q = parse_qs(url.query)
            start_at = (q.get("start") or [None])[0]
            end_at = (q.get("end") or [None])[0]
            events = self._read_events(start_at=start_at, end_at=end_at)
            self._send_json(200, {"ok": True, "events": events})
            return

        if path == "/api/planner/board":
            tasks = planner.get_board_tasks_db(self.db_path)
            self._send_json(200, {"ok": True, "tasks": tasks})
            return

        if path == "/api/planner/health":
            self._send_json(200, {"ok": True, "status": "up"})
            return

        # Calendar endpoints
        if path == "/api/calendar/status":
            status = diagnose_apple_calendar(self.db_path)
            self._send_json(200, {"ok": True, "calendar": status})
            return

        if path == "/api/calendar/events":
            if not self._auth_or_401():
                return
            q = parse_qs(url.query)
            days = int((q.get("days") or ["30"])[0])
            events = self._get_calendar_events(days=days)
            self._send_json(200, {"ok": True, "events": events})
            return

        if path == "/api/calendar/sync":
            if not self._auth_or_401():
                return
            q = parse_qs(url.query)
            days = int((q.get("days") or ["30"])[0])
            result = sync_apple_calendar(db_path=self.db_path, days_ahead=days)
            self._send_json(200, {"ok": result.get("enabled", False), "sync": result})
            return

        # Public endpoint — no auth needed — returns calendar permission state
        if path == "/api/planner/calendar/status":
            diag = diagnose_apple_calendar()  # no db_path for fast probe
            permission = diag.get("permission", "unknown")
            error = diag.get("error")
            self._send_json(
                200,
                {
                    "ok": diag.get("enabled", False),
                    "permission": permission,
                    "error": error,
                    "eventkit": diag.get("eventkit", "unknown"),
                    "calendars_count": diag.get("calendars_count", 0),
                    "default_calendar": diag.get("default_calendar"),
                },
            )
            return

        if path == "/api/planner/calendar/debug":
            if not self._auth_or_401():
                return
            self._send_json(
                200, {"ok": True, "debug": diagnose_apple_calendar(db_path=self.db_path)}
            )
            return

        if path == "/api/planner/agent/capabilities":
            self._send_json(
                200,
                {
                    "ok": True,
                    "tools": [
                        {
                            "name": "create_tasks_batch",
                            "description": "Crée plusieurs tâches planner en une requête",
                            "input_example": {
                                "tasks": [
                                    {
                                        "title": "10km tempo",
                                        "type": "cardio",
                                        "week_ref": "next_week",
                                        "weekday": "mardi",
                                        "time": "07:30",
                                        "duration_min": 60,
                                        "sync_apple": True,
                                    }
                                ]
                            },
                        }
                    ],
                    "week_ref_values": ["this_week", "next_week", "week_plus_2"],
                    "weekday_values": [
                        "lundi",
                        "mardi",
                        "mercredi",
                        "jeudi",
                        "vendredi",
                        "samedi",
                        "dimanche",
                    ],
                },
            )
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path
        body = self._parse_json_body()

        if path == "/api/planner/tasks":
            if not self._auth_or_401():
                return
            title = str(body.get("title") or "").strip() or "Tâche"
            title = title[:120]
            task_type = str(body.get("type") or "autre")
            type_map = {
                "cardio": "sport",
                "musculation": "sport",
                "mobilite": "yoga",
                "sport_libre": "sport",
                "travail": "travail",
                "apprentissage": "formation",
                "formation": "formation",
                "relationnel": "social",
                "social": "social",
                "yoga": "yoga",
                "autre": "autre",
            }
            category = planner.normalize_category(
                body.get("category") or type_map.get(task_type, "autre")
            )
            triage_status = planner.normalize_triage_status(body.get("triage_status"))
            notes = body.get("notes")
            if notes is not None:
                notes = str(notes)[:5000]

            start_at = body.get("start_at") or body.get("scheduled_start")
            end_at = body.get("end_at") or body.get("scheduled_end")
            scheduled = bool(body.get("scheduled", False))
            scheduled_date = body.get("scheduled_date")
            last_bucket = body.get("last_bucket_before_scheduling")

            # Si dates fournies via date+heure
            if not start_at and body.get("task_date"):
                task_date = str(body.get("task_date") or date.today())
                task_time = str(body.get("task_time") or body.get("time") or "09:00:00")
                dur = int(body.get("duration_min") or body.get("duration") or 60)
                start_at, end_at = planner.parse_task_datetime(task_date, task_time, dur)
                scheduled = True

            # Validation si planifié avec dates
            if start_at and end_at:
                ok_bounds, err = self._validate_event_bounds(str(start_at), str(end_at))
                if not ok_bounds:
                    self._send_json(400, {"ok": False, "error": err})
                    return

            sync_apple = bool(body.get("sync_apple", bool(start_at)))
            calendar_name = body.get("calendar_name")

            created = planner.add_task(
                db_path=self.db_path,
                title=title,
                category=category,
                start_at=str(start_at) if start_at else None,
                end_at=str(end_at) if end_at else None,
                notes=notes,
                sync_to_apple=sync_apple,
                apple_calendar_name=calendar_name,
                triage_status=triage_status,
                scheduled=scheduled,
                scheduled_date=scheduled_date or (str(start_at)[:10] if start_at else None),
                scheduled_start=str(start_at) if start_at else None,
                scheduled_end=str(end_at) if end_at else None,
                last_bucket_before_scheduling=last_bucket,
            )
            if sync_apple:
                self._sync_calendar_soft()

            events = self._read_events()
            board = planner.get_board_tasks_db(self.db_path)
            self._send_json(201, {"ok": True, "created": created, "events": events, "board": board})
            return

        if path == "/api/planner/tasks/batch":
            if not self._auth_or_401():
                return
            tasks = body.get("tasks")
            if not isinstance(tasks, list) or not tasks:
                self._send_json(400, {"ok": False, "error": "missing_tasks"})
                return
            if len(tasks) > 100:
                self._send_json(400, {"ok": False, "error": "too_many_tasks"})
                return

            defaults = body.get("defaults") or {}
            default_sync_apple = bool(defaults.get("sync_apple", True))
            default_calendar_name = defaults.get("calendar_name")
            res = planner.add_tasks_batch(
                db_path=self.db_path,
                tasks=tasks,
                default_sync_apple=default_sync_apple,
                default_calendar_name=default_calendar_name,
            )
            if default_sync_apple:
                self._sync_calendar_soft()
            events = self._read_events()
            status = 201 if res.get("ok") else 207
            self._send_json(status, {"ok": bool(res.get("ok")), "result": res, "events": events})
            return

        if path == "/api/planner/calendar/sync":
            if not self._auth_or_401():
                return
            sync_result = {}
            try:
                sync_result = sync_apple_calendar(self.db_path, days_ahead=self.planner_window_days)
            except Exception:
                pass
            events = self._read_events()
            self._send_json(200, {"ok": True, "events": events, "sync": sync_result})
            return

        if path == "/api/planner/calendar/push":
            if not self._auth_or_401():
                return
            push = planner.sync_pending_tasks_to_apple(
                db_path=self.db_path,
                limit=300,
            )
            self._sync_calendar_soft()
            events = self._read_events()
            self._send_json(200, {"ok": bool(push.get("ok")), "result": push, "events": events})
            return

        # Direct calendar management endpoints
        if path == "/api/calendar/create":
            if not self._auth_or_401():
                return
            from integrations.apple_calendar import create_apple_calendar_event

            title = str(body.get("title", "")).strip()
            start_at = body.get("start_at")
            end_at = body.get("end_at")
            notes = body.get("notes")
            location = body.get("location")
            calendar_name = body.get("calendar_name")

            if not title or not start_at or not end_at:
                self._send_json(400, {"ok": False, "error": "missing_required_fields"})
                return

            result = create_apple_calendar_event(
                title=title,
                start_at=start_at,
                end_at=end_at,
                notes=notes,
                location=location,
                calendar_name=calendar_name,
            )

            if result.get("enabled"):
                # Re-sync pour mettre à jour la DB
                sync_apple_calendar(db_path=self.db_path, days_ahead=30)
                events = self._get_calendar_events()
                self._send_json(201, {"ok": True, "created": result, "events": events})
            else:
                self._send_json(400, {"ok": False, "error": result.get("error", "creation_failed")})
            return

        self.send_error(404, "Not Found")

    def do_PATCH(self):
        url = urlparse(self.path)
        path = url.path
        body = self._parse_json_body()

        if path.startswith("/api/planner/tasks/"):
            if not self._auth_or_401():
                return
            task_id_str = path.rsplit("/", 1)[-1]
            try:
                task_id = int(task_id_str)
            except ValueError:
                self._send_json(400, {"ok": False, "error": "invalid_task_id"})
                return

            notes = body.get("notes") if "notes" in body else None
            if notes is not None:
                notes = str(notes)[:5000]

            sync_apple = bool(body.get("sync_apple", True))

            # Préparer les champs de planning
            start_at = body.get("start_at") or body.get("scheduled_start")
            end_at = body.get("end_at") or body.get("scheduled_end")
            scheduled = body.get("scheduled")
            sch_date = body.get("scheduled_date")
            sch_start = body.get("scheduled_start") or start_at
            sch_end = body.get("scheduled_end") or end_at
            last_bucket = body.get("last_bucket_before_scheduling")
            triage_status = body.get("triage_status")

            # Validation si dates fournies
            if start_at and end_at:
                ok_bounds, err = self._validate_event_bounds(str(start_at), str(end_at))
                if not ok_bounds:
                    self._send_json(400, {"ok": False, "error": err})
                    return

            res = planner.update_task(
                db_path=self.db_path,
                task_id=task_id,
                title=body.get("title"),
                category=body.get("category"),
                start_at=str(start_at) if start_at else None,
                end_at=str(end_at) if end_at else None,
                notes=notes,
                sync_apple=sync_apple,
                triage_status=triage_status,
                scheduled=bool(scheduled) if scheduled is not None else None,
                scheduled_date=sch_date or (str(start_at)[:10] if start_at else None),
                scheduled_start=str(sch_start) if sch_start else None,
                scheduled_end=str(sch_end) if sch_end else None,
                last_bucket_before_scheduling=last_bucket,
                calendar_name=body.get("calendar_name"),
            )
            if not res.get("ok"):
                self._send_json(404, {"ok": False, "error": res.get("error", "task_not_found")})
                return
            if sync_apple:
                self._sync_calendar_soft()
            events = self._read_events()
            board = planner.get_board_tasks_db(self.db_path)
            self._send_json(200, {"ok": True, "result": res, "events": events, "board": board})
            return

        if path.startswith("/api/planner/apple/"):
            if not self._auth_or_401():
                return
            uid = unquote(path.rsplit("/", 1)[-1])
            ok, err = self._validate_event_bounds(
                str(body.get("start_at") or ""), str(body.get("end_at") or "")
            )
            if not ok:
                self._send_json(400, {"ok": False, "error": err})
                return
            res = planner.update_apple_only_event(
                event_uid=uid,
                title=str(body.get("title") or "Événement")[:120],
                start_at=str(body.get("start_at") or ""),
                end_at=str(body.get("end_at") or ""),
                notes=body.get("notes"),
            )
            self._sync_calendar_soft()
            events = self._read_events()
            self._send_json(200, {"ok": bool(res.get("enabled")), "result": res, "events": events})
            return

        # Calendar event modification
        if path.startswith("/api/calendar/events/"):
            if not self._auth_or_401():
                return
            unquote(path.rsplit("/", 1)[-1])

            # Pour l'instant, on ne permet que la modification via planner
            # TODO: Implémenter modification directe d'événements calendrier
            self._send_json(400, {"ok": False, "error": "modification_not_implemented"})
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self):
        url = urlparse(self.path)
        path = url.path

        if path.startswith("/api/planner/tasks/"):
            if not self._auth_or_401():
                return
            task_id_str = path.rsplit("/", 1)[-1]
            try:
                task_id = int(task_id_str)
            except ValueError:
                self._send_json(400, {"ok": False, "error": "invalid_task_id"})
                return
            res = planner.delete_task(self.db_path, task_id=task_id, sync_apple=True)
            self._sync_calendar_soft()
            events = self._read_events()
            board = planner.get_board_tasks_db(self.db_path)
            self._send_json(
                200, {"ok": bool(res.get("ok")), "result": res, "events": events, "board": board}
            )
            return

        if path.startswith("/api/planner/apple/"):
            if not self._auth_or_401():
                return
            uid = unquote(path.rsplit("/", 1)[-1])
            res = planner.delete_apple_only_event(uid, db_path=self.db_path)
            self._sync_calendar_soft()
            events = self._read_events()
            self._send_json(200, {"ok": bool(res.get("enabled")), "result": res, "events": events})
            return

        self.send_error(404, "Not Found")

    def _get_calendar_events(self, days: int = 30) -> list[dict]:
        """Get calendar events from DB for the next N days."""
        from integrations.apple_calendar import get_upcoming_events

        try:
            return get_upcoming_events(db_path=self.db_path, days_ahead=days, limit=100)
        except Exception:
            return []


def serve(
    dashboard_path: Path,
    db_path: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    api_token: str = "",
    auto_port_fallback: bool = True,
) -> None:
    CockpitHandler.dashboard_path = dashboard_path
    CockpitHandler.db_path = db_path
    CockpitHandler.api_token = api_token

    # Migration DB au démarrage
    try:
        _conn = get_connection(db_path)
        migrate_db(_conn)
        _conn.close()
    except Exception as _e:
        print(f"⚠️  Migration DB: {_e}")

    candidate_ports = [port]
    if auto_port_fallback:
        candidate_ports.extend([port + i for i in range(1, 10)])

    httpd = None
    chosen_port = None
    last_err = None
    for p in candidate_ports:
        try:
            httpd = ThreadingHTTPServer((host, p), CockpitHandler)
            chosen_port = p
            break
        except OSError as e:
            last_err = e
            if e.errno not in (48, 98):  # macOS / Linux address in use
                raise
            continue

    if httpd is None or chosen_port is None:
        if last_err:
            raise last_err
        raise OSError("unable_to_bind_port")

    if chosen_port != port:
        print(f"⚠️  Port {port} occupé — fallback auto sur {chosen_port}")

    print(f"🚀 PerformOS cockpit server: http://{host}:{chosen_port}")
    print(f"   Dashboard: {dashboard_path}")
    print(f"   DB: {db_path}")
    if api_token:
        print("   API write protection: enabled")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def main() -> None:
    p = argparse.ArgumentParser(description="PerformOS local cockpit server")
    p.add_argument("--dashboard", required=True, help="Path to generated dashboard html")
    p.add_argument("--db", required=True, help="Path to SQLite DB")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--api-token", default="", help="Write-protection token for planner API")
    args = p.parse_args()

    serve(
        dashboard_path=Path(args.dashboard),
        db_path=Path(args.db),
        host=args.host,
        port=args.port,
        api_token=args.api_token,
    )


if __name__ == "__main__":
    main()
