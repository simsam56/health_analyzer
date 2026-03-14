"""Tests for analytics/planner.py — Task management, scheduling, categories."""

import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from analytics.planner import (
    add_task,
    delete_task,
    get_board_tasks_db,
    infer_category,
    normalize_category,
    normalize_triage_status,
    parse_hhmm,
    parse_relative_slot,
    parse_weekday,
    update_task,
    week_start_from_ref,
)
from pipeline.schema import init_db


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    conn = init_db(path)
    conn.close()
    yield path
    path.unlink(missing_ok=True)


# ── Unit Tests: normalize_category ───────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("sport", "sport"),
        ("Sport", "sport"),
        ("sante", "sport"),
        ("santé", "sport"),
        ("yoga", "yoga"),
        ("travail", "travail"),
        ("work", "travail"),
        ("social", "social"),
        ("relationnel", "social"),
        ("formation", "formation"),
        ("apprentissage", "formation"),
        ("unknown", "autre"),
        (None, "autre"),
        ("", "autre"),
    ],
)
def test_normalize_category(raw, expected):
    assert normalize_category(raw) == expected


# ── Unit Tests: normalize_triage_status ──────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("urgent", "urgent"),
        ("a_planifier", "a_planifier"),
        ("planned", "a_planifier"),
        ("done", "termine"),
        ("termine", "termine"),
        ("non_urgent", "non_urgent"),
        ("later", "non_urgent"),
        (None, "a_determiner"),
        ("", "a_determiner"),
        ("random", "a_determiner"),
    ],
)
def test_normalize_triage_status(raw, expected):
    assert normalize_triage_status(raw) == expected


# ── Unit Tests: infer_category ───────────────────────────────────


def test_infer_sport():
    assert infer_category("Course 10km") == "sport"
    assert infer_category("Séance muscu") == "sport"


def test_infer_yoga():
    assert infer_category("Yoga matinal") == "yoga"
    assert infer_category("Séance méditation") == "yoga"


def test_infer_travail():
    assert infer_category("Meeting client") == "travail"
    assert infer_category("RDV prospect") == "travail"


def test_infer_social():
    assert infer_category("Dîner famille") == "social"
    assert infer_category("Sortie amis") == "social"


def test_infer_formation():
    assert infer_category("Cours piano") == "formation"
    assert infer_category("Formation Python") == "formation"


def test_infer_other():
    assert infer_category("Random stuff") == "autre"


def test_infer_with_calendar():
    assert infer_category("Entraînement", "Sport") == "sport"


# ── Unit Tests: parse_weekday ────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("lundi", 0),
        ("monday", 0),
        ("mardi", 1),
        ("dimanche", 6),
        (3, 3),
        ("3", 3),
        (None, 0),
    ],
)
def test_parse_weekday(raw, expected):
    assert parse_weekday(raw) == expected


# ── Unit Tests: parse_hhmm ──────────────────────────────────────


def test_parse_hhmm_normal():
    assert parse_hhmm("14:30") == "14:30:00"


def test_parse_hhmm_with_seconds():
    assert parse_hhmm("14:30:00") == "14:30:00"


def test_parse_hhmm_fallback():
    assert parse_hhmm(None) == "09:00:00"
    assert parse_hhmm("invalid") == "09:00:00"


# ── Unit Tests: week_start_from_ref ──────────────────────────────


def test_week_start_this_week():
    today = date.today()
    expected = today - timedelta(days=today.weekday())
    assert week_start_from_ref("this_week") == expected


def test_week_start_next_week():
    today = date.today()
    expected = today - timedelta(days=today.weekday()) + timedelta(days=7)
    assert week_start_from_ref("next_week") == expected


def test_week_start_french():
    today = date.today()
    expected = today - timedelta(days=today.weekday()) + timedelta(days=7)
    assert week_start_from_ref("semaine_prochaine") == expected


# ── Unit Tests: parse_relative_slot ──────────────────────────────


def test_parse_relative_slot():
    base = date(2026, 3, 9)  # Monday (Mar 9 2026 is a Monday)
    start, end = parse_relative_slot(
        week_ref="this_week",
        weekday="mardi",
        task_time="14:00",
        duration_min=60,
        base_day=base,
    )
    assert start == "2026-03-10T14:00:00"
    assert end == "2026-03-10T15:00:00"


def test_parse_relative_slot_next_week():
    base = date(2026, 3, 9)  # Monday
    start, end = parse_relative_slot(
        week_ref="next_week",
        weekday="vendredi",
        task_time="09:00",
        duration_min=90,
        base_day=base,
    )
    assert start == "2026-03-20T09:00:00"
    assert end == "2026-03-20T10:30:00"


# ── Integration Tests: CRUD ──────────────────────────────────────


def test_add_task(db_path):
    result = add_task(
        db_path=db_path,
        title="Test Task",
        category="sport",
        start_at="2026-03-15T10:00:00",
        end_at="2026-03-15T11:00:00",
        sync_to_apple=False,
    )
    assert result["task_id"] is not None
    assert result["category"] == "sport"
    assert result["scheduled"] is True


def test_add_task_no_dates(db_path):
    result = add_task(
        db_path=db_path,
        title="Board Task",
        category="travail",
        sync_to_apple=False,
    )
    assert result["task_id"] is not None
    assert result["category"] == "travail"


def test_update_task(db_path):
    created = add_task(
        db_path=db_path,
        title="Original",
        category="sport",
        start_at="2026-03-15T10:00:00",
        end_at="2026-03-15T11:00:00",
        sync_to_apple=False,
    )
    result = update_task(
        db_path=db_path,
        task_id=created["task_id"],
        title="Updated Title",
        category="yoga",
        sync_apple=False,
    )
    assert result["ok"] is True

    # Verify in DB
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT title, category FROM planner_tasks WHERE id=?", (created["task_id"],)
    ).fetchone()
    conn.close()
    assert row[0] == "Updated Title"
    assert row[1] == "yoga"


def test_delete_task(db_path):
    created = add_task(
        db_path=db_path,
        title="To Delete",
        category="autre",
        sync_to_apple=False,
    )
    result = delete_task(db_path=db_path, task_id=created["task_id"], sync_apple=False)
    assert result["ok"] is True

    # Verify deleted
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT id FROM planner_tasks WHERE id=?", (created["task_id"],)
    ).fetchone()
    conn.close()
    assert row is None


def test_delete_nonexistent(db_path):
    result = delete_task(db_path=db_path, task_id=99999, sync_apple=False)
    assert result["ok"] is False


def test_get_board_tasks(db_path):
    add_task(db_path=db_path, title="Board 1", category="travail", sync_to_apple=False)
    add_task(db_path=db_path, title="Board 2", category="sport", sync_to_apple=False, triage_status="urgent")

    tasks = get_board_tasks_db(db_path)
    assert len(tasks) >= 2
    # Both tasks should be present with correct triage status
    statuses = {t["title"]: t["triage_status"] for t in tasks}
    assert statuses.get("Board 2") == "urgent"
