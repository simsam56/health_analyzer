"""Seed athlete.db with realistic demo data for development."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from pipeline.schema import init_db

DB = Path("athlete.db")


def seed():
    conn = init_db(DB)
    cur = conn.cursor()

    today = date.today()

    # ── Health metrics (last 30 days) ──
    metrics = []
    for i in range(30):
        d = (today - timedelta(days=i)).isoformat()
        metrics += [
            (d, "hrv_sdnn", 42 + (i % 7) * 3, "garmin"),
            (d, "rhr", 52 + (i % 5), "garmin"),
            (d, "sleep_h", 6.5 + (i % 4) * 0.5, "apple_health"),
            (d, "vo2max", 48.5 - (i % 3) * 0.5, "garmin"),
            (d, "body_battery", 60 + (i % 6) * 5, "garmin"),
            (d, "weight_kg", 72.0 + (i % 3) * 0.2, "apple_health"),
        ]
    cur.executemany(
        "INSERT OR IGNORE INTO health_metrics (date, metric, value, source) VALUES (?,?,?,?)",
        metrics,
    )

    # ── Activities (last 8 weeks) ──
    activity_templates = [
        ("Running", "Course matinale", 2400, 8000, 145, 65),
        ("Running", "Footing récup", 1800, 5000, 130, 40),
        ("Strength Training", "Muscu upper body", 3600, None, 120, 55),
        ("Strength Training", "Muscu lower body", 3600, None, 125, 60),
        ("Cycling", "Sortie vélo", 5400, 30000, 140, 80),
        ("Yoga", "Yoga flow", 2700, None, 90, 20),
        ("Swimming", "Natation", 2700, 2000, 135, 50),
    ]
    activities = []
    for week in range(8):
        for day_offset in [0, 1, 3, 4, 6]:  # 5 sessions / week
            d = today - timedelta(weeks=week, days=day_offset)
            t = activity_templates[(week * 5 + day_offset) % len(activity_templates)]
            started = datetime(d.year, d.month, d.day, 7, 30).isoformat()
            activities.append((
                "garmin_api",
                f"garmin_{d.isoformat()}_{t[0]}",
                t[0], t[1], started, t[2], t[3], int(t[2] / 10),
                t[4], t[4] + 20, None, t[5], t[5],
                f"{d.isoformat()}_{t[0][:3]}_{t[2]}",
            ))

    cur.executemany(
        """INSERT OR IGNORE INTO activities
           (source, source_id, type, name, started_at, duration_s, distance_m,
            calories, avg_hr, max_hr, avg_pace_mpm, tss_proxy, training_load, canonical_key)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        activities,
    )

    # ── Planner tasks ──
    tasks = [
        ("Revue code projet Bord", "travail", "planned", "a_planifier", 1,
         (today + timedelta(days=1)).isoformat(),
         f"{(today + timedelta(days=1)).isoformat()}T09:00:00",
         f"{(today + timedelta(days=1)).isoformat()}T11:00:00"),
        ("Appel client X", "travail", "planned", "urgent", 1,
         today.isoformat(),
         f"{today.isoformat()}T14:00:00",
         f"{today.isoformat()}T15:00:00"),
        ("Yoga matinal", "sport", "planned", "a_planifier", 1,
         today.isoformat(),
         f"{today.isoformat()}T07:00:00",
         f"{today.isoformat()}T08:00:00"),
        ("Course 10k", "sport", "planned", "a_planifier", 1,
         (today + timedelta(days=2)).isoformat(),
         f"{(today + timedelta(days=2)).isoformat()}T07:30:00",
         f"{(today + timedelta(days=2)).isoformat()}T08:30:00"),
        ("Déjeuner avec Marc", "social", "planned", "a_planifier", 1,
         (today + timedelta(days=3)).isoformat(),
         f"{(today + timedelta(days=3)).isoformat()}T12:00:00",
         f"{(today + timedelta(days=3)).isoformat()}T13:30:00"),
        ("Formation Rust", "formation", "planned", "a_planifier", 1,
         (today + timedelta(days=4)).isoformat(),
         f"{(today + timedelta(days=4)).isoformat()}T10:00:00",
         f"{(today + timedelta(days=4)).isoformat()}T12:00:00"),
        ("Lire article IA santé", "autre", "planned", "a_determiner", 0, None, None, None),
        ("Explorer API Garmin v2", "travail", "planned", "a_determiner", 0, None, None, None),
        ("Idée: tracker sommeil", "autre", "planned", "a_determiner", 0, None, None, None),
    ]
    for t in tasks:
        cur.execute(
            """INSERT INTO planner_tasks
               (title, category, status, triage_status, scheduled,
                scheduled_date, scheduled_start, scheduled_end)
               VALUES (?,?,?,?,?,?,?,?)""",
            t,
        )

    # ── Strength sessions + exercises ──
    muscle_groups = [
        ("Bench Press", "chest", "upper_chest"),
        ("Overhead Press", "shoulders", "front_delt"),
        ("Pull-ups", "back", "lats"),
        ("Barbell Row", "back", "mid_back"),
        ("Squat", "legs", "quads"),
        ("Deadlift", "legs", "hamstrings"),
        ("Bicep Curl", "arms", "biceps"),
        ("Tricep Pushdown", "arms", "triceps"),
    ]
    for week in range(4):
        for day_offset in [1, 4]:  # 2 muscu sessions / week
            d = today - timedelta(weeks=week, days=day_offset)
            started = datetime(d.year, d.month, d.day, 8, 0).isoformat()
            cur.execute(
                """INSERT INTO strength_sessions
                   (started_at, workout_name, duration_s, total_sets, total_reps, source)
                   VALUES (?,?,?,?,?,?)""",
                (started, "Full Body" if day_offset == 1 else "Upper/Lower", 3600, 20, 160, "garmin"),
            )
            session_id = cur.lastrowid
            exercises = muscle_groups[:4] if day_offset == 1 else muscle_groups[4:]
            for idx, (name, group, subgroup) in enumerate(exercises):
                for s in range(4):
                    cur.execute(
                        """INSERT INTO exercise_sets
                           (session_id, started_at, exercise_name, exercise_category,
                            muscle_group, muscle_subgroup, set_index, set_type, reps, weight_kg)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (session_id, started, name, "strength", group, subgroup, s + 1, "working", 10, 40 + idx * 5),
                    )

    conn.commit()
    conn.close()
    print(f"✅ Demo data seeded into {DB}")


if __name__ == "__main__":
    seed()
