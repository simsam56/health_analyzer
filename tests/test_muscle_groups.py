"""Tests for analytics/muscle_groups.py — Volume, imbalances, score."""

import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from analytics.muscle_groups import (
    _infer_muscles_from_text,
    analyze_imbalances,
    compute_muscle_score,
    get_cumulative_volume,
    normalize_muscle_name,
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


@pytest.fixture
def db_with_strength(db_path):
    """Database with strength training data."""
    conn = sqlite3.connect(str(db_path))
    today = date.today()

    # Create 2 strength sessions per week for 4 weeks
    session_id = 1
    for week in range(4):
        for day_offset in [0, 3]:  # Mon + Thu
            d = today - timedelta(weeks=week, days=day_offset)

            # Insert activity
            conn.execute(
                """INSERT INTO activities
                   (source, type, name, started_at, duration_s, canonical_key)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("strava_fit", "Strength Training", "Muscu", f"{d}T18:00:00", 3600, f"str|{d}|3600"),
            )
            activity_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Insert strength session
            conn.execute(
                """INSERT INTO strength_sessions
                   (activity_id, started_at, workout_name, duration_s, total_sets, total_reps, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (activity_id, f"{d}T18:00:00", "Full Body", 3600, 20, 160, "strava_fit"),
            )

            # Insert exercise sets
            muscles = [
                ("Pecs", "Bench Press"),
                ("Pecs", "Incline Press"),
                ("Dos", "Rowing"),
                ("Dos", "Pull-up"),
                ("Dos", "Deadlift"),
                ("Épaules", "Lateral Raise"),
                ("Biceps", "Curl"),
                ("Triceps", "Extension"),
                ("Jambes", "Squat"),
                ("Jambes", "Lunges"),
            ]
            for mg, ex_name in muscles:
                for set_idx in range(2):
                    conn.execute(
                        """INSERT INTO exercise_sets
                           (session_id, started_at, exercise_name, muscle_group, set_index,
                            set_type, reps, weight_kg)
                           VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
                        (session_id, f"{d}T18:{10 + set_idx * 3:02d}:00", ex_name, mg, set_idx, 10, 50),
                    )
            session_id += 1

    conn.commit()
    conn.close()
    return db_path


# ── Unit Tests: normalize_muscle_name ────────────────────────────


def test_normalize_epaules():
    assert normalize_muscle_name("Epaules") == "Épaules"


def test_normalize_none():
    assert normalize_muscle_name(None) == "Inconnu"


def test_normalize_valid():
    assert normalize_muscle_name("Pecs") == "Pecs"


# ── Unit Tests: _infer_muscles_from_text ─────────────────────────


def test_infer_bench():
    muscles = _infer_muscles_from_text("Bench Press Heavy")
    assert "Pecs" in muscles
    assert "Triceps" in muscles


def test_infer_squat():
    muscles = _infer_muscles_from_text("Squat and Lunges")
    assert "Jambes" in muscles


def test_infer_rowing():
    muscles = _infer_muscles_from_text("Cable Row + Traction")
    assert "Dos" in muscles
    assert "Biceps" in muscles


def test_infer_wakeboard():
    muscles = _infer_muscles_from_text("Séance wakeboard recovery")
    assert "Dos" in muscles
    assert "Core" in muscles


def test_infer_empty():
    assert _infer_muscles_from_text("") == []
    assert _infer_muscles_from_text(None) == []


# ── Integration Tests: get_cumulative_volume ─────────────────────


def test_cumulative_volume(db_with_strength):
    conn = sqlite3.connect(str(db_with_strength))
    volume = get_cumulative_volume(conn, weeks=4)
    conn.close()

    # Should have data for muscles we inserted
    assert "Pecs" in volume
    assert "Dos" in volume
    assert "Jambes" in volume
    assert volume["Pecs"]["total_sets"] > 0
    assert volume["Dos"]["total_sets"] > 0
    assert volume["Pecs"]["sets_per_week"] > 0


def test_cumulative_includes_missing_muscles(db_path):
    """Empty DB should still include all target muscles with zero volume."""
    conn = sqlite3.connect(str(db_path))
    volume = get_cumulative_volume(conn, weeks=4)
    conn.close()

    assert "Core" in volume
    assert volume["Core"]["total_sets"] == 0
    assert volume["Core"]["sets_per_week"] == 0


# ── Unit Tests: analyze_imbalances ───────────────────────────────


def test_imbalances_empty():
    """All zeros should trigger critical alerts."""
    volume = {mg: {"sets_per_week": 0} for mg in ["Pecs", "Dos", "Épaules", "Biceps", "Triceps", "Jambes", "Core"]}
    alerts = analyze_imbalances(volume)
    critical = [a for a in alerts if a["level"] == "critique"]
    assert len(critical) >= 5  # All muscles at zero


def test_imbalances_optimal():
    """Optimal volume should show optimal alerts."""
    volume = {
        "Pecs": {"sets_per_week": 12},
        "Dos": {"sets_per_week": 14},
        "Épaules": {"sets_per_week": 12},
        "Biceps": {"sets_per_week": 10},
        "Triceps": {"sets_per_week": 10},
        "Jambes": {"sets_per_week": 16},
        "Core": {"sets_per_week": 12},
    }
    alerts = analyze_imbalances(volume)
    optimal = [a for a in alerts if a["level"] == "optimal"]
    assert len(optimal) >= 5


def test_imbalances_detects_pecs_dos():
    """Detects Pecs/Dos imbalance when ratio is too low."""
    volume = {
        "Pecs": {"sets_per_week": 4},
        "Dos": {"sets_per_week": 14},
        "Épaules": {"sets_per_week": 12},
        "Biceps": {"sets_per_week": 10},
        "Triceps": {"sets_per_week": 10},
        "Jambes": {"sets_per_week": 16},
        "Core": {"sets_per_week": 12},
    }
    alerts = analyze_imbalances(volume)
    balance_alerts = [a for a in alerts if a["type"] == "balance"]
    assert len(balance_alerts) >= 1
    assert any("Pecs" in a["muscle"] for a in balance_alerts)


# ── Unit Tests: compute_muscle_score ─────────────────────────────


def test_muscle_score_perfect():
    volume = {
        "Pecs": {"sets_per_week": 15},
        "Dos": {"sets_per_week": 18},
        "Épaules": {"sets_per_week": 14},
        "Biceps": {"sets_per_week": 12},
        "Triceps": {"sets_per_week": 12},
        "Jambes": {"sets_per_week": 20},
        "Core": {"sets_per_week": 14},
    }
    score = compute_muscle_score(volume)
    assert score >= 90


def test_muscle_score_zero():
    volume = {mg: {"sets_per_week": 0} for mg in ["Pecs", "Dos", "Épaules", "Biceps", "Triceps", "Jambes", "Core"]}
    score = compute_muscle_score(volume)
    assert score == 0


def test_muscle_score_partial():
    volume = {
        "Pecs": {"sets_per_week": 6},
        "Dos": {"sets_per_week": 8},
        "Épaules": {"sets_per_week": 0},
        "Biceps": {"sets_per_week": 5},
        "Triceps": {"sets_per_week": 5},
        "Jambes": {"sets_per_week": 10},
        "Core": {"sets_per_week": 0},
    }
    score = compute_muscle_score(volume)
    assert 20 < score < 70
