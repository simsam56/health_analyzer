#!/usr/bin/env python3
"""PerformOS local cockpit server (dashboard + planner API)."""
from __future__ import annotations

import argparse
import json
import mimetypes
import sqlite3
from datetime import date, timedelta
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

    def _send_json(self, status: int, payload: dict | list) -> None:
        data = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404, "Not Found")
            return
        ctype, _ = mimetypes.guess_type(str(path))
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _parse_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

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

        self.send_error(404, "Not Found")

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path
        body = self._parse_json_body()

        if path == "/api/planner/tasks":
            title = str(body.get("title") or "").strip() or "Activité"
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

            sync_apple = bool(body.get("sync_apple", True))
            calendar_name = body.get("calendar_name")
            notes = body.get("notes")

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

        if path == "/api/planner/calendar/sync":
            self._sync_calendar_soft()
            events = self._read_events()
            self._send_json(200, {"ok": True, "events": events})
            return

        self.send_error(404, "Not Found")

    def do_PATCH(self):
        url = urlparse(self.path)
        path = url.path
        body = self._parse_json_body()

        if path.startswith("/api/planner/tasks/"):
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

            title = str(body.get("title") if body.get("title") is not None else row["title"])
            category = planner.normalize_category(body.get("category") if body.get("category") is not None else row["category"])
            start_at = str(body.get("start_at") if body.get("start_at") is not None else row["start_at"])
            end_at = str(body.get("end_at") if body.get("end_at") is not None else row["end_at"])
            notes = body.get("notes") if "notes" in body else row["notes"]
            sync_apple = bool(body.get("sync_apple", True))

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
            uid = unquote(path.rsplit("/", 1)[-1])
            res = planner.update_apple_only_event(
                event_uid=uid,
                title=str(body.get("title") or "Événement"),
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
            uid = unquote(path.rsplit("/", 1)[-1])
            res = planner.delete_apple_only_event(uid)
            self._sync_calendar_soft()
            events = self._read_events()
            self._send_json(200, {"ok": bool(res.get("enabled")), "result": res, "events": events})
            return

        self.send_error(404, "Not Found")


def serve(dashboard_path: Path, db_path: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    CockpitHandler.dashboard_path = dashboard_path
    CockpitHandler.db_path = db_path

    httpd = ThreadingHTTPServer((host, port), CockpitHandler)
    print(f"🚀 PerformOS cockpit server: http://{host}:{port}")
    print(f"   Dashboard: {dashboard_path}")
    print(f"   DB: {db_path}")
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
    args = p.parse_args()

    serve(
        dashboard_path=Path(args.dashboard),
        db_path=Path(args.db),
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
