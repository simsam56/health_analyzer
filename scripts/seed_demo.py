"""
seed_demo.py — Generate a realistic demo SQLite database for the Cockpit dashboard.
"""

import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.schema import init_db

DB_PATH = Path(__file__).resolve().parent.parent / "athlete.db"

random.seed(42)

# ── Helpers ───────────────────────────────────────────────────────

def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")

def date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def week_start(dt: datetime) -> str:
    return date_str(dt - timedelta(days=dt.weekday()))


# ── Main ──────────────────────────────────────────────────────────

def seed():
    conn = init_db(DB_PATH)
    cur = conn.cursor()
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ── 1. Activities (90 days) ──────────────────────────────────
    activity_types = [
        ("Running", 30, 60, 5, 12),          # min_dur, max_dur, min_dist_km, max_dist_km
        ("Strength Training", 40, 75, 0, 0),
        ("Cycling", 45, 120, 15, 50),
        ("Yoga", 30, 60, 0, 0),
        ("Swimming", 30, 60, 1, 3),
        ("Hiking", 60, 180, 5, 15),
    ]
    activity_id = 0
    session_id = 0

    for day_offset in range(90, -1, -1):
        dt = today - timedelta(days=day_offset)
        # 0-3 activities per day, weighted toward 1
        n_activities = random.choices([0, 1, 2, 3], weights=[15, 50, 25, 10])[0]
        for _ in range(n_activities):
            atype, min_d, max_d, min_km, max_km = random.choice(activity_types)
            dur_min = random.randint(min_d, max_d)
            dist_m = random.uniform(min_km, max_km) * 1000 if max_km > 0 else None
            start = dt + timedelta(hours=random.choice([6, 7, 8, 12, 17, 18, 19]),
                                   minutes=random.randint(0, 59))
            avg_hr = random.randint(110, 170) if atype != "Yoga" else random.randint(70, 100)
            max_hr = avg_hr + random.randint(10, 30)
            pace = (dur_min * 60 / (dist_m / 1000)) / 60 if dist_m else None  # min/km
            tss = random.uniform(30, 150)
            calories = int(dur_min * random.uniform(5, 12))

            activity_id += 1
            cur.execute("""
                INSERT INTO activities (id, source, type, name, started_at, duration_s,
                    distance_m, calories, avg_hr, max_hr, avg_pace_mpm, tss_proxy, training_load, canonical_key)
                VALUES (?, 'demo', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (activity_id, atype,
                  f"{atype} {date_str(dt)}",
                  iso(start), dur_min * 60,
                  dist_m, calories, avg_hr, max_hr,
                  pace, tss, tss,
                  f"demo_{activity_id}"))

            # Strength sessions
            if atype == "Strength Training":
                session_id += 1
                muscles = ["Pecs", "Dos", "Épaules", "Biceps", "Triceps", "Quadriceps",
                           "Ischio-jambiers", "Mollets", "Abdos", "Fessiers"]
                n_exercises = random.randint(4, 8)
                total_sets = 0
                total_reps = 0

                # Collect sets first
                sets_data = []
                for ex_i in range(n_exercises):
                    mg = random.choice(muscles)
                    n_sets = random.randint(3, 5)
                    for s in range(n_sets):
                        reps = random.randint(6, 15)
                        weight = round(random.uniform(10, 80), 1)
                        total_sets += 1
                        total_reps += reps
                        sets_data.append((session_id, iso(start), f"Exercise {ex_i+1}", mg,
                                          s + 1, reps, weight))

                # Insert session first (parent), then sets (children)
                cur.execute("""
                    INSERT INTO strength_sessions
                        (id, activity_id, started_at, workout_name, duration_s, total_sets, total_reps, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'demo')
                """, (session_id, activity_id, iso(start), f"Musculation {date_str(dt)}",
                      dur_min * 60, total_sets, total_reps))

                for sd in sets_data:
                    cur.execute("""
                        INSERT INTO exercise_sets
                            (session_id, started_at, exercise_name, muscle_group,
                             set_index, set_type, reps, weight_kg)
                        VALUES (?, ?, ?, ?, ?, 'normal', ?, ?)
                    """, sd)

    # ── 2. Health metrics (90 days) ──────────────────────────────
    base_hrv = 45
    base_rhr = 58
    for day_offset in range(90, -1, -1):
        dt = today - timedelta(days=day_offset)
        d = date_str(dt)
        metrics = [
            ("hrv", base_hrv + random.uniform(-15, 15) + day_offset * 0.05),
            ("rhr", base_rhr + random.uniform(-5, 5)),
            ("sleep_hours", round(random.uniform(5.5, 8.5), 1)),
            ("vo2max", round(42 + random.uniform(-2, 3), 1)),
            ("body_battery", random.randint(30, 95)),
            ("steps", random.randint(3000, 15000)),
        ]
        for metric, value in metrics:
            cur.execute("""
                INSERT OR IGNORE INTO health_metrics (date, metric, value, source)
                VALUES (?, ?, ?, 'demo')
            """, (d, metric, round(value, 2)))

    # ── 3. Daily load (PMC) ──────────────────────────────────────
    ctl = 35.0
    atl = 30.0
    for day_offset in range(90, -1, -1):
        dt = today - timedelta(days=day_offset)
        d = date_str(dt)
        # Count activities for this day
        cur.execute("SELECT COUNT(*), COALESCE(SUM(tss_proxy),0) FROM activities WHERE substr(started_at,1,10)=?", (d,))
        count, day_tss = cur.fetchone()
        day_tss = day_tss or 0
        ctl = ctl + (day_tss - ctl) / 42
        atl = atl + (day_tss - atl) / 7
        tsb = ctl - atl
        cur.execute("""
            INSERT OR REPLACE INTO daily_load (date, tss, ctl, atl, tsb, activity_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (d, day_tss, round(ctl, 2), round(atl, 2), round(tsb, 2), count))

    # ── 4. Weekly muscle volume ──────────────────────────────────
    for day_offset in range(0, 91, 7):
        ws = week_start(today - timedelta(days=day_offset))
        ws_end = date_str(datetime.strptime(ws, "%Y-%m-%d") + timedelta(days=7))
        cur.execute("""
            SELECT muscle_group, COUNT(*), SUM(reps)
            FROM exercise_sets es
            JOIN strength_sessions ss ON es.session_id = ss.id
            WHERE ss.started_at >= ? AND ss.started_at < ?
            GROUP BY muscle_group
        """, (ws, ws_end))
        for mg, sets, reps in cur.fetchall():
            cur.execute("""
                INSERT OR REPLACE INTO weekly_muscle_volume (week_start, muscle_group, total_sets, total_reps)
                VALUES (?, ?, ?, ?)
            """, (ws, mg, sets, reps))

    # ── 5. Planner tasks ─────────────────────────────────────────
    categories = ["sport", "travail", "formation", "social", "yoga"]
    statuses = ["planned", "done", "done", "done", "cancelled"]
    triage_statuses = ["urgent", "a_planifier", "non_urgent", "termine", "a_determiner"]

    for i in range(30):
        cat = random.choice(categories)
        day_off = random.randint(-3, 10)
        dt = today + timedelta(days=day_off, hours=random.randint(8, 20))
        titles = {
            "sport": ["Running 10k", "Musculation haut", "Vélo route", "Natation", "HIIT"],
            "travail": ["Code review", "Sprint planning", "Deploy v2", "Bug fix API", "Meeting client"],
            "formation": ["Cours Rust", "Lecture ML paper", "Workshop DevOps", "Kata Python"],
            "social": ["Dîner amis", "Café Pierre", "Apéro team", "Téléphone parents"],
            "yoga": ["Yoga matinal", "Méditation", "Étirements", "Yoga Nidra"],
        }
        title = random.choice(titles[cat])
        status = random.choice(statuses) if day_off < 0 else "planned"
        ts = random.choice(triage_statuses)

        scheduled = 1 if day_off <= 3 else 0
        cur.execute("""
            INSERT INTO planner_tasks
                (title, category, start_at, end_at, status, source, triage_status,
                 scheduled, scheduled_date, scheduled_start, scheduled_end)
            VALUES (?, ?, ?, ?, ?, 'demo', ?, ?, ?, ?, ?)
        """, (title, cat, iso(dt), iso(dt + timedelta(hours=1)),
              status, ts, scheduled, date_str(dt), iso(dt), iso(dt + timedelta(hours=1))))

    # ── 6. Calendar events ───────────────────────────────────────
    for i in range(20):
        day_off = random.randint(-3, 7)
        dt = today + timedelta(days=day_off, hours=random.randint(8, 20))
        cat_titles = [
            ("Sport", "Running matinal"), ("Sport", "Salle de sport"),
            ("Travail", "Standup"), ("Travail", "Code review"),
            ("Social", "Déjeuner équipe"), ("Social", "Afterwork"),
            ("Formation", "Webinar IA"),
        ]
        cal, title = random.choice(cat_titles)
        cur.execute("""
            INSERT INTO calendar_events
                (event_uid, calendar_name, title, start_at, end_at, source)
            VALUES (?, ?, ?, ?, ?, 'demo')
        """, (f"demo_evt_{i}", cal, title, iso(dt), iso(dt + timedelta(hours=1))))

    conn.commit()
    conn.close()
    print(f"✓ Demo database created at {DB_PATH}")
    print(f"  {activity_id} activities, {session_id} strength sessions, 91 days of health metrics")


if __name__ == "__main__":
    seed()
