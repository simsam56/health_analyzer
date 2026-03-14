"""Routes calendrier Apple (port depuis cockpit_server.py)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.deps import DB_PATH, require_auth
from integrations.apple_calendar import (
    create_apple_calendar_event,
    diagnose_apple_calendar,
    get_upcoming_events,
    sync_apple_calendar,
)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/status")
def calendar_status() -> dict:
    status = diagnose_apple_calendar(DB_PATH)
    return {"ok": True, "calendar": status}


@router.get("/events")
def get_events(days: int = 30, _: None = Depends(require_auth)) -> dict:
    try:
        events = get_upcoming_events(db_path=DB_PATH, days_ahead=days, limit=100)
    except Exception:
        events = []
    return {"ok": True, "events": events}


@router.get("/sync")
def sync_calendar(days: int = 30, _: None = Depends(require_auth)) -> dict:
    result = sync_apple_calendar(db_path=DB_PATH, days_ahead=days)
    return {"ok": result.get("enabled", False), "sync": result}


@router.post("/create", status_code=201)
def create_event(body: dict[str, Any], _: None = Depends(require_auth)) -> dict:
    title = str(body.get("title", "")).strip()
    start_at = body.get("start_at")
    end_at = body.get("end_at")
    notes = body.get("notes")
    location = body.get("location")
    calendar_name = body.get("calendar_name")

    if not title or not start_at or not end_at:
        return {"ok": False, "error": "missing_required_fields"}

    result = create_apple_calendar_event(
        title=title,
        start_at=start_at,
        end_at=end_at,
        notes=notes,
        location=location,
        calendar_name=calendar_name,
    )

    if result.get("enabled"):
        sync_apple_calendar(db_path=DB_PATH, days_ahead=30)
        events = get_upcoming_events(db_path=DB_PATH, days_ahead=30, limit=100)
        return {"ok": True, "created": result, "events": events}
    return {"ok": False, "error": result.get("error", "creation_failed")}
