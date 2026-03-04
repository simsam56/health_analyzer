#!/usr/bin/env python3
"""PerformOS local cockpit server (dashboard + planner API)."""
from __future__ import annotations

import argparse
import json
import mimetypes
import sqlite3
from datetime import date, timedelta, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote

from analytics import planner
from integrations.apple_calendar import sync_apple_calendar


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

    def _window_bounds(self, start_q: str | None = None, end_q: str | None = None) -> tuple[str, str]:
        if start_q and end_q:
            return start_q, end_q
        start = (date.today() - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00")
        end = (date.today() + timedelta(days=self.planner_window_days)).strftime("%Y-%m-%dT23:59:59")
        return start, end

    def _read_events(self, start_at: str | None = None, end_at: str | None = None) -> list[dict]:
        s, e = self._window_bounds(start_at, end_at)
        return planner.get_planner_events_db(self.db_path, start_at=s, end_at=e)

    def _sync_calendar_soft(self) -> None:
        try:
            sync_apple_calendar(self.db_path, days_ahead=self.planner_window_days)
        except Exception:
            pass

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        if path in ("/", "/index.html", "/dashboard"):
            self._send_file(self.dashboard_path)
            return

        if path == "/api/planner/events":
            q = parse_qs(url.query)
            start_at = (q.get("start") or [None])[0]
            end_at = (q.get("end") or [None])[0]
            events = self._read_events(start_at=start_at, end_at=end_at)
            self._send_json(200, {"ok": True, "events": events})
            return

        if path == "/api/planner/health":
            self._send_json(200, {"ok": True, "status": "up"})
            return

        if path == "/api/planner/agent/capabilities":
            self._send_json(200, {
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
                                    "sync_apple": True
                                }
                            ]
                        }
                    }
                ],
                "week_ref_values": ["this_week", "next_week", "week_plus_2"],
                "weekday_values": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
            })
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path
        body = self._parse_json_body()

        if path == "/api/planner/tasks":
            if not self._auth_or_401():
                return
            title = str(body.get("title") or "").strip() or "Activité"
            title = title[:120]
            task_type = str(body.get("type") or "autre")
            type_map = {
                "cardio": "sante",
                "musculation": "sante",
                "mobilite": "sante",
                "sport_libre": "sante",
                "travail": "travail",
                "apprentissage": "apprentissage",
                "relationnel": "relationnel",
                "autre": "autre",
            }
            category = planner.normalize_category(body.get("category") or type_map.get(task_type, "autre"))

            start_at = body.get("start_at")
            end_at = body.get("end_at")
            if not start_at or not end_at:
                task_date = str(body.get("task_date") or body.get("date") or date.today())
                task_time = str(body.get("task_time") or body.get("time") or "09:00:00")
                dur = int(body.get("duration_min") or body.get("duration") or 60)
                start_at, end_at = planner.parse_task_datetime(task_date, task_time, dur)
            ok, err = self._validate_event_bounds(str(start_at), str(end_at))
            if not ok:
                self._send_json(400, {"ok": False, "error": err})
                return

            sync_apple = bool(body.get("sync_apple", True))
            calendar_name = body.get("calendar_name")
            notes = body.get("notes")
            if notes is not None:
                notes = str(notes)[:5000]

            created = planner.add_task(
                db_path=self.db_path,
                title=title,
                category=category,
                start_at=str(start_at),
                end_at=str(end_at),
                notes=notes,
                sync_to_apple=sync_apple,
                apple_calendar_name=calendar_name,
            )
            if sync_apple:
                self._sync_calendar_soft()

            events = self._read_events()
            self._send_json(201, {"ok": True, "created": created, "events": events})
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
            self._sync_calendar_soft()
            events = self._read_events()
            self._send_json(200, {"ok": True, "events": events})
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

            # Read existing task for partial updates
            conn = planner.connect_db(self.db_path)
            row = conn.execute(
                "SELECT id, title, category, start_at, end_at, notes FROM planner_tasks WHERE id=?",
                (task_id,),
            ).fetchone()
            conn.close()
            if not row:
                self._send_json(404, {"ok": False, "error": "task_not_found"})
                return

            title = str(body.get("title") if body.get("title") is not None else row["title"])[:120]
            category = planner.normalize_category(body.get("category") if body.get("category") is not None else row["category"])
            start_at = str(body.get("start_at") if body.get("start_at") is not None else row["start_at"])
            end_at = str(body.get("end_at") if body.get("end_at") is not None else row["end_at"])
            notes = body.get("notes") if "notes" in body else row["notes"]
            if notes is not None:
                notes = str(notes)[:5000]
            sync_apple = bool(body.get("sync_apple", True))
            ok, err = self._validate_event_bounds(start_at, end_at)
            if not ok:
                self._send_json(400, {"ok": False, "error": err})
                return

            res = planner.update_task(
                db_path=self.db_path,
                task_id=task_id,
                title=title,
                category=category,
                start_at=start_at,
                end_at=end_at,
                notes=notes,
                sync_apple=sync_apple,
            )
            if sync_apple:
                self._sync_calendar_soft()
            events = self._read_events()
            self._send_json(200, {"ok": bool(res.get("ok")), "result": res, "events": events})
            return

        if path.startswith("/api/planner/apple/"):
            if not self._auth_or_401():
                return
            uid = unquote(path.rsplit("/", 1)[-1])
            ok, err = self._validate_event_bounds(str(body.get("start_at") or ""), str(body.get("end_at") or ""))
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
            self._send_json(200, {"ok": bool(res.get("ok")), "result": res, "events": events})
            return

        if path.startswith("/api/planner/apple/"):
            if not self._auth_or_401():
                return
            uid = unquote(path.rsplit("/", 1)[-1])
            res = planner.delete_apple_only_event(uid)
            self._sync_calendar_soft()
            events = self._read_events()
            self._send_json(200, {"ok": bool(res.get("enabled")), "result": res, "events": events})
            return

        self.send_error(404, "Not Found")


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
