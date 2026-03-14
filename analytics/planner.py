"""
planner.py — Pilotage hebdomadaire (planning + catégories de vie)
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path

CATEGORY_ALIASES = {
    # Nouveaux domaines
    "sport": "sport",
    "yoga": "yoga",
    "travail": "travail",
    "formation": "formation",
    "social": "social",
    "lecon": "lecon",
    "autre": "autre",
    # Rétro-compat anciens noms
    "sante": "sport",
    "santé": "sport",
    "health": "sport",
    "relationnel": "social",
    "apprentissage": "formation",
    "learning": "formation",
    "leçon": "lecon",
    "lesson": "lecon",
    "work": "travail",
    "other": "autre",
}

TRIAGE_STATUS_ALIASES = {
    "a_determiner": "a_determiner",
    "urgent": "urgent",
    "a_planifier": "a_planifier",
    "planifier": "a_planifier",
    "planned": "a_planifier",
    "non_urgent": "non_urgent",
    "later": "non_urgent",
    "termine": "termine",
    "done": "termine",
}

WEEKDAY_ALIASES = {
    "lundi": 0,
    "monday": 0,
    "mon": 0,
    "mardi": 1,
    "tuesday": 1,
    "tue": 1,
    "mercredi": 2,
    "wednesday": 2,
    "wed": 2,
    "jeudi": 3,
    "thursday": 3,
    "thu": 3,
    "vendredi": 4,
    "friday": 4,
    "fri": 4,
    "samedi": 5,
    "saturday": 5,
    "sat": 5,
    "dimanche": 6,
    "sunday": 6,
    "sun": 6,
}

WEEK_REF_ALIASES = {
    "this_week": 0,
    "current_week": 0,
    "cette_semaine": 0,
    "next_week": 1,
    "semaine_prochaine": 1,
    "week_plus_2": 2,
    "semaine_apres": 2,
    "semaine_apres_prochaine": 2,
}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def normalize_category(raw: str | None) -> str:
    if not raw:
        return "autre"
    key = str(raw).strip().lower()
    return CATEGORY_ALIASES.get(key, "autre")


def normalize_triage_status(raw: str | None) -> str:
    if not raw:
        return "a_determiner"
    key = str(raw).strip().lower()
    return TRIAGE_STATUS_ALIASES.get(key, "a_determiner")


def infer_category(title: str | None, calendar_name: str | None = None) -> str:
    text = f"{title or ''} {calendar_name or ''}".lower()

    sport_kw = [
        "run",
        "course",
        "muscu",
        "gym",
        "tennis",
        "golf",
        "swim",
        "natation",
        "vélo",
        "velo",
        "sport",
        "workout",
        "crossfit",
        "trail",
    ]
    yoga_kw = ["yoga", "méditation", "meditation", "mobilité", "stretching", "pilates"]
    work_kw = [
        "client",
        "meeting",
        "rdv",
        "call",
        "prospect",
        "linkedin",
        "mail",
        "travail",
        "business",
        "entreprise",
    ]
    social_kw = [
        "famille",
        "ami",
        "diner",
        "déjeuner",
        "dej",
        "soirée",
        "sortie",
        "relation",
        "fête",
        "anniversaire",
    ]
    formation_kw = [
        "piano",
        "apprendre",
        "learning",
        "formation",
        "cours",
        "leçon",
        "lesson",
        "conférence",
        "webinaire",
    ]

    if any(k in text for k in yoga_kw):
        return "yoga"
    if any(k in text for k in sport_kw):
        return "sport"
    if any(k in text for k in work_kw):
        return "travail"
    if any(k in text for k in social_kw):
        return "social"
    if any(k in text for k in formation_kw):
        return "formation"
    return "autre"


def parse_task_datetime(task_date: str, task_time: str, duration_min: int) -> tuple[str, str]:
    d = date.fromisoformat(task_date)
    t = time.fromisoformat(task_time)
    start = datetime.combine(d, t)
    end = start + timedelta(minutes=int(duration_min))
    return (
        start.replace(microsecond=0).isoformat(),
        end.replace(microsecond=0).isoformat(),
    )


def week_start_from_ref(week_ref: str | None, base_day: date | None = None) -> date:
    """Retourne le lundi de la semaine ciblée à partir d'un alias."""
    if base_day is None:
        base_day = date.today()
    current_week_start = base_day - timedelta(days=base_day.weekday())
    key = str(week_ref or "this_week").strip().lower()
    delta = WEEK_REF_ALIASES.get(key, 0)
    return current_week_start + timedelta(days=delta * 7)


def parse_weekday(raw: str | int | None) -> int:
    """Normalise un jour semaine vers 0=lundi ... 6=dimanche."""
    if raw is None:
        return 0
    if isinstance(raw, int):
        return max(0, min(6, int(raw)))
    key = str(raw).strip().lower()
    if key in WEEKDAY_ALIASES:
        return WEEKDAY_ALIASES[key]
    try:
        n = int(key)
        return max(0, min(6, n))
    except Exception:
        return 0


def parse_hhmm(raw: str | None, fallback: str = "09:00:00") -> str:
    t = str(raw or fallback).strip()
    if len(t) == 5:
        t = t + ":00"
    try:
        time.fromisoformat(t)
        return t
    except Exception:
        return fallback


def parse_relative_slot(
    week_ref: str | None,
    weekday: str | int | None,
    task_time: str | None,
    duration_min: int | float | None,
    base_day: date | None = None,
) -> tuple[str, str]:
    """
    Construit start_at/end_at ISO depuis une référence relative.
    Exemple: week_ref='next_week', weekday='mardi', task_time='14:00', duration=60
    """
    ws = week_start_from_ref(week_ref, base_day=base_day)
    wd = parse_weekday(weekday)
    d = ws + timedelta(days=wd)
    hhmmss = parse_hhmm(task_time)
    dur = max(5, int(duration_min or 60))
    return parse_task_datetime(str(d), hhmmss, dur)


def connect_db(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def add_task(
    db_path: str | Path,
    title: str,
    category: str,
    start_at: str | None = None,
    end_at: str | None = None,
    notes: str | None = None,
    sync_to_apple: bool = False,
    apple_calendar_name: str | None = None,
    triage_status: str | None = None,
    scheduled: bool = False,
    scheduled_date: str | None = None,
    scheduled_start: str | None = None,
    scheduled_end: str | None = None,
    last_bucket_before_scheduling: str | None = None,
) -> dict:
    """Crée une tâche planner locale, optionnellement sync Apple Calendar."""
    db_path = Path(db_path)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    ts = normalize_triage_status(triage_status)
    is_scheduled = int(bool(scheduled))

    # Si on a des dates, la tâche est planifiée dans le calendrier
    if start_at and end_at and not is_scheduled:
        is_scheduled = 1
        scheduled_start = scheduled_start or start_at
        scheduled_end = scheduled_end or end_at
        scheduled_date = scheduled_date or (start_at[:10] if start_at else None)
        if ts == "a_determiner":
            ts = "a_planifier"

    calendar_uid = None
    source = "local"
    sync_error = None

    if sync_to_apple and start_at and end_at:
        try:
            from integrations.apple_calendar import create_apple_calendar_event

            res = create_apple_calendar_event(
                title=title,
                start_at=start_at,
                end_at=end_at,
                notes=notes,
                calendar_name=apple_calendar_name,
            )
            if res.get("enabled"):
                calendar_uid = res.get("event_uid")
                source = "apple_calendar"
            else:
                sync_error = res.get("error")
        except Exception as e:
            sync_error = str(e)

    cursor.execute(
        """
        INSERT INTO planner_tasks
          (title, category, start_at, end_at, notes, status, source, calendar_uid,
           triage_status, scheduled, scheduled_date, scheduled_start, scheduled_end,
           last_bucket_before_scheduling, created_at, updated_at)
        VALUES (?,?,?,?,?,'planned',?,?,?,?,?,?,?,?,?,?)
        """,
        (
            title.strip(),
            normalize_category(category),
            start_at or "",
            end_at or "",
            notes.strip() if notes else None,
            source,
            calendar_uid,
            ts,
            is_scheduled,
            scheduled_date,
            scheduled_start,
            scheduled_end,
            last_bucket_before_scheduling,
            now_iso(),
            now_iso(),
        ),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "task_id": task_id,
        "category": normalize_category(category),
        "triage_status": ts,
        "scheduled": bool(is_scheduled),
        "start_at": start_at,
        "end_at": end_at,
        "source": source,
        "apple_uid": calendar_uid,
        "apple_sync_error": sync_error,
    }


def add_tasks_batch(
    db_path: str | Path,
    tasks: list[dict],
    default_sync_apple: bool = True,
    default_calendar_name: str | None = None,
) -> dict:
    """
    Création batch de tâches planner.
    Supporte:
      - start_at/end_at directs
      - ou week_ref + weekday + time + duration_min
    """
    created: list[dict] = []
    errors: list[dict] = []

    for idx, raw in enumerate(tasks or []):
        try:
            title = str(raw.get("title") or "").strip()
            if not title:
                raise ValueError("missing_title")

            category = normalize_category(raw.get("category"))
            if category == "autre" and raw.get("type"):
                # fallback type -> category
                t = str(raw.get("type")).lower().strip()
                type_map = {
                    "cardio": "sante",
                    "musculation": "sante",
                    "mobilite": "sante",
                    "sport_libre": "sante",
                    "travail": "travail",
                    "apprentissage": "apprentissage",
                    "relationnel": "relationnel",
                }
                category = type_map.get(t, category)

            start_at = raw.get("start_at")
            end_at = raw.get("end_at")
            if not start_at or not end_at:
                start_at, end_at = parse_relative_slot(
                    week_ref=raw.get("week_ref") or raw.get("week"),
                    weekday=raw.get("weekday"),
                    task_time=raw.get("time") or raw.get("task_time"),
                    duration_min=raw.get("duration_min"),
                )

            sync_apple = bool(raw.get("sync_apple", default_sync_apple))
            notes = raw.get("notes")
            res = add_task(
                db_path=db_path,
                title=title,
                category=category,
                start_at=str(start_at),
                end_at=str(end_at),
                notes=str(notes)[:5000] if notes is not None else None,
                sync_to_apple=sync_apple,
                apple_calendar_name=raw.get("calendar_name") or default_calendar_name,
            )
            created.append(
                {
                    "index": idx,
                    "title": title,
                    "task_id": res.get("task_id"),
                    "start_at": res.get("start_at"),
                    "end_at": res.get("end_at"),
                    "category": res.get("category"),
                    "apple_uid": res.get("apple_uid"),
                    "apple_sync_error": res.get("apple_sync_error"),
                }
            )
        except Exception as e:
            errors.append(
                {
                    "index": idx,
                    "title": raw.get("title"),
                    "error": str(e),
                }
            )

    return {
        "ok": len(errors) == 0,
        "created": created,
        "errors": errors,
        "created_count": len(created),
        "error_count": len(errors),
    }


def update_task(
    db_path: str | Path,
    task_id: int,
    title: str | None = None,
    category: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    notes: str | None = None,
    sync_apple: bool = True,
    triage_status: str | None = None,
    scheduled: bool | None = None,
    scheduled_date: str | None = None,
    scheduled_start: str | None = None,
    scheduled_end: str | None = None,
    last_bucket_before_scheduling: str | None = None,
    calendar_name: str | None = None,
) -> dict:
    """Met à jour une tâche planner, et éventuellement son événement Apple lié."""
    conn = connect_db(db_path)
    cur = conn.cursor()
    row = cur.execute(
        """SELECT id, title, category, start_at, end_at, notes, source, calendar_uid,
                  triage_status, scheduled, scheduled_date, scheduled_start, scheduled_end,
                  last_bucket_before_scheduling
           FROM planner_tasks WHERE id=?""",
        (int(task_id),),
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "task_not_found"}

    # Appliquer les champs fournis ou garder l'existant
    new_title = (title.strip() if title is not None else row["title"]) or "Tâche"
    new_category = (
        normalize_category(category) if category is not None else (row["category"] or "autre")
    )
    new_start = start_at if start_at is not None else (row["start_at"] or "")
    new_end = end_at if end_at is not None else (row["end_at"] or "")
    new_notes = (notes.strip() if notes else None) if notes is not None else row["notes"]
    new_ts = (
        normalize_triage_status(triage_status)
        if triage_status is not None
        else (row["triage_status"] or "a_determiner")
    )
    new_scheduled = int(scheduled) if scheduled is not None else (row["scheduled"] or 0)
    new_sch_date = scheduled_date if scheduled_date is not None else row["scheduled_date"]
    new_sch_start = scheduled_start if scheduled_start is not None else row["scheduled_start"]
    new_sch_end = scheduled_end if scheduled_end is not None else row["scheduled_end"]
    new_last_bkt = (
        last_bucket_before_scheduling
        if last_bucket_before_scheduling is not None
        else row["last_bucket_before_scheduling"]
    )

    calendar_uid = row["calendar_uid"]
    source = row["source"] or "local"
    sync_error = None

    if sync_apple and new_scheduled and new_sch_start and new_sch_end:
        if source == "apple_calendar" and calendar_uid:
            # Mettre à jour l'événement Apple existant
            try:
                from integrations.apple_calendar import update_apple_calendar_event

                res = update_apple_calendar_event(
                    event_uid=calendar_uid,
                    title=new_title,
                    start_at=new_sch_start,
                    end_at=new_sch_end,
                    notes=new_notes,
                )
                if not res.get("enabled"):
                    sync_error = res.get("error")
            except Exception as e:
                sync_error = str(e)
        elif not calendar_uid:
            # Tâche locale sans événement Apple — créer l'événement maintenant
            try:
                from integrations.apple_calendar import create_apple_calendar_event

                res = create_apple_calendar_event(
                    title=new_title,
                    start_at=new_sch_start,
                    end_at=new_sch_end,
                    notes=new_notes,
                    calendar_name=calendar_name,
                )
                if res.get("enabled") and res.get("event_uid"):
                    calendar_uid = res["event_uid"]
                    source = "apple_calendar"
                else:
                    sync_error = res.get("error")
            except Exception as e:
                sync_error = str(e)

    cur.execute(
        """
        UPDATE planner_tasks
        SET title=?, category=?, start_at=?, end_at=?, notes=?, updated_at=?,
            triage_status=?, scheduled=?, scheduled_date=?, scheduled_start=?,
            scheduled_end=?, last_bucket_before_scheduling=?, source=?, calendar_uid=?
        WHERE id=?
        """,
        (
            new_title,
            new_category,
            new_start,
            new_end,
            new_notes,
            now_iso(),
            new_ts,
            new_scheduled,
            new_sch_date,
            new_sch_start,
            new_sch_end,
            new_last_bkt,
            source,
            calendar_uid,
            int(task_id),
        ),
    )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "task_id": int(task_id),
        "triage_status": new_ts,
        "scheduled": bool(new_scheduled),
        "apple_uid": calendar_uid,
        "sync_error": sync_error,
    }


def delete_task(
    db_path: str | Path,
    task_id: int,
    sync_apple: bool = True,
) -> dict:
    """Supprime une tâche planner (+ suppression Apple si liée)."""
    conn = connect_db(db_path)
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, source, calendar_uid FROM planner_tasks WHERE id=?",
        (int(task_id),),
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "task_not_found"}

    sync_error = None
    if sync_apple and (row["source"] == "apple_calendar") and row["calendar_uid"]:
        try:
            from integrations.apple_calendar import delete_apple_calendar_event

            res = delete_apple_calendar_event(event_uid=row["calendar_uid"])
            if not res.get("enabled"):
                sync_error = res.get("error")
        except Exception as e:
            sync_error = str(e)

    cur.execute("DELETE FROM planner_tasks WHERE id=?", (int(task_id),))
    # Also remove from calendar_events so the event doesn't reappear as
    # an "Apple-only" item before the next full sync.
    if row["calendar_uid"]:
        cur.execute(
            "DELETE FROM calendar_events WHERE event_uid=?",
            (row["calendar_uid"],),
        )
    conn.commit()
    conn.close()
    return {"ok": True, "task_id": int(task_id), "sync_error": sync_error}


def update_apple_only_event(
    event_uid: str,
    title: str,
    start_at: str,
    end_at: str,
    notes: str | None = None,
) -> dict:
    """Met à jour un événement Apple non géré par planner_tasks."""
    try:
        from integrations.apple_calendar import update_apple_calendar_event

        return update_apple_calendar_event(
            event_uid=event_uid,
            title=title,
            start_at=start_at,
            end_at=end_at,
            notes=notes,
        )
    except Exception as e:
        return {"enabled": False, "error": str(e)}


def delete_apple_only_event(event_uid: str, db_path: str | Path | None = None) -> dict:
    """Supprime un événement Apple non géré par planner_tasks."""
    try:
        from integrations.apple_calendar import delete_apple_calendar_event

        res = delete_apple_calendar_event(event_uid=event_uid)
        # Also remove from local calendar_events table so it doesn't linger
        # until the next full sync.
        if db_path:
            conn = connect_db(db_path)
            conn.execute("DELETE FROM calendar_events WHERE event_uid=?", (event_uid,))
            conn.commit()
            conn.close()
        return res
    except Exception as e:
        return {"enabled": False, "error": str(e)}


def sync_pending_tasks_to_apple(
    db_path: str | Path,
    limit: int = 200,
    calendar_name: str | None = None,
) -> dict:
    """
    Pousse les tâches planner locales non synchronisées vers Apple Calendar.
    Retourne un résumé: total, synced, failed.
    """
    conn = connect_db(db_path)
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT id, title, start_at, end_at, notes
        FROM planner_tasks
        WHERE status != 'cancelled'
          AND (calendar_uid IS NULL OR calendar_uid = '')
        ORDER BY start_at
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()

    total = len(rows)
    synced = 0
    failed = 0
    last_error = None

    try:
        from integrations.apple_calendar import create_apple_calendar_event
    except Exception as e:
        conn.close()
        return {
            "ok": False,
            "total": total,
            "synced": 0,
            "failed": total,
            "error": str(e),
        }

    # Calendrier par défaut : "Personnel" (privé) plutôt que "Calendrier" (partagé)
    if not calendar_name:
        calendar_name = "Personnel"

    for r in rows:
        res = create_apple_calendar_event(
            title=str(r["title"] or "Activité"),
            start_at=str(r["start_at"]),
            end_at=str(r["end_at"]),
            notes=r["notes"],
            calendar_name=calendar_name,
        )
        if res.get("enabled") and res.get("event_uid"):
            cur.execute(
                """
                UPDATE planner_tasks
                SET source='apple_calendar', calendar_uid=?, updated_at=?
                WHERE id=?
                """,
                (str(res["event_uid"]), now_iso(), int(r["id"])),
            )
            synced += 1
        else:
            failed += 1
            last_error = res.get("error") or last_error

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "total": total,
        "synced": synced,
        "failed": failed,
        "error": last_error,
    }


def _event_duration_h(start_at: str, end_at: str) -> float:
    try:
        start = datetime.fromisoformat(start_at[:19])
        end = datetime.fromisoformat(end_at[:19]) if end_at else start + timedelta(minutes=30)
        sec = max(0, (end - start).total_seconds())
        return sec / 3600.0
    except Exception:
        return 0.0


def get_planner_events(
    conn: sqlite3.Connection,
    start_at: str,
    end_at: str,
) -> list[dict]:
    """Retourne les tâches planifiées (scheduled=1) + événements Apple dans la fenêtre."""
    tasks = [
        dict(r)
        for r in conn.execute(
            """
        SELECT
          id, title, category, start_at, end_at, notes, status, source, calendar_uid,
          triage_status, scheduled, scheduled_date, scheduled_start, scheduled_end,
          last_bucket_before_scheduling
        FROM planner_tasks
        WHERE status != 'cancelled'
          AND triage_status != 'termine'
          AND scheduled = 1
          AND scheduled_start >= ? AND scheduled_start <= ?
        ORDER BY scheduled_start
        """,
            (start_at, end_at),
        ).fetchall()
    ]

    cals = [
        dict(r)
        for r in conn.execute(
            """
        SELECT
          event_uid, title, calendar_name, start_at, end_at, notes, source
        FROM calendar_events
        WHERE start_at>=? AND start_at<=?
        ORDER BY start_at
        """,
            (start_at, end_at),
        ).fetchall()
    ]

    rows: list[dict] = []
    task_calendar_keys = set()
    for t in tasks:
        cal_uid = t.get("calendar_uid")
        sch_start = t.get("scheduled_start") or t.get("start_at") or ""
        if cal_uid and sch_start:
            task_calendar_keys.add((str(cal_uid), str(sch_start)[:16]))

        rows.append(
            {
                "id": f"task:{t.get('id')}",
                "task_id": t.get("id"),
                "title": t.get("title") or "Tâche",
                "category": normalize_category(t.get("category")),
                "start_at": t.get("scheduled_start") or t.get("start_at"),
                "end_at": t.get("scheduled_end") or t.get("end_at"),
                "notes": t.get("notes"),
                "source": t.get("source") or "local",
                "calendar_uid": cal_uid,
                "calendar_name": None,
                "editable": True,
                "triage_status": t.get("triage_status") or "a_planifier",
                "scheduled": True,
                "last_bucket_before_scheduling": t.get("last_bucket_before_scheduling"),
            }
        )

    for e in cals:
        uid = str(e.get("event_uid") or "")
        start_key = str(e.get("start_at") or "")[:16]
        if (uid, start_key) in task_calendar_keys:
            continue
        title = e.get("title") or "Événement"
        cal_name = e.get("calendar_name")
        rows.append(
            {
                "id": f"apple:{uid}",
                "task_id": None,
                "title": title,
                "category": infer_category(title, cal_name),
                "start_at": e.get("start_at"),
                "end_at": e.get("end_at"),
                "notes": e.get("notes"),
                "source": "apple_calendar",
                "calendar_uid": uid,
                "calendar_name": cal_name,
                "editable": True,
                "triage_status": "a_planifier",
                "scheduled": True,
                "last_bucket_before_scheduling": None,
            }
        )

    rows.sort(key=lambda x: x.get("start_at") or "")
    return rows


def get_board_tasks(conn: sqlite3.Connection) -> list[dict]:
    """Retourne toutes les tâches non planifiées (board), y compris 'termine'."""
    rows = [
        dict(r)
        for r in conn.execute(
            """
        SELECT
          id, title, category, notes, status, source, calendar_uid,
          triage_status, scheduled, created_at, updated_at
        FROM planner_tasks
        WHERE status != 'cancelled'
          AND (scheduled = 0 OR scheduled IS NULL)
        ORDER BY
          CASE triage_status
            WHEN 'urgent'       THEN 1
            WHEN 'a_planifier'  THEN 2
            WHEN 'non_urgent'   THEN 3
            WHEN 'termine'      THEN 4
            ELSE 0
          END,
          created_at DESC
        """
        ).fetchall()
    ]

    result = []
    for r in rows:
        result.append(
            {
                "id": f"task:{r.get('id')}",
                "task_id": r.get("id"),
                "title": r.get("title") or "Tâche",
                "category": normalize_category(r.get("category")),
                "notes": r.get("notes"),
                "source": r.get("source") or "local",
                "calendar_uid": r.get("calendar_uid"),
                "triage_status": r.get("triage_status") or "a_determiner",
                "scheduled": False,
                "created_at": r.get("created_at"),
            }
        )
    return result


def get_board_tasks_db(db_path: str | Path) -> list[dict]:
    conn = connect_db(db_path)
    rows = get_board_tasks(conn)
    conn.close()
    return rows


def get_planner_events_db(
    db_path: str | Path,
    start_at: str,
    end_at: str,
) -> list[dict]:
    conn = connect_db(db_path)
    rows = get_planner_events(conn, start_at=start_at, end_at=end_at)
    conn.close()
    return rows


def weekly_category_summary(events: list[dict], week_start: date) -> dict:
    week_end = week_start + timedelta(days=7)
    summary = {
        "sante_h": 0.0,
        "travail_h": 0.0,
        "relationnel_h": 0.0,
        "apprentissage_h": 0.0,
        "autre_h": 0.0,
        "total_h": 0.0,
    }

    for e in events:
        try:
            start = datetime.fromisoformat((e.get("start_at") or "")[:19]).date()
        except Exception:
            continue
        if not (week_start <= start < week_end):
            continue
        cat = normalize_category(e.get("category"))
        dur_h = _event_duration_h(e.get("start_at") or "", e.get("end_at") or "")
        key = f"{cat}_h" if f"{cat}_h" in summary else "autre_h"
        summary[key] += dur_h
        summary["total_h"] += dur_h

    for k in summary:
        summary[k] = round(summary[k], 2)
    return summary


def weekly_series(conn: sqlite3.Connection) -> dict:
    """Séries longues (2017+): heures entraînement/sem & pas/sem."""
    training_h = [
        dict(r)
        for r in conn.execute(
            """
        SELECT strftime('%Y-W%W', started_at) AS week, ROUND(SUM(COALESCE(duration_s,0))/3600.0,2) AS value
        FROM activities
        WHERE started_at IS NOT NULL
        GROUP BY week
        ORDER BY week
        """
        ).fetchall()
    ]

    steps_week = [
        dict(r)
        for r in conn.execute(
            """
        SELECT strftime('%Y-W%W', date) AS week, ROUND(SUM(value),0) AS value
        FROM health_metrics
        WHERE metric='steps'
        GROUP BY week
        ORDER BY week
        """
        ).fetchall()
    ]

    sport_mix = [
        dict(r)
        for r in conn.execute(
            """
        SELECT type, ROUND(SUM(COALESCE(duration_s,0))/3600.0,2) AS hours
        FROM activities
        WHERE started_at IS NOT NULL
        GROUP BY type
        HAVING hours > 0
        ORDER BY hours DESC
        LIMIT 12
        """
        ).fetchall()
    ]

    return {
        "training_hours_weekly": training_h,
        "steps_weekly": steps_week,
        "sport_mix_hours": sport_mix,
    }
