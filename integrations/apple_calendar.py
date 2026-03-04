"""Apple Calendar sync (macOS) for PerformOS v3."""
from __future__ import annotations

import sqlite3
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _to_iso_from_nsdate(nsdate) -> str | None:
    if nsdate is None:
        return None
    try:
        ts = float(nsdate.timeIntervalSince1970())
    except Exception:
        return None
    return datetime.fromtimestamp(ts).replace(microsecond=0).isoformat()


def _fetch_with_eventkit(days_ahead: int, calendar_name: str | None = None) -> tuple[list[dict], str | None]:
    """Fetch calendar events via EventKit (requires pyobjc on macOS)."""
    try:
        from Foundation import NSDate  # type: ignore
        from EventKit import EKEntityTypeEvent, EKEventStore  # type: ignore
    except Exception:
        return [], "eventkit_unavailable"

    store = EKEventStore.alloc().init()
    grant = {"ok": False, "err": None}
    done = threading.Event()

    def _completion(granted, error):
        grant["ok"] = bool(granted)
        if error is not None:
            grant["err"] = str(error)
        done.set()

    store.requestAccessToEntityType_completion_(EKEntityTypeEvent, _completion)
    done.wait(timeout=15)

    if not grant["ok"]:
        return [], grant["err"] or "calendar_permission_denied"

    start_dt = datetime.now()
    end_dt = start_dt + timedelta(days=days_ahead)
    start_date = NSDate.dateWithTimeIntervalSince1970_(start_dt.timestamp())
    end_date = NSDate.dateWithTimeIntervalSince1970_(end_dt.timestamp())

    calendars = list(store.calendarsForEntityType_(EKEntityTypeEvent) or [])
    if calendar_name:
        calendars = [c for c in calendars if str(c.title()) == calendar_name]

    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(
        start_date, end_date, calendars or None
    )
    events = list(store.eventsMatchingPredicate_(predicate) or [])

    parsed: list[dict] = []
    for ev in events:
        start_at = _to_iso_from_nsdate(ev.startDate())
        if not start_at:
            continue
        parsed.append(
            {
                "event_uid": str(ev.calendarItemIdentifier() or ev.eventIdentifier() or ""),
                "calendar_name": str(ev.calendar().title() if ev.calendar() else ""),
                "title": str(ev.title() or ""),
                "location": str(ev.location() or ""),
                "notes": str(ev.notes() or ""),
                "start_at": start_at,
                "end_at": _to_iso_from_nsdate(ev.endDate()),
                "is_all_day": 1 if bool(ev.isAllDay()) else 0,
                "source": "apple_calendar",
            }
        )

    parsed.sort(key=lambda x: x["start_at"])
    return parsed, None


def sync_apple_calendar(
    db_path: str | Path,
    days_ahead: int = 21,
    calendar_name: str | None = None,
) -> dict:
    """Sync upcoming Apple Calendar events into SQLite."""
    if sys.platform != "darwin":
        return {"enabled": False, "error": "apple_calendar_macos_only", "events_synced": 0}

    events, error = _fetch_with_eventkit(days_ahead=days_ahead, calendar_name=calendar_name)
    if error:
        return {"enabled": False, "error": error, "events_synced": 0}

    conn = sqlite3.connect(str(db_path))
    now = _now_iso()
    start_cutoff = datetime.now().replace(microsecond=0).isoformat()
    end_cutoff = (datetime.now() + timedelta(days=days_ahead + 2)).replace(microsecond=0).isoformat()

    conn.execute(
        """
        DELETE FROM calendar_events
        WHERE source='apple_calendar' AND start_at>=? AND start_at<=?
        """,
        (start_cutoff, end_cutoff),
    )

    inserted = 0
    for ev in events:
        conn.execute(
            """
            INSERT OR REPLACE INTO calendar_events
            (event_uid, calendar_name, title, location, notes,
             start_at, end_at, is_all_day, source, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                ev["event_uid"],
                ev["calendar_name"],
                ev["title"],
                ev["location"],
                ev["notes"],
                ev["start_at"],
                ev.get("end_at"),
                int(ev.get("is_all_day", 0)),
                ev.get("source", "apple_calendar"),
                now,
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()

    return {
        "enabled": True,
        "error": None,
        "events_synced": inserted,
        "window_days": days_ahead,
        "synced_at": now,
    }


def get_upcoming_events(db_path: str | Path, days_ahead: int = 21, limit: int = 40) -> list[dict]:
    """Return upcoming agenda events for dashboard display."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    now = datetime.now().replace(microsecond=0).isoformat()
    end = (datetime.now() + timedelta(days=days_ahead)).replace(microsecond=0).isoformat()

    rows = conn.execute(
        """
        SELECT event_uid, calendar_name, title, location, notes,
               start_at, end_at, is_all_day, source
        FROM calendar_events
        WHERE start_at >= ? AND start_at <= ?
        ORDER BY start_at ASC
        LIMIT ?
        """,
        (now, end, int(limit)),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
