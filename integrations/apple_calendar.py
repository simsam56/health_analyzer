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


def _nsdate_from_iso(iso_ts: str):
    try:
        from Foundation import NSDate  # type: ignore
        dt = datetime.fromisoformat(iso_ts[:19])
        return NSDate.dateWithTimeIntervalSince1970_(dt.timestamp())
    except Exception:
        return None


def _get_store_and_access():
    try:
        from EventKit import EKEntityTypeEvent, EKEventStore  # type: ignore
    except Exception:
        return None, None, "eventkit_unavailable"

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
        return None, None, grant["err"] or "calendar_permission_denied"
    return store, EKEntityTypeEvent, None


def _fetch_with_eventkit(days_ahead: int, calendar_name: str | None = None) -> tuple[list[dict], str | None]:
    """Fetch calendar events via EventKit (requires pyobjc on macOS)."""
    try:
        from Foundation import NSDate  # type: ignore
    except Exception:
        return [], "eventkit_unavailable"

    store, EKEntityTypeEvent, err = _get_store_and_access()
    if err:
        return [], err

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


def create_apple_calendar_event(
    title: str,
    start_at: str,
    end_at: str,
    notes: str | None = None,
    location: str | None = None,
    calendar_name: str | None = None,
) -> dict:
    """Create an event in Apple Calendar via EventKit."""
    if sys.platform != "darwin":
        return {"enabled": False, "error": "apple_calendar_macos_only"}

    try:
        from EventKit import EKEvent, EKSpanThisEvent  # type: ignore
    except Exception:
        return {"enabled": False, "error": "eventkit_unavailable"}

    store, entity_type, err = _get_store_and_access()
    if err:
        return {"enabled": False, "error": err}

    start_date = _nsdate_from_iso(start_at)
    end_date = _nsdate_from_iso(end_at)
    if start_date is None or end_date is None:
        return {"enabled": False, "error": "invalid_datetime"}

    event = EKEvent.eventWithEventStore_(store)
    event.setTitle_(str(title or "Tâche"))
    event.setStartDate_(start_date)
    event.setEndDate_(end_date)
    if notes:
        event.setNotes_(str(notes))
    if location:
        event.setLocation_(str(location))

    calendar = None
    if calendar_name:
        calendars = list(store.calendarsForEntityType_(entity_type) or [])
        for c in calendars:
            if str(c.title()) == calendar_name:
                calendar = c
                break
    if calendar is None:
        calendar = store.defaultCalendarForNewEvents()
    if calendar is None:
        return {"enabled": False, "error": "no_default_calendar"}
    event.setCalendar_(calendar)

    try:
        ok, save_err = store.saveEvent_span_commit_error_(event, EKSpanThisEvent, True, None)
    except Exception:
        try:
            ok, save_err = store.saveEvent_span_error_(event, EKSpanThisEvent, None)
        except Exception as e:
            return {"enabled": False, "error": str(e)}

    if not ok:
        return {"enabled": False, "error": str(save_err) if save_err else "save_failed"}

    uid = str(event.calendarItemIdentifier() or event.eventIdentifier() or "")
    return {
        "enabled": True,
        "error": None,
        "event_uid": uid,
        "calendar_name": str(calendar.title()) if calendar else None,
    }


def _find_event_by_uid(store, event_uid: str):
    """Find an EventKit event from multiple identifier methods."""
    if not event_uid:
        return None
    for method in (
        "eventWithIdentifier_",
        "calendarItemWithIdentifier_",
        "eventWithUniqueIdentifier_",
        "eventWithEventIdentifier_",
    ):
        if not hasattr(store, method):
            continue
        try:
            ev = getattr(store, method)(event_uid)
            if ev is not None:
                return ev
        except Exception:
            continue
    return None


def update_apple_calendar_event(
    event_uid: str,
    title: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    notes: str | None = None,
    location: str | None = None,
) -> dict:
    """Update an existing Apple Calendar event."""
    if sys.platform != "darwin":
        return {"enabled": False, "error": "apple_calendar_macos_only"}

    try:
        from EventKit import EKSpanThisEvent  # type: ignore
    except Exception:
        return {"enabled": False, "error": "eventkit_unavailable"}

    store, _, err = _get_store_and_access()
    if err:
        return {"enabled": False, "error": err}

    ev = _find_event_by_uid(store, event_uid)
    if ev is None:
        return {"enabled": False, "error": "event_not_found"}

    if title is not None:
        ev.setTitle_(str(title))
    if start_at:
        ns = _nsdate_from_iso(start_at)
        if ns is not None:
            ev.setStartDate_(ns)
    if end_at:
        ne = _nsdate_from_iso(end_at)
        if ne is not None:
            ev.setEndDate_(ne)
    if notes is not None:
        ev.setNotes_(str(notes))
    if location is not None:
        ev.setLocation_(str(location))

    try:
        ok, save_err = store.saveEvent_span_commit_error_(ev, EKSpanThisEvent, True, None)
    except Exception:
        try:
            ok, save_err = store.saveEvent_span_error_(ev, EKSpanThisEvent, None)
        except Exception as e:
            return {"enabled": False, "error": str(e)}

    if not ok:
        return {"enabled": False, "error": str(save_err) if save_err else "save_failed"}

    return {"enabled": True, "error": None, "event_uid": event_uid}


def delete_apple_calendar_event(event_uid: str) -> dict:
    """Delete an Apple Calendar event by uid."""
    if sys.platform != "darwin":
        return {"enabled": False, "error": "apple_calendar_macos_only"}

    try:
        from EventKit import EKSpanThisEvent  # type: ignore
    except Exception:
        return {"enabled": False, "error": "eventkit_unavailable"}

    store, _, err = _get_store_and_access()
    if err:
        return {"enabled": False, "error": err}

    ev = _find_event_by_uid(store, event_uid)
    if ev is None:
        return {"enabled": False, "error": "event_not_found"}

    try:
        ok, del_err = store.removeEvent_span_commit_error_(ev, EKSpanThisEvent, True, None)
    except Exception:
        try:
            ok, del_err = store.removeEvent_span_error_(ev, EKSpanThisEvent, None)
        except Exception as e:
            return {"enabled": False, "error": str(e)}

    if not ok:
        return {"enabled": False, "error": str(del_err) if del_err else "delete_failed"}

    return {"enabled": True, "error": None, "event_uid": event_uid}


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


def diagnose_apple_calendar(db_path: str | Path | None = None) -> dict:
    """Quick diagnostics for Apple Calendar integration."""
    info = {
        "enabled": False,
        "error": None,
        "platform": sys.platform,
        "eventkit": "unknown",
        "permission": "unknown",
        "calendars_count": 0,
        "default_calendar": None,
        "probe_events_synced": None,
    }

    if sys.platform != "darwin":
        info["error"] = "apple_calendar_macos_only"
        return info

    try:
        from EventKit import EKEntityTypeEvent  # type: ignore
    except Exception:
        info["eventkit"] = "unavailable"
        info["error"] = "eventkit_unavailable"
        return info

    info["eventkit"] = "ok"
    store, entity_type, err = _get_store_and_access()
    if err:
        info["permission"] = "denied"
        info["error"] = err
        return info

    info["permission"] = "granted"
    try:
        calendars = list(store.calendarsForEntityType_(entity_type or EKEntityTypeEvent) or [])
        info["calendars_count"] = len(calendars)
        default_cal = store.defaultCalendarForNewEvents()
        info["default_calendar"] = str(default_cal.title()) if default_cal else None
    except Exception as e:
        info["error"] = str(e)
        return info

    if db_path:
        try:
            probe = sync_apple_calendar(db_path=db_path, days_ahead=2)
            info["probe_events_synced"] = int(probe.get("events_synced", 0) or 0)
            if probe.get("enabled"):
                info["enabled"] = True
            else:
                info["error"] = probe.get("error")
        except Exception as e:
            info["error"] = str(e)
    else:
        info["enabled"] = True

    return info


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
