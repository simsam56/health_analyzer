"""
planner.py — Pilotage hebdomadaire (planning + catégories de vie)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, date, time, timedelta
from pathlib import Path


CATEGORY_ALIASES = {
    "sante": "sante",
    "santé": "sante",
    "sport": "sante",
    "health": "sante",
    "travail": "travail",
    "work": "travail",
    "relationnel": "relationnel",
    "social": "relationnel",
    "apprentissage": "apprentissage",
    "learning": "apprentissage",
    "lecon": "apprentissage",
    "leçon": "apprentissage",
    "autre": "autre",
    "other": "autre",
}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def normalize_category(raw: str | None) -> str:
    if not raw:
        return "autre"
    key = str(raw).strip().lower()
    return CATEGORY_ALIASES.get(key, "autre")


def infer_category(title: str | None, calendar_name: str | None = None) -> str:
    text = f"{title or ''} {calendar_name or ''}".lower()

    health_kw = ["run", "course", "muscu", "gym", "tennis", "golf", "swim", "natation", "vélo", "velo", "sport", "workout"]
    work_kw = ["client", "meeting", "rdv", "call", "prospect", "linkedin", "mail", "travail", "business", "entreprise"]
    social_kw = ["famille", "ami", "diner", "déjeuner", "dej", "soirée", "sortie", "relation"]
    learn_kw = ["piano", "apprendre", "learning", "formation", "cours", "leçon", "lesson"]

    if any(k in text for k in health_kw):
        return "sante"
    if any(k in text for k in work_kw):
        return "travail"
    if any(k in text for k in social_kw):
        return "relationnel"
    if any(k in text for k in learn_kw):
        return "apprentissage"
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


def add_task(
    db_path: str | Path,
    title: str,
    category: str,
    start_at: str,
    end_at: str,
    notes: str | None = None,
    sync_to_apple: bool = False,
    apple_calendar_name: str | None = None,
) -> dict:
    """Crée une tâche planner locale, optionnellement sync Apple Calendar."""
    db_path = Path(db_path)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    calendar_uid = None
    source = "local"
    sync_error = None

    if sync_to_apple:
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
          (title, category, start_at, end_at, notes, status, source, calendar_uid, created_at, updated_at)
        VALUES (?,?,?,?,?,'planned',?,?,?,?)
        """,
        (
            title.strip(),
            normalize_category(category),
            start_at,
            end_at,
            notes.strip() if notes else None,
            source,
            calendar_uid,
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
        "start_at": start_at,
        "end_at": end_at,
        "source": source,
        "apple_uid": calendar_uid,
        "apple_sync_error": sync_error,
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
    """Fusionne planner_tasks + calendar_events dans une vue pilotage."""
    tasks = [dict(r) for r in conn.execute(
        """
        SELECT
          id, title, category, start_at, end_at, notes, status, source
        FROM planner_tasks
        WHERE status!='cancelled'
          AND start_at>=? AND start_at<=?
        ORDER BY start_at
        """,
        (start_at, end_at),
    ).fetchall()]

    cals = [dict(r) for r in conn.execute(
        """
        SELECT
          event_uid, title, calendar_name, start_at, end_at, notes, source
        FROM calendar_events
        WHERE start_at>=? AND start_at<=?
        ORDER BY start_at
        """,
        (start_at, end_at),
    ).fetchall()]

    rows: list[dict] = []
    for t in tasks:
        rows.append({
            "id": t.get("id"),
            "title": t.get("title") or "Tâche",
            "category": normalize_category(t.get("category")),
            "start_at": t.get("start_at"),
            "end_at": t.get("end_at"),
            "notes": t.get("notes"),
            "source": t.get("source") or "local",
            "calendar_name": None,
        })

    for e in cals:
        title = e.get("title") or "Événement"
        cal_name = e.get("calendar_name")
        rows.append({
            "id": e.get("event_uid"),
            "title": title,
            "category": infer_category(title, cal_name),
            "start_at": e.get("start_at"),
            "end_at": e.get("end_at"),
            "notes": e.get("notes"),
            "source": "apple_calendar",
            "calendar_name": cal_name,
        })

    rows.sort(key=lambda x: x.get("start_at") or "")
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
    training_h = [dict(r) for r in conn.execute(
        """
        SELECT strftime('%Y-W%W', started_at) AS week, ROUND(SUM(COALESCE(duration_s,0))/3600.0,2) AS value
        FROM activities
        WHERE started_at IS NOT NULL
        GROUP BY week
        ORDER BY week
        """
    ).fetchall()]

    steps_week = [dict(r) for r in conn.execute(
        """
        SELECT strftime('%Y-W%W', date) AS week, ROUND(SUM(value),0) AS value
        FROM health_metrics
        WHERE metric='steps'
        GROUP BY week
        ORDER BY week
        """
    ).fetchall()]

    sport_mix = [dict(r) for r in conn.execute(
        """
        SELECT type, ROUND(SUM(COALESCE(duration_s,0))/3600.0,2) AS hours
        FROM activities
        WHERE started_at IS NOT NULL
        GROUP BY type
        HAVING hours > 0
        ORDER BY hours DESC
        LIMIT 12
        """
    ).fetchall()]

    return {
        "training_hours_weekly": training_h,
        "steps_weekly": steps_week,
        "sport_mix_hours": sport_mix,
    }
