"""Routes planner."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends

from analytics import planner
from api.deps import DB_PATH, invalidate_cache, require_auth
from integrations.apple_calendar import (
    diagnose_apple_calendar,
    sync_apple_calendar,
)

router = APIRouter(prefix="/api/planner", tags=["planner"])

PLANNER_WINDOW_DAYS = 120


def _window_bounds(
    start: str | None = None, end: str | None = None
) -> tuple[str, str]:
    if start and end:
        return start, end
    s = (date.today() - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00")
    e = (date.today() + timedelta(days=PLANNER_WINDOW_DAYS)).strftime(
        "%Y-%m-%dT23:59:59"
    )
    return s, e


def _validate_event_bounds(start_at: str, end_at: str) -> tuple[bool, str]:
    if not start_at or not end_at:
        return False, "missing_datetime"
    try:
        s = datetime.fromisoformat(str(start_at).replace("Z", ""))
        e = datetime.fromisoformat(str(end_at).replace("Z", ""))
    except Exception:
        return False, "invalid_datetime"
    if e <= s:
        return False, "end_before_start"
    if (e - s).total_seconds() > 60 * 60 * 24 * 3:
        return False, "duration_too_long"
    return True, ""


def _read_events(start_at: str | None = None, end_at: str | None = None) -> list[dict]:
    s, e = _window_bounds(start_at, end_at)
    return planner.get_planner_events_db(DB_PATH, start_at=s, end_at=e)


def _sync_calendar_soft() -> None:
    try:
        sync_apple_calendar(DB_PATH, days_ahead=PLANNER_WINDOW_DAYS)
    except Exception:
        pass


# ── GET ────────────────────────────────────────────────────────────


@router.get("/events")
def get_events(start: str | None = None, end: str | None = None) -> dict:
    events = _read_events(start_at=start, end_at=end)
    return {"ok": True, "events": events}


@router.get("/board")
def get_board() -> dict:
    tasks = planner.get_board_tasks_db(DB_PATH)
    return {"ok": True, "tasks": tasks}


@router.get("/health")
def health_check() -> dict:
    return {"ok": True, "status": "up"}


@router.get("/calendar/status")
def calendar_status() -> dict:
    diag = diagnose_apple_calendar()
    return {
        "ok": diag.get("enabled", False),
        "permission": diag.get("permission", "unknown"),
        "error": diag.get("error"),
        "eventkit": diag.get("eventkit", "unknown"),
        "calendars_count": diag.get("calendars_count", 0),
        "default_calendar": diag.get("default_calendar"),
    }


@router.get("/calendar/debug")
def calendar_debug(_: None = Depends(require_auth)) -> dict:
    return {"ok": True, "debug": diagnose_apple_calendar(db_path=DB_PATH)}


@router.get("/agent/capabilities")
def agent_capabilities() -> dict:
    return {
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
            "lundi", "mardi", "mercredi", "jeudi",
            "vendredi", "samedi", "dimanche",
        ],
    }


# ── POST ───────────────────────────────────────────────────────────


@router.post("/tasks", status_code=201)
def create_task(
    body: dict[str, Any],
    background_tasks: BackgroundTasks,
    _: None = Depends(require_auth),
) -> dict:
    title = str(body.get("title") or "").strip() or "Tâche"
    title = title[:120]
    task_type = str(body.get("type") or "autre")
    type_map = {
        "cardio": "sport", "musculation": "sport", "mobilite": "yoga",
        "sport_libre": "sport", "travail": "travail",
        "apprentissage": "formation", "formation": "formation",
        "relationnel": "social", "social": "social",
        "yoga": "yoga", "autre": "autre",
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

    if not start_at and body.get("task_date"):
        task_date = str(body.get("task_date") or date.today())
        task_time = str(body.get("task_time") or body.get("time") or "09:00:00")
        dur = int(body.get("duration_min") or body.get("duration") or 60)
        start_at, end_at = planner.parse_task_datetime(task_date, task_time, dur)
        scheduled = True

    if start_at and end_at:
        ok_bounds, err = _validate_event_bounds(str(start_at), str(end_at))
        if not ok_bounds:
            return {"ok": False, "error": err}

    sync_apple = bool(body.get("sync_apple", bool(start_at)))
    calendar_name = body.get("calendar_name")

    created = planner.add_task(
        db_path=DB_PATH,
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
        background_tasks.add_task(_sync_calendar_soft)

    events = _read_events()
    board = planner.get_board_tasks_db(DB_PATH)
    return {"ok": True, "created": created, "events": events, "board": board}


@router.post("/tasks/batch")
def create_tasks_batch(
    body: dict[str, Any],
    background_tasks: BackgroundTasks,
    _: None = Depends(require_auth),
) -> dict:
    tasks = body.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return {"ok": False, "error": "missing_tasks"}
    if len(tasks) > 100:
        return {"ok": False, "error": "too_many_tasks"}

    defaults = body.get("defaults") or {}
    default_sync_apple = bool(defaults.get("sync_apple", True))
    default_calendar_name = defaults.get("calendar_name")
    res = planner.add_tasks_batch(
        db_path=DB_PATH,
        tasks=tasks,
        default_sync_apple=default_sync_apple,
        default_calendar_name=default_calendar_name,
    )
    if default_sync_apple:
        background_tasks.add_task(_sync_calendar_soft)
    events = _read_events()
    status = 201 if res.get("ok") else 207
    return {"ok": bool(res.get("ok")), "result": res, "events": events}


@router.post("/calendar/sync")
def sync_calendar(
    background_tasks: BackgroundTasks,
    _: None = Depends(require_auth),
) -> dict:
    sync_result: dict = {}
    try:
        sync_result = sync_apple_calendar(DB_PATH, days_ahead=PLANNER_WINDOW_DAYS)
    except Exception:
        pass
    events = _read_events()
    return {"ok": True, "events": events, "sync": sync_result}


@router.post("/calendar/push")
def push_calendar(
    background_tasks: BackgroundTasks,
    _: None = Depends(require_auth),
) -> dict:
    push = planner.sync_pending_tasks_to_apple(db_path=DB_PATH, limit=300)
    background_tasks.add_task(_sync_calendar_soft)
    events = _read_events()
    return {"ok": bool(push.get("ok")), "result": push, "events": events}


# ── PATCH ──────────────────────────────────────────────────────────


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: int,
    body: dict[str, Any],
    background_tasks: BackgroundTasks,
    _: None = Depends(require_auth),
) -> dict:
    notes = body.get("notes") if "notes" in body else None
    if notes is not None:
        notes = str(notes)[:5000]

    sync_apple = bool(body.get("sync_apple", True))
    start_at = body.get("start_at") or body.get("scheduled_start")
    end_at = body.get("end_at") or body.get("scheduled_end")
    scheduled = body.get("scheduled")
    sch_date = body.get("scheduled_date")
    sch_start = body.get("scheduled_start") or start_at
    sch_end = body.get("scheduled_end") or end_at
    last_bucket = body.get("last_bucket_before_scheduling")
    triage_status = body.get("triage_status")

    if start_at and end_at:
        ok_bounds, err = _validate_event_bounds(str(start_at), str(end_at))
        if not ok_bounds:
            return {"ok": False, "error": err}

    res = planner.update_task(
        db_path=DB_PATH,
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
        return {"ok": False, "error": res.get("error", "task_not_found")}
    if sync_apple:
        background_tasks.add_task(_sync_calendar_soft)
    events = _read_events()
    board = planner.get_board_tasks_db(DB_PATH)
    return {"ok": True, "result": res, "events": events, "board": board}


@router.patch("/apple/{uid:path}")
def update_apple_event(
    uid: str,
    body: dict[str, Any],
    background_tasks: BackgroundTasks,
    _: None = Depends(require_auth),
) -> dict:
    ok, err = _validate_event_bounds(
        str(body.get("start_at") or ""), str(body.get("end_at") or "")
    )
    if not ok:
        return {"ok": False, "error": err}
    res = planner.update_apple_only_event(
        event_uid=uid,
        title=str(body.get("title") or "Événement")[:120],
        start_at=str(body.get("start_at") or ""),
        end_at=str(body.get("end_at") or ""),
        notes=body.get("notes"),
    )
    background_tasks.add_task(_sync_calendar_soft)
    events = _read_events()
    return {"ok": bool(res.get("enabled")), "result": res, "events": events}


# ── DELETE ─────────────────────────────────────────────────────────


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_auth),
) -> dict:
    res = planner.delete_task(DB_PATH, task_id=task_id, sync_apple=True)
    background_tasks.add_task(_sync_calendar_soft)
    events = _read_events()
    board = planner.get_board_tasks_db(DB_PATH)
    return {"ok": bool(res.get("ok")), "result": res, "events": events, "board": board}


@router.delete("/apple/{uid:path}")
def delete_apple_event(
    uid: str,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_auth),
) -> dict:
    res = planner.delete_apple_only_event(uid, db_path=DB_PATH)
    background_tasks.add_task(_sync_calendar_soft)
    events = _read_events()
    return {"ok": bool(res.get("enabled")), "result": res, "events": events}
