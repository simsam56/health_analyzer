"""Tests for analytics/training_load.py — TSS, PMC, ACWR, health metrics."""

import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from analytics.training_load import (
    _clamp,
    build_daily_tss,
    compute_acwr,
    compute_pmc,
    compute_wakeboard_score,
    tss_from_activity,
)
from pipeline.schema import init_db

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def db_path():
    """Create a temporary database with schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    conn = init_db(path)
    conn.close()
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def db_with_activities(db_path):
    """Database populated with sample activities and health metrics."""
    conn = sqlite3.connect(str(db_path))
    today = date.today()

    # Insert running activities over 30 days
    for i in range(30):
        d = today - timedelta(days=i)
        if i % 3 == 0:  # Every 3 days
            conn.execute(
                """INSERT INTO activities
                   (source, type, name, started_at, duration_s, distance_m, avg_hr, max_hr, calories, canonical_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "garmin_connect",
                    "Running",
                    "Morning Run",
                    f"{d}T07:00:00",
                    3600,
                    10000,
                    145,
                    175,
                    600,
                    f"running|{d}|3600",
                ),
            )

    # Insert strength sessions
    for i in range(0, 30, 4):
        d = today - timedelta(days=i)
        conn.execute(
            """INSERT INTO activities
               (source, type, name, started_at, duration_s, calories, canonical_key)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "garmin_connect",
                "Strength Training",
                "Muscu full body",
                f"{d}T18:00:00",
                3600,
                400,
                f"strength|{d}|3600",
            ),
        )

    # Insert health metrics
    for i in range(30):
        d = today - timedelta(days=i)
        ds = str(d)
        conn.execute(
            "INSERT OR IGNORE INTO health_metrics (date, metric, value, source) VALUES (?,?,?,?)",
            (ds, "hrv_sdnn", 45 + (i % 10), "garmin_connect"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO health_metrics (date, metric, value, source) VALUES (?,?,?,?)",
            (ds, "rhr", 52 + (i % 5), "garmin_connect"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO health_metrics (date, metric, value, source) VALUES (?,?,?,?)",
            (ds, "sleep_h", 7.0 + (i % 3) * 0.5, "garmin_connect"),
        )

    conn.commit()
    conn.close()
    return db_path


# ── Unit Tests: _clamp ───────────────────────────────────────────


def test_clamp_within_range():
    assert _clamp(5.0, 0.0, 10.0) == 5.0


def test_clamp_below_min():
    assert _clamp(-5.0, 0.0, 10.0) == 0.0


def test_clamp_above_max():
    assert _clamp(15.0, 0.0, 10.0) == 10.0


# ── Unit Tests: tss_from_activity ─────────────────────────────────


def test_tss_from_training_load():
    """When training_load is provided, use it directly."""
    row = {"training_load": 75.0, "type": "Running", "duration_s": 3600}
    assert tss_from_activity(row) == 75.0


def test_tss_from_hr():
    """TSS calculated from heart rate (TRIMP)."""
    row = {
        "type": "Running",
        "duration_s": 3600,
        "avg_hr": 150,
        "calories": 0,
        "name": "Run",
        "training_load": None,
        "strength_sets": 0,
    }
    tss = tss_from_activity(row, hr_rest=55, hr_max=190)
    assert tss > 0
    assert tss <= 300


def test_tss_from_strength():
    """Strength TSS from duration + neural fatigue multiplier."""
    row = {
        "type": "Strength Training",
        "name": "Muscu jambe",
        "duration_s": 3600,
        "avg_hr": 0,
        "calories": 0,
        "training_load": None,
        "strength_sets": 20,
    }
    tss = tss_from_activity(row)
    assert tss > 0
    # Jambe multiplier = 1.5, base = 1h * 40 = 40, sets density boost
    assert tss > 40


def test_tss_from_calories_fallback():
    """Fallback to calories when no HR data."""
    row = {
        "type": "Other",
        "name": "Activity",
        "duration_s": 3600,
        "avg_hr": 0,
        "calories": 500,
        "training_load": None,
        "strength_sets": 0,
    }
    tss = tss_from_activity(row)
    assert tss == pytest.approx(500 / 8.0, abs=1)


def test_tss_zero_duration():
    """Zero duration = zero TSS."""
    row = {
        "type": "Running",
        "name": "Run",
        "duration_s": 0,
        "avg_hr": 150,
        "calories": 0,
        "training_load": None,
        "strength_sets": 0,
    }
    assert tss_from_activity(row) == 0.0


# ── Integration Tests: build_daily_tss ────────────────────────────


def test_build_daily_tss(db_with_activities):
    conn = sqlite3.connect(str(db_with_activities))
    daily = build_daily_tss(conn)
    conn.close()

    assert len(daily) > 0
    # All TSS values should be non-negative
    assert all(v >= 0 for v in daily.values())


# ── Unit Tests: compute_pmc ──────────────────────────────────────


def test_pmc_empty():
    assert compute_pmc({}) == []


def test_pmc_basic():
    """PMC with constant daily TSS should converge."""
    today = date.today()
    daily_tss = {}
    for i in range(90):
        d = today - timedelta(days=90 - i)
        daily_tss[str(d)] = 50.0

    pmc = compute_pmc(daily_tss, end_date=today)
    assert len(pmc) > 0

    last = pmc[-1]
    # After 90 days of constant TSS=50, CTL/ATL should converge near 50
    # (start_date is 90 days before first data, so 180 days total to converge)
    assert 35 < last["ctl"] < 55
    assert 35 < last["atl"] < 55
    # TSB should be small when both converged
    assert -15 < last["tsb"] < 15


def test_pmc_spike_detection():
    """A spike in TSS should show in ATL before CTL."""
    today = date.today()
    daily_tss = {}
    for i in range(60):
        d = today - timedelta(days=60 - i)
        daily_tss[str(d)] = 30.0

    # Add a massive day
    daily_tss[str(today - timedelta(days=1))] = 200.0
    daily_tss[str(today)] = 0.0

    pmc = compute_pmc(daily_tss, end_date=today)
    last = pmc[-1]

    # ATL should be much higher than CTL after a spike
    assert last["atl"] > last["ctl"]
    # TSB should be negative (fatigued)
    assert last["tsb"] < 0


# ── Unit Tests: compute_acwr ─────────────────────────────────────


def test_acwr_empty():
    result = compute_acwr({})
    assert result["acwr"] == 0.0
    assert result["zone"] == "repos"


def test_acwr_optimal_zone():
    """Constant load should give ACWR ~1.0 (optimal)."""
    today = date.today()
    daily_tss = {}
    for i in range(120):
        d = today - timedelta(days=i)
        daily_tss[str(d)] = 50.0

    result = compute_acwr(daily_tss, end_date=today)
    assert 0.8 <= result["acwr"] <= 1.3
    assert result["zone"] == "optimal"


def test_acwr_danger_zone():
    """Large acute load after rest should give high ACWR."""
    today = date.today()
    daily_tss = {}
    # 4 weeks of low load
    for i in range(28, 120):
        d = today - timedelta(days=i)
        daily_tss[str(d)] = 10.0
    # Recent week: very high load
    for i in range(7):
        d = today - timedelta(days=i)
        daily_tss[str(d)] = 100.0

    result = compute_acwr(daily_tss, end_date=today)
    assert result["acwr"] > 1.3
    assert result["zone"] in ("élevé", "danger")


def test_acwr_has_both_methods():
    """ACWR result should contain both rolling and EWMA values."""
    today = date.today()
    daily_tss = {str(today - timedelta(days=i)): 50.0 for i in range(120)}
    result = compute_acwr(daily_tss, end_date=today)
    assert "acwr_roll" in result
    assert "acwr_ewma" in result
    assert "method" in result


# ── Unit Tests: compute_wakeboard_score ──────────────────────────


def test_wakeboard_score_excellent():
    result = compute_wakeboard_score(
        hrv_val=55.0,
        hrv_baseline=50.0,
        sleep_h=8.0,
        acwr_val=1.0,
        rhr_val=50,
        rhr_baseline=55,
        body_battery=90,
    )
    assert result["score"] >= 70
    assert result["label"] in ("Excellent", "Bon")
    assert "components" in result


def test_wakeboard_score_poor():
    result = compute_wakeboard_score(
        hrv_val=25.0,
        hrv_baseline=50.0,
        sleep_h=4.5,
        acwr_val=1.8,
        rhr_val=70,
        rhr_baseline=55,
        body_battery=15,
    )
    assert result["score"] < 55
    assert result["label"] in ("Faible", "Repos conseillé", "Moyen")


def test_wakeboard_score_no_data():
    """Without data, score should be neutral (~50-60)."""
    result = compute_wakeboard_score(
        hrv_val=None,
        hrv_baseline=None,
        sleep_h=None,
        acwr_val=0.0,
    )
    assert 30 <= result["score"] <= 70
    assert 0 <= result["confidence"] <= 1.0


def test_wakeboard_freshness_degrades():
    """Old data should push score toward neutral."""
    fresh = compute_wakeboard_score(
        hrv_val=60, hrv_baseline=50, sleep_h=8.0, acwr_val=1.0,
        freshness={"hrv": 1.0, "sleep": 1.0, "rhr": 1.0, "body_battery": 1.0},
    )
    stale = compute_wakeboard_score(
        hrv_val=60, hrv_baseline=50, sleep_h=8.0, acwr_val=1.0,
        freshness={"hrv": 0.0, "sleep": 0.0, "rhr": 0.0, "body_battery": 0.0},
    )
    # Fresh data should give a more extreme score (better or worse)
    assert abs(fresh["score"] - 50) > abs(stale["score"] - 50)
