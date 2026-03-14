"""Apple Calendar sync (macOS) for Bord."""

from __future__ import annotations

import sqlite3
import subprocess
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
    # Convertir en heure locale (cohérent avec le reste du système)
    return datetime.fromtimestamp(ts).replace(microsecond=0).isoformat()


def _nsdate_from_iso(iso_ts: str):
    try:
        import time as _time

        from Foundation import NSDate  # type: ignore

        # Supprimer le 'Z' ou le fuseau horaire s'il existe
        iso_clean = iso_ts.rstrip("Z").split("+")[0]
        # Si le format contient un fuseau horaire, on le supprime aussi
        if "-" in iso_clean[10:]:  # Après la date YYYY-MM-DD
            iso_clean = iso_clean[:19]

        # Parser comme heure locale et convertir en timestamp
        dt = datetime.fromisoformat(iso_clean)
        ts = _time.mktime(dt.timetuple())
        return NSDate.dateWithTimeIntervalSince1970_(float(ts))
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
            grant["err"] = str(error)  # type: ignore[assignment]
        done.set()

    # Utiliser l'API moderne (macOS 17+) puis fallback sur l'ancienne
    try:
        store.requestFullAccessToEventsWithCompletion_(_completion)
    except (AttributeError, Exception):
        try:
            store.requestAccessToEntityType_completion_(EKEntityTypeEvent, _completion)
        except Exception:
            pass

    # Spinner le RunLoop pour que la callback se déclenche (nécessaire
    # quand Python tourne hors d'une app Cocoa avec boucle événementielle)
    try:
        from Foundation import NSDate, NSRunLoop  # type: ignore

        for _ in range(50):  # 5 secondes max
            NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))
            if done.is_set():
                break
    except Exception:
        done.wait(timeout=5)

    # Tester l'opération la plus basique pour vérifier le droit de lire
    try:
        cals = list(store.calendarsForEntityType_(EKEntityTypeEvent) or [])
        if cals or grant.get("ok"):
            return store, EKEntityTypeEvent, None
        # Pas de calendriers mais pas d'exception : permission peut-être
        # accordée mais 0 calendriers configurés, ou status notDetermined
        status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
        if status in (3, 4):  # authorized / fullAccess
            return store, EKEntityTypeEvent, None
        return store, EKEntityTypeEvent, f"calendar_status_unknown_{status}"
    except Exception as e:
        err = str(e) or "calendar_permission_denied"
        return None, None, err


# ── AppleScript fallback (contourne les restrictions TCC de macOS 26) ──


def _osascript(script: str, timeout: int = 15) -> str:
    """Run an AppleScript and return stdout."""
    r = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"osascript exit {r.returncode}")
    return r.stdout.strip()


def _fetch_with_applescript(days_ahead: int) -> tuple[list[dict], str | None]:
    """Fetch calendar events via AppleScript (fallback when EventKit TCC fails)."""
    if sys.platform != "darwin":
        return [], "apple_calendar_macos_only"

    # Exclure les calendriers système lents (Rappels, Anniversaires, Siri, Fêtes)
    skip_names = {"Rappels programmés", "Anniversaires", "Suggestions de Siri"}
    script = f"""
set startDate to current date
set endDate to startDate + {days_ahead} * days
set skipNames to {{{", ".join('"' + n + '"' for n in skip_names)}}}
set output to ""
tell application "Calendar"
    repeat with c in calendars
        set cName to name of c
        if cName is not in skipNames then
            try
                set evts to (every event of c whose start date >= startDate and start date <= endDate)
                repeat with e in evts
                    set eUID to uid of e
                    set eTitle to summary of e
                    set eStart to (start date of e) as «class isot» as string
                    set eEnd to (end date of e) as «class isot» as string
                    set eNotes to ""
                    try
                        set n to description of e
                        if n is not missing value then set eNotes to n
                    end try
                    set eLoc to ""
                    try
                        set loc to location of e
                        if loc is not missing value then set eLoc to loc
                    end try
                    set eAllDay to allday event of e
                    set output to output & eUID & "\\t" & cName & "\\t" & eTitle & "\\t" & eStart & "\\t" & eEnd & "\\t" & eNotes & "\\t" & eLoc & "\\t" & eAllDay & "\\n"
                end repeat
            end try
        end if
    end repeat
end tell
return output
"""
    try:
        raw = _osascript(script, timeout=60)
    except Exception as e:
        return [], str(e)

    # Robust parsing: notes/title/location may contain newlines which
    # break the tab-separated output across multiple lines.  Each record
    # is: UID\tcal\ttitle\tstartISO\tendISO\tnotes\tlocation\tallday
    # We detect a new record when a line has >=6 tab-fields with ISO
    # dates at positions 3 & 4.  Continuation lines are appended to the
    # pending record's raw text, and we parse fields from the assembled
    # block at flush time.
    import re

    _iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    parsed: list[dict] = []
    pending_raw: str | None = None

    def _flush(raw_block: str) -> None:
        # The full block is one logical record. Split on tabs.
        parts = raw_block.split("\t")
        if len(parts) < 6:
            return
        uid, cal_name, title = parts[0], parts[1], parts[2]
        start_at, end_at = parts[3][:19], parts[4][:19]
        if not _iso_re.match(start_at):
            return
        # Last field is allday (true/false), second-to-last is location.
        # Everything between parts[5] and parts[-2] is notes (may contain
        # tabs that were inside the notes text itself).
        if len(parts) >= 8:
            all_day = parts[-1].strip()
            location = parts[-2]
            notes = " ".join(parts[5:-2])
        elif len(parts) == 7:
            all_day = parts[-1].strip()
            location = ""
            notes = " ".join(parts[5:-1])
        else:
            all_day = ""
            location = ""
            notes = " ".join(parts[5:])
        # Sanitize
        for ch in ("\n", "\r", "\t"):
            notes = notes.replace(ch, " ")
            title = title.replace(ch, " ")
            location = location.replace(ch, " ")
        parsed.append(
            {
                "event_uid": uid.strip(),
                "calendar_name": cal_name.strip(),
                "title": title.strip(),
                "location": location.strip(),
                "notes": notes.strip(),
                "start_at": start_at,
                "end_at": end_at,
                "is_all_day": 1 if all_day.lower() in ("true", "1") else 0,
                "source": "apple_calendar",
            }
        )

    for line in raw.split("\n"):
        parts = line.split("\t")
        # A new record starts when we see >=6 tab fields with ISO dates at [3] & [4]
        is_new = (
            len(parts) >= 6
            and _iso_re.match(parts[3] if len(parts) > 3 else "")
            and _iso_re.match(parts[4] if len(parts) > 4 else "")
        )
        if is_new:
            if pending_raw is not None:
                _flush(pending_raw)
            pending_raw = line
        elif pending_raw is not None:
            # Continuation of notes — append with tab so we can still
            # detect the trailing location\tallday fields.
            pending_raw = pending_raw + "\t" + line
        # else: orphan line before first record, skip

    if pending_raw is not None:
        _flush(pending_raw)

    parsed.sort(key=lambda x: x["start_at"])
    return parsed, None


def _create_event_applescript(
    title: str,
    start_at: str,
    end_at: str,
    notes: str | None = None,
    location: str | None = None,
    calendar_name: str | None = None,
) -> dict:
    """Create a calendar event via AppleScript."""
    if sys.platform != "darwin":
        return {"enabled": False, "error": "apple_calendar_macos_only"}

    cal_target = f'calendar "{calendar_name}"' if calendar_name else 'calendar "Personnel"'

    escaped_title = title.replace('"', '\\"').replace("'", "'")
    # Construire date via AppleScript natif pour éviter les problèmes de locale
    start_iso = start_at[:19]
    end_iso = end_at[:19]

    note_set = ""
    loc_set = ""
    if notes:
        escaped_notes = notes.replace('"', '\\"').replace("'", "'")
        note_set = f'\n        set description of newEvent to "{escaped_notes}"'
    if location:
        escaped_loc = location.replace('"', '\\"').replace("'", "'")
        loc_set = f'\n        set location of newEvent to "{escaped_loc}"'

    script = f'''
tell application "Calendar"
    tell {cal_target}
        set sDate to current date
        set year of sDate to {start_iso[:4]}
        set month of sDate to {int(start_iso[5:7])}
        set day of sDate to {int(start_iso[8:10])}
        set hours of sDate to {int(start_iso[11:13])}
        set minutes of sDate to {int(start_iso[14:16])}
        set seconds of sDate to {int(start_iso[17:19])}
        set eDate to current date
        set year of eDate to {end_iso[:4]}
        set month of eDate to {int(end_iso[5:7])}
        set day of eDate to {int(end_iso[8:10])}
        set hours of eDate to {int(end_iso[11:13])}
        set minutes of eDate to {int(end_iso[14:16])}
        set seconds of eDate to {int(end_iso[17:19])}
        set newEvent to make new event with properties {{summary:"{escaped_title}", start date:sDate, end date:eDate}}{note_set}{loc_set}
        return uid of newEvent
    end tell
end tell
'''
    try:
        uid = _osascript(script, timeout=15)
        return {
            "enabled": True,
            "error": None,
            "event_uid": uid.strip(),
            "calendar_name": calendar_name,
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)}


def _update_event_applescript(
    event_uid: str,
    title: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    notes: str | None = None,
    location: str | None = None,
) -> dict:
    """Update a calendar event via AppleScript."""
    if sys.platform != "darwin":
        return {"enabled": False, "error": "apple_calendar_macos_only"}

    set_lines = []
    if title is not None:
        set_lines.append(f'set summary of e to "{title.replace(chr(34), chr(92) + chr(34))}"')
    if notes is not None:
        set_lines.append(f'set description of e to "{notes.replace(chr(34), chr(92) + chr(34))}"')
    if location is not None:
        set_lines.append(f'set location of e to "{location.replace(chr(34), chr(92) + chr(34))}"')

    # Construire les dates via AppleScript natif (évite l'erreur -10000)
    date_setup = ""
    if start_at is not None:
        s = start_at[:19]
        date_setup += f"""
            set sDate to current date
            set year of sDate to {s[:4]}
            set month of sDate to {int(s[5:7])}
            set day of sDate to {int(s[8:10])}
            set hours of sDate to {int(s[11:13])}
            set minutes of sDate to {int(s[14:16])}
            set seconds of sDate to {int(s[17:19])}
            set start date of e to sDate"""
    if end_at is not None:
        e_iso = end_at[:19]
        date_setup += f"""
            set eDate to current date
            set year of eDate to {e_iso[:4]}
            set month of eDate to {int(e_iso[5:7])}
            set day of eDate to {int(e_iso[8:10])}
            set hours of eDate to {int(e_iso[11:13])}
            set minutes of eDate to {int(e_iso[14:16])}
            set seconds of eDate to {int(e_iso[17:19])}
            set end date of e to eDate"""

    if not set_lines and not date_setup:
        return {"enabled": True, "error": None, "event_uid": event_uid}

    set_block = "\n            ".join(set_lines)
    script = f'''
tell application "Calendar"
    repeat with c in calendars
        set evts to (every event of c whose uid is "{event_uid}")
        repeat with e in evts{date_setup}
            {set_block}
            return uid of e
        end repeat
    end repeat
end tell
return "not_found"
'''
    try:
        result = _osascript(script, timeout=15)
        if result == "not_found":
            return {"enabled": False, "error": "event_not_found"}
        return {"enabled": True, "error": None, "event_uid": event_uid}
    except Exception as e:
        return {"enabled": False, "error": str(e)}


def _delete_event_applescript(event_uid: str) -> dict:
    """Delete a calendar event via AppleScript."""
    if sys.platform != "darwin":
        return {"enabled": False, "error": "apple_calendar_macos_only"}

    script = f'''
tell application "Calendar"
    repeat with c in calendars
        set evts to (every event of c whose uid is "{event_uid}")
        repeat with e in evts
            delete e
            return "ok"
        end repeat
    end repeat
end tell
return "not_found"
'''
    try:
        result = _osascript(script, timeout=15)
        if result == "not_found":
            return {"enabled": False, "error": "event_not_found"}
        return {"enabled": True, "error": None, "event_uid": event_uid}
    except Exception as e:
        return {"enabled": False, "error": str(e)}


def _applescript_available() -> bool:
    """Check if AppleScript can access Calendar app."""
    if sys.platform != "darwin":
        return False
    try:
        _osascript('tell application "Calendar" to get name of first calendar', timeout=5)
        return True
    except Exception:
        return False


def _fetch_with_eventkit(
    days_ahead: int, calendar_name: str | None = None
) -> tuple[list[dict], str | None]:
    """Fetch calendar events via EventKit, fallback to AppleScript."""
    try:
        from Foundation import NSDate  # type: ignore
    except Exception:
        # EventKit indisponible — fallback AppleScript
        return _fetch_with_applescript(days_ahead)

    store, EKEntityTypeEvent, err = _get_store_and_access()
    if err:
        # EventKit TCC refusé — fallback AppleScript
        if _applescript_available():
            return _fetch_with_applescript(days_ahead)
        return [], err

    start_dt = datetime.now()
    end_dt = start_dt + timedelta(days=days_ahead)
    start_date = NSDate.dateWithTimeIntervalSince1970_(start_dt.timestamp())
    end_date = NSDate.dateWithTimeIntervalSince1970_(end_dt.timestamp())

    calendars = list(store.calendarsForEntityType_(EKEntityTypeEvent) or [])

    # Si EventKit ne voit aucun (ou très peu de) calendrier(s), fallback AppleScript
    # car l'accès TCC est souvent partiel sur macOS 26+
    if len(calendars) <= 1 and _applescript_available():
        return _fetch_with_applescript(days_ahead)

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
    # si on ne peut pas déterminer le statut mais aucune erreur critique, on
    # tente quand même de poursuivre en créant un store vierge – cela permet de
    # contourner certains cas où l'API renvoie un statut inconnu (0) malgré des
    # permissions valides.
    if err:
        if err.startswith("calendar_status_unknown"):
            try:
                from EventKit import EKEntityTypeEvent, EKEventStore  # type: ignore

                store = EKEventStore.alloc().init()
                entity_type = EKEntityTypeEvent
                err = None
            except Exception:
                pass
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
        # Si pas de calendrier par défaut, prioriser un calendrier iCloud/modifiable
        calendars = list(store.calendarsForEntityType_(entity_type) or [])
        preferred = None
        for c in calendars:
            try:
                src = c.source() if hasattr(c, "source") else None
                src_title = str(src.title()).lower() if src is not None else ""
            except Exception:
                src_title = ""
            if src_title and ("icloud" in src_title or "caldav" in src_title):
                preferred = c
                break
        if preferred is None:
            for c in calendars:
                try:
                    if c.allowsContentModifications():
                        preferred = c
                        break
                except Exception:
                    # some calendar objects may not expose this method reliably
                    continue
        calendar = preferred
    if calendar is None:
        # Last-resort fallback: pick the first available calendar and try
        try:
            calendars = list(store.calendarsForEntityType_(entity_type) or [])
            if calendars:
                calendar = calendars[0]
        except Exception:
            calendar = None
    if calendar is None:
        # Fallback AppleScript si EventKit ne voit aucun calendrier
        if _applescript_available():
            return _create_event_applescript(
                title=title,
                start_at=start_at,
                end_at=end_at,
                notes=notes,
                location=location,
                calendar_name=calendar_name,
            )
        return {"enabled": False, "error": "no_writable_calendar"}
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


def update_apple_calendar_event(
    event_uid: str,
    title: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    notes: str | None = None,
    location: str | None = None,
) -> dict:
    """Update an existing event in Apple Calendar via EventKit."""
    if sys.platform != "darwin":
        return {"enabled": False, "error": "apple_calendar_macos_only"}

    try:
        from EventKit import EKSpanThisEvent  # type: ignore
    except Exception:
        if _applescript_available():
            return _update_event_applescript(event_uid, title, start_at, end_at, notes, location)
        return {"enabled": False, "error": "eventkit_unavailable"}

    store, _, err = _get_store_and_access()
    if err:
        if err.startswith("calendar_status_unknown"):
            try:
                from EventKit import EKEventStore  # type: ignore

                store = EKEventStore.alloc().init()
                err = None
            except Exception:
                pass
        if err:
            if _applescript_available():
                return _update_event_applescript(
                    event_uid, title, start_at, end_at, notes, location
                )
            return {"enabled": False, "error": err}

    event = _find_event_by_uid(store, event_uid)
    if event is None:
        if _applescript_available():
            return _update_event_applescript(event_uid, title, start_at, end_at, notes, location)
        return {"enabled": False, "error": "event_not_found"}

    # Update fields if provided
    if title is not None:
        event.setTitle_(str(title))
    if start_at is not None:
        start_date = _nsdate_from_iso(start_at)
        if start_date:
            event.setStartDate_(start_date)
    if end_at is not None:
        end_date = _nsdate_from_iso(end_at)
        if end_date:
            event.setEndDate_(end_date)
    if notes is not None:
        event.setNotes_(str(notes))
    if location is not None:
        event.setLocation_(str(location))

    try:
        ok, save_err = store.saveEvent_span_commit_error_(event, EKSpanThisEvent, True, None)
    except Exception:
        try:
            ok, save_err = store.saveEvent_span_error_(event, EKSpanThisEvent, None)
        except Exception as e:
            return {"enabled": False, "error": str(e)}

    if not ok:
        return {"enabled": False, "error": str(save_err) if save_err else "save_failed"}

    return {"enabled": True, "error": None, "event_uid": event_uid}


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


def delete_apple_calendar_event(event_uid: str) -> dict:
    """Delete an Apple Calendar event by uid."""
    if sys.platform != "darwin":
        return {"enabled": False, "error": "apple_calendar_macos_only"}

    try:
        from EventKit import EKSpanThisEvent  # type: ignore
    except Exception:
        if _applescript_available():
            return _delete_event_applescript(event_uid)
        return {"enabled": False, "error": "eventkit_unavailable"}

    store, _, err = _get_store_and_access()
    if err:
        if _applescript_available():
            return _delete_event_applescript(event_uid)
        return {"enabled": False, "error": err}

    ev = _find_event_by_uid(store, event_uid)
    if ev is None:
        if _applescript_available():
            return _delete_event_applescript(event_uid)
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
    end_cutoff = (
        (datetime.now() + timedelta(days=days_ahead + 2)).replace(microsecond=0).isoformat()
    )

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

    # ── Reconciliation: remove orphaned planner_tasks whose Apple event
    #    no longer exists in calendar_events (deleted from Apple Calendar).
    orphan_ids = [
        row[0]
        for row in conn.execute(
            """
        SELECT pt.id
        FROM planner_tasks pt
        WHERE pt.source = 'apple_calendar'
          AND pt.calendar_uid IS NOT NULL
          AND pt.calendar_uid NOT IN (SELECT event_uid FROM calendar_events)
        """,
        ).fetchall()
    ]
    if orphan_ids:
        conn.execute(
            f"DELETE FROM planner_tasks WHERE id IN ({','.join('?' * len(orphan_ids))})",
            orphan_ids,
        )

    conn.commit()
    conn.close()

    return {
        "enabled": True,
        "error": None,
        "events_synced": inserted,
        "orphaned_tasks_removed": len(orphan_ids) if orphan_ids else 0,
        "window_days": days_ahead,
        "synced_at": now,
    }


def diagnose_apple_calendar(db_path: str | Path | None = None) -> dict:
    """Return lightweight diagnostics for Apple Calendar integration."""
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
        # Vérifier si AppleScript fonctionne comme fallback
        if _applescript_available():
            info["permission"] = "granted"
            info["error"] = None
            info["enabled"] = True
            info["eventkit"] = "applescript_fallback"
            try:
                cal_names = _osascript(
                    'tell application "Calendar" to get name of every calendar',
                    timeout=5,
                )
                cals = [c.strip() for c in cal_names.split(",") if c.strip()]
                info["calendars_count"] = len(cals)
                if cals:
                    info["default_calendar"] = cals[0]
            except Exception:
                pass
            if db_path:
                try:
                    probe = sync_apple_calendar(db_path=db_path, days_ahead=2)
                    info["probe_events_synced"] = int(probe.get("events_synced", 0) or 0)
                except Exception:
                    pass
            return info
        if err.startswith("calendar_status_unknown"):
            info["permission"] = "unknown"
        else:
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
