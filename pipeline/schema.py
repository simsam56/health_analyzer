"""
schema.py — PerformOS v3 · Schéma SQLite complet
"""
import sqlite3
from pathlib import Path


DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ──────────────────────────────────────────────────────────────
-- Activités (toutes sources)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activities (
    id            INTEGER PRIMARY KEY,
    source        TEXT NOT NULL,          -- strava_fit | apple_health | garmin_api
    source_id     TEXT,                   -- ID externe
    type          TEXT,                   -- Running | Strength Training | ...
    name          TEXT,
    started_at    TEXT,                   -- ISO8601
    duration_s    INTEGER,
    distance_m    REAL,
    elev_gain_m   REAL,
    calories      INTEGER,
    avg_hr        REAL,
    max_hr        REAL,
    avg_pace_mpm  REAL,
    tss_proxy     REAL,
    training_load REAL,
    canonical_key TEXT UNIQUE            -- dédup
);

-- ──────────────────────────────────────────────────────────────
-- Sessions musculation
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strength_sessions (
    id           INTEGER PRIMARY KEY,
    activity_id  INTEGER REFERENCES activities(id),
    started_at   TEXT,
    workout_name TEXT,
    duration_s   INTEGER,
    total_sets   INTEGER,
    total_reps   INTEGER,
    source       TEXT
);

-- ──────────────────────────────────────────────────────────────
-- Séries d'exercices
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exercise_sets (
    id               INTEGER PRIMARY KEY,
    session_id       INTEGER REFERENCES strength_sessions(id),
    started_at       TEXT,
    exercise_name    TEXT,
    exercise_category TEXT,
    muscle_group     TEXT,
    muscle_subgroup  TEXT,
    set_index        INTEGER,
    set_type         TEXT,
    reps             INTEGER,
    duration_s       REAL,
    weight_kg        REAL
);

-- ──────────────────────────────────────────────────────────────
-- Métriques de santé journalières (HRV, RHR, sleep, steps...)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS health_metrics (
    id      INTEGER PRIMARY KEY,
    date    TEXT NOT NULL,
    metric  TEXT NOT NULL,
    value   REAL,
    source  TEXT,
    UNIQUE(date, metric, source)
);

-- ──────────────────────────────────────────────────────────────
-- Charge d'entraînement quotidienne (TSS, CTL, ATL, TSB)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_load (
    date       TEXT PRIMARY KEY,
    tss        REAL,
    ctl        REAL,
    atl        REAL,
    tsb        REAL,
    activity_count INTEGER
);

-- ──────────────────────────────────────────────────────────────
-- Volume musculaire hebdomadaire
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weekly_muscle_volume (
    id           INTEGER PRIMARY KEY,
    week_start   TEXT,
    muscle_group TEXT,
    total_sets   INTEGER,
    total_reps   INTEGER,
    UNIQUE(week_start, muscle_group)
);

-- ──────────────────────────────────────────────────────────────
-- Événements agenda (Apple Calendar)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calendar_events (
    id            INTEGER PRIMARY KEY,
    event_uid     TEXT NOT NULL,
    calendar_name TEXT,
    title         TEXT,
    location      TEXT,
    notes         TEXT,
    start_at      TEXT NOT NULL,
    end_at        TEXT,
    is_all_day    INTEGER DEFAULT 0,
    source        TEXT DEFAULT 'apple_calendar',
    updated_at    TEXT,
    UNIQUE(event_uid, start_at)
);

-- ──────────────────────────────────────────────────────────────
-- Pilotage: tâches planifiées (santé/travail/relationnel/apprentissage)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS planner_tasks (
    id            INTEGER PRIMARY KEY,
    title         TEXT NOT NULL,
    category      TEXT NOT NULL,          -- sante | travail | relationnel | apprentissage | autre
    start_at      TEXT NOT NULL,
    end_at        TEXT NOT NULL,
    notes         TEXT,
    status        TEXT DEFAULT 'planned', -- planned | done | cancelled
    source        TEXT DEFAULT 'local',   -- local | apple_calendar
    calendar_uid  TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────────────────────────
-- Indices
-- ──────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_activities_started   ON activities(started_at);
CREATE INDEX IF NOT EXISTS idx_activities_type      ON activities(type);
CREATE INDEX IF NOT EXISTS idx_health_metrics_date  ON health_metrics(date);
CREATE INDEX IF NOT EXISTS idx_health_metrics_metric ON health_metrics(metric);
CREATE INDEX IF NOT EXISTS idx_exercise_sets_session ON exercise_sets(session_id);
CREATE INDEX IF NOT EXISTS idx_exercise_sets_muscle  ON exercise_sets(muscle_group);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(start_at);
CREATE INDEX IF NOT EXISTS idx_calendar_events_cal   ON calendar_events(calendar_name);
CREATE INDEX IF NOT EXISTS idx_planner_tasks_start   ON planner_tasks(start_at);
CREATE INDEX IF NOT EXISTS idx_planner_tasks_cat     ON planner_tasks(category);
"""


def init_db(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(DDL)
    conn.commit()
    return conn


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn
