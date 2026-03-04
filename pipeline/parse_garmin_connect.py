"""
parse_garmin_connect.py — Récupère les données récentes depuis Garmin Connect API

Utilise la bibliothèque `garminconnect` (cyberjunky) avec auth OAuth2 via `garth`.

Données récupérées :
  - Activités récentes (30 derniers jours) → table activities
  - HRV nocturne → table health_metrics
  - FC repos (dailyHeartRate) → table health_metrics
  - Sommeil → table health_metrics
  - Body Battery (énergie) → table health_metrics
  - VO2Max → table health_metrics

Auth :
  Créer un fichier .env dans le dossier racine :
    GARMIN_EMAIL=votre@email.com
    GARMIN_PASSWORD=votreMotDePasse

  OU exécuter manuellement une fois pour stocker le token :
    python3 pipeline/parse_garmin_connect.py --login

  Les tokens sont sauvegardés dans ~/.garth/ (valides ~1 an)
"""
import sqlite3
import json
import os
import sys
from datetime import date, timedelta, datetime
from pathlib import Path

ROOT    = Path(__file__).parent.parent
DB_PATH = ROOT / "athlete.db"

try:
    import garminconnect
    GARMIN_AVAILABLE = True
except ImportError:
    GARMIN_AVAILABLE = False
    print("⚠️  garminconnect non installé : pip install garminconnect --break-system-packages")

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# ─────────────────────────────────────────────────────────────────
# MAPPING TYPE ACTIVITÉ GARMIN → TYPE NORMALISÉ
# ─────────────────────────────────────────────────────────────────
GARMIN_TYPE_MAP = {
    "running":              "Running",
    "trail_running":        "Running",
    "cycling":              "Cycling",
    "mountain_biking":      "Cycling",
    "swimming":             "Swimming",
    "open_water_swimming":  "Swimming",
    "strength_training":    "Strength Training",
    "fitness_equipment":    "Strength Training",
    "yoga":                 "Yoga",
    "hiking":               "Hiking",
    "walking":              "Walking",
    "snowboarding":         "Snowboarding",
    "snow_skiing":          "Snowboarding",
    "backcountry_skiing_snowboarding_ws": "Snowboarding",
    "cross_country_skiing": "Cross_country_skiing",
    "stand_up_paddleboarding": "Paddling",
    "wakeboarding":         "Wakeboarding",
    "tennis":               "Tennis",
    "rowing":               "Rowing",
    "other":                "Other",
}

# ─────────────────────────────────────────────────────────────────
# MAPPING CATÉGORIE EXERCICE GARMIN → MUSCLE
# ─────────────────────────────────────────────────────────────────
GARMIN_EX_CATEGORY_TO_MUSCLE = {
    # Pecs
    "BENCH_PRESS":        ("Pecs", "Pecs Moyen"),
    "CHEST_PRESS":        ("Pecs", "Pecs Moyen"),
    "FLY":                ("Pecs", "Pecs Moyen"),
    "PUSH_UP":            ("Pecs", "Pecs Bas"),
    # Dos
    "ROW":                ("Dos", "Rhomboïdes"),
    "PULL_UP":            ("Dos", "Grand Dorsal"),
    "LAT_PULLDOWN":       ("Dos", "Grand Dorsal"),
    "DEADLIFT":           ("Dos", "Lombaires"),
    "HYPEREXTENSION":     ("Dos", "Lombaires"),
    # Épaules
    "SHOULDER_PRESS":     ("Épaules", "Faisceau Antérieur"),
    "LATERAL_RAISE":      ("Épaules", "Faisceau Latéral"),
    "FRONT_RAISE":        ("Épaules", "Faisceau Antérieur"),
    "FACE_PULL":          ("Épaules", "Faisceau Postérieur"),
    "SHRUG":              ("Épaules", "Trapèzes"),
    "UPRIGHT_ROW":        ("Épaules", "Faisceau Latéral"),
    # Biceps
    "CURL":               ("Biceps", "Biceps Brachial"),
    # Triceps
    "TRICEPS_EXTENSION":  ("Triceps", "Chef Long"),
    "DIP":                ("Triceps", "Chef Long"),
    # Jambes
    "SQUAT":              ("Jambes", "Quadriceps"),
    "LUNGE":              ("Jambes", "Quadriceps"),
    "LEG_PRESS":          ("Jambes", "Quadriceps"),
    "LEG_EXTENSION":      ("Jambes", "Quadriceps"),
    "LEG_CURL":           ("Jambes", "Ischio-Jambiers"),
    "HIP_THRUST":         ("Jambes", "Fessiers"),
    "CALF_RAISE":         ("Jambes", "Mollets"),
    # Core
    "PLANK":              ("Core", "Gainage"),
    "CORE":               ("Core", "Abdominaux"),
    "SUSPENSION":         ("Core", "Gainage"),
    "CRUNCH":             ("Core", "Abdominaux"),
    "SIT_UP":             ("Core", "Abdominaux"),
    "RUSSIAN_TWIST":      ("Core", "Obliques"),
    "LEG_RAISE":          ("Core", "Abdominaux Bas"),
}


def canonical_key(act_type: str, started_at: str, duration_s) -> str:
    t8  = act_type[:8].lower().replace(" ", "_")
    d   = started_at[:10] if started_at else "0000-00-00"
    dur = round((int(duration_s) if duration_s else 0) / 300) * 300
    return f"{t8}|{d}|{dur}"


# ─────────────────────────────────────────────────────────────────
# CONNEXION GARMIN
# ─────────────────────────────────────────────────────────────────
def get_garmin_client(
    email: str | None = None,
    password: str | None = None,
    tokenstore: str | None = None,
) -> "garminconnect.Garmin | None":
    """
    Initialise et retourne un client Garmin Connect.
    Essaie d'abord les tokens sauvegardés, puis les credentials.
    """
    if not GARMIN_AVAILABLE:
        return None

    email    = email    or os.environ.get("GARMIN_EMAIL")
    password = password or os.environ.get("GARMIN_PASSWORD")
    tokendir = tokenstore or os.path.expanduser("~/.garth")

    client = garminconnect.Garmin()

    # 1. Essai token existant
    try:
        client.login(tokenstore=tokendir)
        user_data = client.get_full_name()
        print(f"   ✅ Garmin Connect : connecté ({user_data})")
        return client
    except Exception as e:
        if "oauth" in str(e).lower() or "token" in str(e).lower():
            print(f"   ℹ️  Token expiré, reconnexion…")
        else:
            pass

    # 2. Connexion avec credentials
    if not email or not password:
        print("   ❌ Garmin : email/password manquants (configurez .env)")
        print("      GARMIN_EMAIL=votre@email.com")
        print("      GARMIN_PASSWORD=votre_mdp")
        return None

    try:
        client = garminconnect.Garmin(email=email, password=password)
        client.login()
        # Sauvegarder les tokens
        os.makedirs(tokendir, exist_ok=True)
        client.garth.dump(tokendir)
        print(f"   ✅ Garmin Connect : connecté et token sauvegardé → {tokendir}")
        return client
    except garminconnect.GarminConnectTooManyRequestsError:
        print("   ⚠️  Garmin Connect : trop de requêtes, réessayez dans 15 min")
        return None
    except Exception as e:
        print(f"   ❌ Garmin Connect erreur de connexion : {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# RÉCUPÉRATION ACTIVITÉS
# ─────────────────────────────────────────────────────────────────
def fetch_recent_activities(
    client,
    days: int = 30,
    start_date: date | None = None,
) -> list[dict]:
    """Récupère les activités récentes depuis Garmin Connect."""
    if start_date is None:
        start_date = date.today() - timedelta(days=days)

    try:
        activities = client.get_activities_by_date(
            str(start_date), str(date.today()), activitytype=""
        )
    except Exception as e:
        print(f"   ⚠️  Erreur fetch activités : {e}")
        return []

    parsed = []
    for act in activities:
        raw_type = str(act.get("activityType", {}).get("typeKey", "other")).lower()
        act_type = GARMIN_TYPE_MAP.get(raw_type, raw_type.replace("_", " ").capitalize())

        # Date
        start_str = act.get("startTimeLocal") or act.get("startTimeGMT", "")
        try:
            dt = datetime.strptime(start_str[:19], "%Y-%m-%d %H:%M:%S")
            started_at = dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            started_at = start_str[:19]

        duration_s = int(act.get("duration", 0) or 0)
        distance_m = float(act.get("distance", 0) or 0)
        calories   = int(act.get("calories", 0) or 0)
        avg_hr     = act.get("averageHR")
        max_hr     = act.get("maxHR")
        elev_gain  = act.get("elevationGain")
        act_name   = act.get("activityName", "")
        act_id     = str(act.get("activityId", ""))

        avg_pace = None
        if act_type == "Running" and distance_m > 0 and duration_s > 0:
            avg_pace = (duration_s / 60) / (distance_m / 1000)

        ck = canonical_key(act_type, started_at, duration_s)

        parsed.append({
            "source":       "garmin_connect",
            "source_id":    act_id,
            "type":         act_type,
            "name":         act_name,
            "started_at":   started_at,
            "duration_s":   duration_s,
            "distance_m":   distance_m if distance_m > 0 else None,
            "elev_gain_m":  float(elev_gain) if elev_gain else None,
            "calories":     calories if calories > 0 else None,
            "avg_hr":       float(avg_hr) if avg_hr else None,
            "max_hr":       float(max_hr) if max_hr else None,
            "avg_pace_mpm": avg_pace,
            "tss_proxy":    None,
            "training_load": None,
            "canonical_key": ck,
        })

    print(f"   → {len(parsed)} activités Garmin Connect ({start_date} → aujourd'hui)")
    return parsed


# ─────────────────────────────────────────────────────────────────
# EXERCISES / MUSCULATION (Garmin activity_exercise_sets)
# ─────────────────────────────────────────────────────────────────
def _title_from_token(token: str | None) -> str | None:
    if not token:
        return None
    return str(token).replace("_", " ").strip().title()


def _resolve_muscle_from_category(category: str | None, ex_name: str | None) -> tuple[str, str]:
    cat = str(category or "").upper().strip()
    if cat in GARMIN_EX_CATEGORY_TO_MUSCLE:
        return GARMIN_EX_CATEGORY_TO_MUSCLE[cat]

    key = f"{cat} {str(ex_name or '').upper()}"

    # Fallback par mots-clés quand Garmin envoie des catégories non mappées
    if any(k in key for k in ("ROW", "PULL_UP", "PULLDOWN", "PULL DOWN", "DEADLIFT", "HYPEREXTENSION")):
        return "Dos", "Rhomboïdes"
    if any(k in key for k in ("SQUAT", "LUNGE", "LEG", "CALF", "GLUTE", "HIP_THRUST", "HIP_RAISE")):
        return "Jambes", "Quadriceps"
    if any(k in key for k in ("PLANK", "CORE", "CRUNCH", "SIT_UP", "RUSSIAN", "TWIST", "LEG_RAISE")):
        return "Core", "Abdominaux"
    if any(k in key for k in ("CURL", "CHIN_UP")):
        return "Biceps", "Biceps Brachial"
    if any(k in key for k in ("TRICEPS", "DIP", "SKULL", "TRICEPS_EXTENSION", "TRICEP_EXTENSION")):
        return "Triceps", "Chef Long"
    if any(k in key for k in ("SHOULDER", "LATERAL", "FRONT_RAISE", "SHRUG", "FACE_PULL", "UPRIGHT_ROW")):
        return "Épaules", "Faisceau Latéral"
    if any(k in key for k in ("BENCH", "CHEST", "FLY", "FLYE", "PUSH_UP")):
        return "Pecs", "Pecs Moyen"

    return "Inconnu", "Inconnu"


def _normalize_weight_kg(value) -> float | None:
    if value is None:
        return None
    try:
        w = float(value)
    except (TypeError, ValueError):
        return None
    if w <= 0:
        return None
    # Heuristique: très grandes valeurs probablement en grammes
    if w > 350:
        w = w / 1000.0
    return round(w, 3)


def _pick_number(payload: dict, keys: list[str], as_int: bool = False):
    """Récupère la première valeur numérique valide parmi plusieurs clés possibles."""
    for key in keys:
        if key not in payload:
            continue
        val = payload.get(key)
        if val is None or val == "":
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        if as_int:
            return int(round(num))
        return num
    return None


def _pick_best_exercise(exercises) -> dict:
    if not isinstance(exercises, list) or not exercises:
        return {"category": None, "name": None}
    try:
        best = max(exercises, key=lambda e: float((e or {}).get("probability") or 0))
        if not isinstance(best, dict):
            return {"category": None, "name": None}
        return {
            "category": best.get("category"),
            "name": best.get("name"),
        }
    except Exception:
        return {"category": None, "name": None}


def _find_activity_db_id(conn: sqlite3.Connection, activity: dict) -> int | None:
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT id FROM activities WHERE source='garmin_connect' AND source_id=?",
        (activity.get("source_id"),),
    ).fetchone()
    if row:
        return row[0]
    row = cursor.execute(
        "SELECT id FROM activities WHERE canonical_key=?",
        (activity.get("canonical_key"),),
    ).fetchone()
    return row[0] if row else None


def _upsert_strength_session_from_garmin_sets(
    conn: sqlite3.Connection,
    activity_db_id: int,
    activity: dict,
    garmin_sets: list[dict],
) -> tuple[bool, int]:
    # Conserver seulement les sets actifs comme dans le pipeline FIT.
    active_sets = [s for s in garmin_sets if str(s.get("setType", "")).upper() == "ACTIVE"]
    if not active_sets:
        # Fallback: certaines payloads n'exposent pas "ACTIVE" explicitement.
        active_sets = [
            s for s in garmin_sets
            if str(s.get("setType", "")).upper() not in {"REST", "RECOVERY", "WARMUP", "COOLDOWN"}
        ]
    if not active_sets:
        return False, 0

    parsed_sets = []
    for i, s in enumerate(active_sets, start=1):
        best = _pick_best_exercise(s.get("exercises"))
        ex_cat = str(
            best.get("category")
            or s.get("exerciseCategory")
            or s.get("category")
            or ""
        ).upper().strip() or None
        ex_name_token = best.get("name") or s.get("exerciseName") or s.get("name")
        ex_name = _title_from_token(ex_name_token) or _title_from_token(ex_cat) or "Unknown"
        mg, sub = _resolve_muscle_from_category(ex_cat, ex_name_token)

        reps = _pick_number(
            s,
            ["repetitionCount", "repetitions", "repCount", "numReps", "reps"],
            as_int=True,
        )
        duration_s = _pick_number(
            s,
            ["duration", "durationSecs", "elapsedDuration", "time"],
            as_int=False,
        )
        weight_kg = _normalize_weight_kg(
            _pick_number(
                s,
                ["weightInKilograms", "weightKg", "weight", "resistance"],
                as_int=False,
            )
        )

        parsed_sets.append({
            "started_at": str(s.get("startTime") or activity.get("started_at") or "")[:19] or None,
            "exercise_name": ex_name,
            "exercise_category": (ex_cat or "unknown").lower(),
            "muscle_group": mg,
            "muscle_subgroup": sub,
            "set_index": i,
            "set_type": "active",
            "reps": reps,
            "duration_s": duration_s,
            "weight_kg": weight_kg,
        })

    total_reps = sum(x["reps"] or 0 for x in parsed_sets)

    cursor = conn.cursor()
    existing = cursor.execute(
        "SELECT id FROM strength_sessions WHERE activity_id=?",
        (activity_db_id,),
    ).fetchone()

    created = False
    if existing:
        session_id = existing[0]
        cursor.execute(
            """
            UPDATE strength_sessions
            SET started_at=?, workout_name=?, duration_s=?, total_sets=?, total_reps=?, source=?
            WHERE id=?
            """,
            (
                activity.get("started_at"),
                activity.get("name"),
                activity.get("duration_s"),
                len(parsed_sets),
                total_reps,
                "garmin_connect",
                session_id,
            ),
        )
        cursor.execute("DELETE FROM exercise_sets WHERE session_id=?", (session_id,))
    else:
        cursor.execute(
            """
            INSERT INTO strength_sessions
              (activity_id, started_at, workout_name, duration_s, total_sets, total_reps, source)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                activity_db_id,
                activity.get("started_at"),
                activity.get("name"),
                activity.get("duration_s"),
                len(parsed_sets),
                total_reps,
                "garmin_connect",
            ),
        )
        session_id = cursor.lastrowid
        created = True

    ins_sets = 0
    for s in parsed_sets:
        cursor.execute(
            """
            INSERT INTO exercise_sets
              (session_id, started_at, exercise_name, exercise_category,
               muscle_group, muscle_subgroup, set_index, set_type,
               reps, duration_s, weight_kg)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                session_id,
                s["started_at"],
                s["exercise_name"],
                s["exercise_category"],
                s["muscle_group"],
                s["muscle_subgroup"],
                s["set_index"],
                s["set_type"],
                s["reps"],
                s["duration_s"],
                s["weight_kg"],
            ),
        )
        ins_sets += 1

    return created, ins_sets


def fetch_and_insert_strength_sets(
    client,
    conn: sqlite3.Connection,
    activities: list[dict],
    refresh_tail_days: int = 3,
) -> tuple[int, int, int]:
    """
    Pour chaque activité force/training Garmin, récupère les exercise sets
    et persiste en strength_sessions + exercise_sets.
    """
    sessions_created = 0
    sets_inserted = 0
    skipped_existing = 0

    strength_acts = [a for a in activities if a.get("type") == "Strength Training"]
    if not strength_acts:
        return sessions_created, sets_inserted, skipped_existing

    cutoff_date = date.today() - timedelta(days=max(0, int(refresh_tail_days) - 1))

    for a in strength_acts:
        source_id = a.get("source_id")
        if not source_id:
            continue
        activity_db_id = _find_activity_db_id(conn, a)
        if not activity_db_id:
            continue

        # Skip des séances historiques déjà importées (sauf queue récente).
        act_date = None
        try:
            act_date = datetime.fromisoformat(str(a.get("started_at", ""))[:19]).date()
        except Exception:
            act_date = None
        existing = conn.execute(
            "SELECT id FROM strength_sessions WHERE activity_id=?",
            (activity_db_id,),
        ).fetchone()
        if existing and act_date and act_date < cutoff_date:
            skipped_existing += 1
            continue

        try:
            payload = client.get_activity_exercise_sets(int(source_id))
        except Exception:
            continue

        garmin_sets = payload.get("exerciseSets", []) if isinstance(payload, dict) else []
        if not garmin_sets:
            continue

        created, ins_sets = _upsert_strength_session_from_garmin_sets(
            conn=conn,
            activity_db_id=activity_db_id,
            activity=a,
            garmin_sets=garmin_sets,
        )
        if created:
            sessions_created += 1
        sets_inserted += ins_sets

    conn.commit()
    return sessions_created, sets_inserted, skipped_existing


# ─────────────────────────────────────────────────────────────────
# RÉCUPÉRATION MÉTRIQUES SANTÉ
# ─────────────────────────────────────────────────────────────────
def fetch_health_metrics(
    client,
    days: int = 30,
    conn: sqlite3.Connection | None = None,
    refresh_tail_days: int = 3,
) -> list[dict]:
    """Récupère HRV, FC repos, sommeil, Body Battery des N derniers jours."""
    metrics = []
    end   = date.today()
    start = end - timedelta(days=days)
    refresh_cutoff = end - timedelta(days=max(0, int(refresh_tail_days) - 1))

    existing_dates = set()
    if conn is not None:
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT date
                FROM health_metrics
                WHERE source='garmin_connect'
                  AND date >= ?
                  AND date <= ?
                """,
                (str(start), str(end)),
            ).fetchall()
            existing_dates = {str(r[0]) for r in rows if r and r[0]}
        except Exception:
            existing_dates = set()

    current = start
    skipped_days = 0
    while current <= end:
        ds = str(current)

        # Incrémental: si on a déjà un historique Garmin, on ne refetch pas l'ancien.
        # On conserve seulement une "queue" récente pour capter les mises à jour tardives.
        if conn is not None and current < refresh_cutoff and existing_dates:
            skipped_days += 1
            current += timedelta(days=1)
            continue

        # ── HRV ─────────────────────────────────────────────────
        try:
            hrv_data = client.get_hrv_data(ds)
            if hrv_data:
                # La structure varie selon la version Garmin API
                hrv_val = None
                if isinstance(hrv_data, dict):
                    hrv_val = (
                        hrv_data.get("lastNight", {}).get("avg5MinHrv") or
                        hrv_data.get("hrvSummary", {}).get("lastNight") or
                        hrv_data.get("hrv5MinAvg")
                    )
                    if hrv_val and hrv_val > 0:
                        metrics.append({
                            "date": ds, "metric": "hrv_sdnn",
                            "value": float(hrv_val), "source": "garmin_connect",
                        })
        except Exception:
            pass

        # ── FC Repos (Resting HR) ────────────────────────────────
        try:
            rhr_data = client.get_rhr_day(ds)
            if rhr_data:
                rhr_val = None
                if isinstance(rhr_data, dict):
                    rhr_val = rhr_data.get("allMetrics", {}).get("metricsMap", {}).get("WELLNESS_RESTING_HEART_RATE", [{}])[0].get("value")
                    if not rhr_val:
                        rhr_val = rhr_data.get("restingHeartRate") or rhr_data.get("value")
                if rhr_val and float(rhr_val) > 0:
                    metrics.append({
                        "date": ds, "metric": "rhr",
                        "value": float(rhr_val), "source": "garmin_connect",
                    })
        except Exception:
            pass

        # ── Sommeil ──────────────────────────────────────────────
        try:
            sleep_data = client.get_sleep_data(ds)
            if sleep_data:
                sleep_secs = None
                if isinstance(sleep_data, dict):
                    daily = sleep_data.get("dailySleepDTO", {})
                    sleep_secs = daily.get("sleepTimeSeconds") or daily.get("totalSleepSeconds")
                    if not sleep_secs:
                        sleep_secs = sleep_data.get("sleepTimeSeconds")
                if sleep_secs and sleep_secs > 0:
                    sleep_h = round(sleep_secs / 3600, 2)
                    if 2 < sleep_h < 14:
                        metrics.append({
                            "date": ds, "metric": "sleep_h",
                            "value": sleep_h, "source": "garmin_connect",
                        })
        except Exception:
            pass

        # ── Body Battery ─────────────────────────────────────────
        try:
            bb_data = client.get_body_battery(ds)
            if bb_data and isinstance(bb_data, list) and bb_data:
                # Prendre la valeur max de la journée (matin = récupéré)
                charged_vals = [
                    r.get("charged") for r in bb_data
                    if r.get("charged") is not None and r.get("charged") > 0
                ]
                if charged_vals:
                    metrics.append({
                        "date": ds, "metric": "body_battery",
                        "value": max(charged_vals), "source": "garmin_connect",
                    })
        except Exception:
            pass

        # ── Stress ───────────────────────────────────────────────
        try:
            stress = client.get_stress_data(ds)
            if stress and isinstance(stress, dict):
                avg_stress = stress.get("avgStressLevel")
                if avg_stress and avg_stress > 0:
                    metrics.append({
                        "date": ds, "metric": "stress_avg",
                        "value": float(avg_stress), "source": "garmin_connect",
                    })
        except Exception:
            pass

        current += timedelta(days=1)

    if skipped_days > 0:
        print(f"   → {len(metrics)} métriques santé Garmin Connect ({skipped_days} jours historiques ignorés)")
    else:
        print(f"   → {len(metrics)} métriques santé Garmin Connect")
    return metrics


# ─────────────────────────────────────────────────────────────────
# INSERTION EN BASE
# ─────────────────────────────────────────────────────────────────
def insert_activities(conn: sqlite3.Connection, activities: list[dict]) -> tuple[int, int]:
    ins, skip = 0, 0
    cursor = conn.cursor()
    for a in activities:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO activities
                  (source, source_id, type, name, started_at, duration_s,
                   distance_m, elev_gain_m, calories, avg_hr, max_hr,
                   avg_pace_mpm, tss_proxy, training_load, canonical_key)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                a["source"], a["source_id"], a["type"], a["name"],
                a["started_at"], a["duration_s"], a["distance_m"],
                a["elev_gain_m"], a["calories"], a["avg_hr"], a["max_hr"],
                a["avg_pace_mpm"], a["tss_proxy"], a["training_load"],
                a["canonical_key"],
            ))
            if cursor.rowcount:
                ins += 1
            else:
                skip += 1
        except sqlite3.Error as e:
            print(f"   ⚠️  DB error: {e}")
    conn.commit()
    return ins, skip


def insert_health_metrics(conn: sqlite3.Connection, metrics: list[dict]) -> int:
    ins = 0
    cursor = conn.cursor()
    for m in metrics:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO health_metrics (date, metric, value, source)
                VALUES (?,?,?,?)
            """, (m["date"], m["metric"], m["value"], m["source"]))
            if cursor.rowcount:
                ins += 1
        except sqlite3.Error:
            pass
    conn.commit()
    return ins


# ─────────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────────
def run(
    db_path:    Path = DB_PATH,
    days:       int  = 30,
    email:      str | None = None,
    password:   str | None = None,
    verbose:    bool = True,
    refresh_tail_days: int = 3,
) -> dict:
    """
    Pipeline Garmin Connect → SQLite.
    Récupère les N derniers jours d'activités et métriques santé.
    """
    if not GARMIN_AVAILABLE:
        return {"error": "garminconnect non installé"}

    print(f"🔗 Connexion Garmin Connect…")
    client = get_garmin_client(email=email, password=password)

    if client is None:
        return {"error": "connexion impossible"}

    conn = sqlite3.connect(str(db_path))

    # 1. Activités récentes
    activities = fetch_recent_activities(client, days=days)
    ins_a, skip_a = insert_activities(conn, activities)
    print(f"   ✅ Activities : {ins_a} insérées, {skip_a} doublons")

    # 2. Sets musculation (si disponibles)
    sess_new, sets_ins, sets_skip = fetch_and_insert_strength_sets(
        client,
        conn,
        activities,
        refresh_tail_days=refresh_tail_days,
    )
    print(
        f"   ✅ Musculation Garmin : {sess_new} séances créées, "
        f"{sets_ins} sets importés, {sets_skip} séances historiques ignorées"
    )

    # 3. Métriques santé
    metrics = fetch_health_metrics(
        client,
        days=days,
        conn=conn,
        refresh_tail_days=refresh_tail_days,
    )
    ins_m = insert_health_metrics(conn, metrics)
    print(f"   ✅ Métriques santé : {ins_m} insérées")

    conn.close()

    return {
        "activities_fetched":  len(activities),
        "activities_inserted": ins_a,
        "activities_skipped":  skip_a,
        "strength_sessions_inserted": sess_new,
        "exercise_sets_inserted": sets_ins,
        "strength_sessions_skipped": sets_skip,
        "metrics_inserted":    ins_m,
    }


# ─────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Sync Garmin Connect → SQLite")
    p.add_argument("--db",       default=str(DB_PATH))
    p.add_argument("--days",     type=int, default=30, help="Nb jours à récupérer")
    p.add_argument("--refresh-tail-days", type=int, default=3,
                   help="Ne refresh complètement que les N derniers jours")
    p.add_argument("--email",    default=None)
    p.add_argument("--password", default=None)
    p.add_argument("--login",    action="store_true",
                   help="Force login interactif (stocke le token)")
    args = p.parse_args()

    if args.login:
        # Login interactif avec saisie manuelle
        email    = args.email    or input("Email Garmin : ").strip()
        password = args.password or input("Mot de passe Garmin : ").strip()
        client   = get_garmin_client(email=email, password=password)
        if client:
            print("✅ Connecté et token sauvegardé.")
        sys.exit(0)

    result = run(
        Path(args.db),
        days=args.days,
        email=args.email,
        password=args.password,
        refresh_tail_days=max(1, int(args.refresh_tail_days)),
    )
    print(f"\n📊 Résultat : {result}")
