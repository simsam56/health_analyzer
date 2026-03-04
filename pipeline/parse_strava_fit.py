"""
parse_strava_fit.py — Parse fichiers FIT Garmin (export Strava) → SQLite

Structure FIT Garmin :
  - exercise_title messages : {message_index → (wkt_step_name, exercise_category)}
  - set messages            : wkt_step_index → link vers exercise_title
                              category       → tuple d'indices (premier entier = cat_idx)
  - session message         : résumé activité
  - workout message         : nom de la séance (wkt_name)
"""
import sys
import gzip
import sqlite3
import csv
from pathlib import Path
from datetime import datetime

try:
    import fitparse
except ImportError:
    print("⚠️  fitparse manquant — pip install fitparse --break-system-packages")
    fitparse = None

ROOT       = Path(__file__).parent.parent
DB_PATH    = ROOT / "athlete.db"
STRAVA_DIR = ROOT / "export_strava"

# ─────────────────────────────────────────────────────────────────
# MAPPING GARMIN CATEGORY INDEX → CATÉGORIE NORMALISÉE
# Source : Garmin FIT SDK + validation empirique sur les données
# ─────────────────────────────────────────────────────────────────
GARMIN_CAT_IDX = {
    # Pectoraux
    0:  "bench_press",       # confirmé par exercise_title
    1:  "cable_crossover",
    2:  "fly",
    3:  "chest_press",
    # Dos
    4:  "lat_pulldown",
    5:  "pull_up",
    6:  "row",               # confirmé
    7:  "deadlift",
    8:  "back_extension",    # confirmé
    # Épaules
    9:  "shoulder_press",    # confirmé
    10: "lateral_raise",
    11: "front_raise",
    12: "face_pull",
    13: "shrug",
    14: "upright_row",
    # Biceps
    15: "curl",
    16: "hammer_curl",
    17: "preacher_curl",
    # Triceps
    18: "tricep_extension",
    19: "dip",
    20: "skull_crusher",
    # Jambes
    21: "squat",             # confirmé
    22: "leg_press",
    23: "leg_curl",          # confirmé (cat=23 dans données réelles)
    24: "leg_extension",     # confirmé (cat=24 dans données réelles)
    25: "lunge",
    26: "hip_thrust",
    27: "calf_raise",
    # Core
    28: "sit_up",            # confirmé (cat=28 dans données réelles)
    29: "crunch",
    30: "plank",
    31: "leg_raise",
    32: "russian_twist",
    33: "ab_wheel",
    34: "suspension",
    35: "push_up",
    36: "burpee",
    65534: "unknown",        # valeur sentinel Garmin
}

# Mapping catégorie → (Groupe Musculaire, Sous-groupe)
CATEGORY_TO_MUSCLE = {
    "bench_press":      ("Pecs",      "Pecs Moyen"),
    "cable_crossover":  ("Pecs",      "Pecs Bas"),
    "fly":              ("Pecs",      "Pecs Moyen"),
    "chest_press":      ("Pecs",      "Pecs Moyen"),
    "incline_press":    ("Pecs",      "Pecs Haut"),
    "decline_press":    ("Pecs",      "Pecs Bas"),
    "push_up":          ("Pecs",      "Pecs Bas"),

    "lat_pulldown":     ("Dos",       "Grand Dorsal"),
    "pull_up":          ("Dos",       "Grand Dorsal"),
    "row":              ("Dos",       "Rhomboïdes"),
    "seated_row":       ("Dos",       "Rhomboïdes"),
    "deadlift":         ("Dos",       "Lombaires"),
    "back_extension":   ("Dos",       "Lombaires"),
    "good_morning":     ("Dos",       "Lombaires"),

    "shoulder_press":   ("Épaules",   "Faisceau Antérieur"),
    "lateral_raise":    ("Épaules",   "Faisceau Latéral"),
    "front_raise":      ("Épaules",   "Faisceau Antérieur"),
    "face_pull":        ("Épaules",   "Faisceau Postérieur"),
    "shrug":            ("Épaules",   "Trapèzes"),
    "upright_row":      ("Épaules",   "Faisceau Latéral"),
    "arnold_press":     ("Épaules",   "Faisceau Antérieur"),

    "curl":             ("Biceps",    "Biceps Brachial"),
    "bicep_curl":       ("Biceps",    "Biceps Brachial"),
    "hammer_curl":      ("Biceps",    "Brachial"),
    "preacher_curl":    ("Biceps",    "Biceps Brachial"),

    "tricep_extension": ("Triceps",   "Chef Long"),
    "triceps_extension":("Triceps",   "Chef Long"),
    "skull_crusher":    ("Triceps",   "Chef Long"),
    "tricep_pressdown": ("Triceps",   "Chef Latéral"),
    "close_grip_press": ("Triceps",   "Chef Médial"),
    "dip":              ("Triceps",   "Chef Long"),

    "squat":            ("Jambes",    "Quadriceps"),
    "leg_press":        ("Jambes",    "Quadriceps"),
    "leg_extension":    ("Jambes",    "Quadriceps"),
    "lunge":            ("Jambes",    "Quadriceps"),
    "leg_curl":         ("Jambes",    "Ischio-Jambiers"),
    "romanian_deadlift":("Jambes",    "Ischio-Jambiers"),
    "hip_thrust":       ("Jambes",    "Fessiers"),
    "hip_raise":        ("Jambes",    "Fessiers"),
    "glute_bridge":     ("Jambes",    "Fessiers"),
    "calf_raise":       ("Jambes",    "Mollets"),
    "step_up":          ("Jambes",    "Quadriceps"),
    "box_jump":         ("Jambes",    "Quadriceps"),

    "sit_up":           ("Core",      "Abdominaux"),
    "crunch":           ("Core",      "Abdominaux"),
    "plank":            ("Core",      "Gainage"),
    "russian_twist":    ("Core",      "Obliques"),
    "leg_raise":        ("Core",      "Abdominaux Bas"),
    "ab_wheel":         ("Core",      "Abdominaux"),
    "flye":             ("Pecs",      "Pecs Moyen"),
    "suspension":       ("Core",      "Gainage"),
    "mountain_climber": ("Core",      "Gainage"),

    "burpee":           ("Cardio",    "Full Body"),
    "jumping_jack":     ("Cardio",    "Full Body"),
    "unknown":          ("Inconnu",   "Inconnu"),
}

# Mapping nom exercice FR → catégorie
NAME_TO_CATEGORY = {
    "développé couché avec barre": "bench_press",
    "développé couché":            "bench_press",
    "développé incliné":           "incline_press",
    "développé militaire":         "shoulder_press",
    "développé épaules":           "shoulder_press",
    "rowing barre":                "row",
    "rowing haltère":              "row",
    "tirage horizontal":           "seated_row",
    "traction":                    "pull_up",
    "tirage vertical":             "lat_pulldown",
    "soulevé de terre":            "deadlift",
    "soulevé de terre roumain":    "romanian_deadlift",
    "squat arrière":               "squat",
    "squat avant":                 "squat",
    "leg extension":               "leg_extension",
    "leg curl":                    "leg_curl",
    "fentes":                      "lunge",
    "hip thrust":                  "hip_thrust",
    "mollets":                     "calf_raise",
    "élévations latérales":        "lateral_raise",
    "oiseau":                      "face_pull",
    "curl barre":                  "curl",
    "curl haltères":               "curl",
    "curl marteau":                "hammer_curl",
    "extension triceps":           "tricep_extension",
    "barre au front":              "skull_crusher",
    "dips":                        "dip",
    "gainage":                     "plank",
    "relevé de jambes":            "leg_raise",
    "crunch":                      "crunch",
    "abdominaux":                  "sit_up",
    "rotation russe":              "russian_twist",
    "suspension":                  "suspension",
    "pompes":                      "push_up",
    "hyperextension":              "back_extension",
    "torsion du buste":            "russian_twist",
    "superman":                    "back_extension",
    "planche en suspension":       "suspension",
    "planche avec":                "plank",
    "développé écarté en suspension": "suspension",
    "extension triceps à la poulie": "tricep_pressdown",
    "extension triceps":           "tricep_extension",
    "extension du triceps":        "tricep_extension",
    "extension jambe arrière":     "hip_thrust",
    "course tapis":                "burpee",   # cardio
    "oiseau avec haltères":        "face_pull",
    "dip incliné":                 "dip",
}

def resolve_muscle(cat_str: str) -> tuple[str, str]:
    """Retourne (muscle_group, muscle_subgroup) depuis catégorie string."""
    if not cat_str:
        return "Inconnu", "Inconnu"
    key = cat_str.lower().strip()
    return CATEGORY_TO_MUSCLE.get(key, ("Inconnu", "Inconnu"))

def name_to_cat(name: str) -> str | None:
    """Cherche catégorie depuis nom français (matching partiel)."""
    if not name:
        return None
    n = name.lower().strip()
    for key, cat in NAME_TO_CATEGORY.items():
        if key in n or n.startswith(key[:8]):
            return cat
    return None


# ─────────────────────────────────────────────────────────────────
# PARSE UN FICHIER FIT
# ─────────────────────────────────────────────────────────────────
def parse_fit_file(fit_path: Path) -> dict | None:
    if fitparse is None:
        return None

    opener = gzip.open if str(fit_path).endswith(".gz") else open
    try:
        with opener(str(fit_path), "rb") as f:
            data = f.read()
        fitfile = fitparse.FitFile(data)
    except Exception:
        return None

    try:
        msgs = list(fitfile.get_messages())
    except Exception:
        return None

    activity = {
        "type":       "Unknown",
        "name":       None,
        "started_at": None,
        "duration_s": None,
        "distance_m": None,
        "avg_hr":     None,
        "max_hr":     None,
        "calories":   None,
        "elev_gain":  None,
    }
    sets = []
    set_index = 0

    # ── 1. Construire l'index exercise_title ─────────────────────
    # {message_index: {name: str, category: str}}
    title_idx: dict[int, dict] = {}
    for msg in msgs:
        if msg.name != "exercise_title":
            continue
        d = {f.name: f.value for f in msg.fields}
        mi = d.get("message_index")
        if mi is not None:
            cat_str = str(d.get("exercise_category", "")).lower().replace(" ", "_")
            ex_name = d.get("wkt_step_name") or d.get("exercise_name")
            title_idx[mi] = {
                "name":     str(ex_name) if ex_name else None,
                "category": cat_str if cat_str and cat_str != "none" else None,
            }

    # ── 2. Session (résumé) ──────────────────────────────────────
    for msg in msgs:
        if msg.name != "session":
            continue
        d = {f.name: f.value for f in msg.fields}

        sport = str(d.get("sport", "")).lower()
        sport_map = {
            "running":       "Running",
            "cycling":       "Cycling",
            "training":      "Strength Training",
            "strength_training": "Strength Training",
            "swimming":      "Swimming",
            "hiking":        "Hiking",
            "snowboarding":  "Snowboarding",
            "rowing":        "Rowing",
            "stand_up_paddleboarding": "Paddling",
            "tennis":        "Tennis",
            "cross_country_skiing": "Cross_country_skiing",
        }
        activity["type"] = sport_map.get(sport, sport.capitalize() if sport else "Unknown")

        ts = d.get("start_time")
        if ts:
            if isinstance(ts, datetime):
                activity["started_at"] = ts.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                activity["started_at"] = str(ts)[:19]

        dur = d.get("total_elapsed_time") or d.get("total_timer_time")
        if dur is not None:
            try:
                activity["duration_s"] = int(float(dur))
            except (ValueError, TypeError):
                pass

        dist = d.get("total_distance")
        if dist is not None:
            try:
                activity["distance_m"] = float(dist)
            except (ValueError, TypeError):
                pass

        for field, key in [
            ("total_calories",  "calories"),
            ("avg_heart_rate",  "avg_hr"),
            ("max_heart_rate",  "max_hr"),
            ("total_ascent",    "elev_gain"),
        ]:
            val = d.get(field)
            if val is not None:
                try:
                    activity[key] = float(val)
                except (ValueError, TypeError):
                    pass

        break  # on prend le premier session message

    # ── 3. Workout (nom de la séance) ────────────────────────────
    for msg in msgs:
        if msg.name != "workout":
            continue
        d = {f.name: f.value for f in msg.fields}
        wkt_name = d.get("wkt_name") or d.get("name")
        if wkt_name:
            activity["name"] = str(wkt_name)
        break

    # ── 4. Sets ──────────────────────────────────────────────────
    for msg in msgs:
        if msg.name != "set":
            continue
        d = {f.name: f.value for f in msg.fields}

        # Ignorer les périodes de repos
        if str(d.get("set_type", "")).lower() == "rest":
            continue

        # Lier au titre d'exercice via wkt_step_index
        wkt_step = d.get("wkt_step_index")
        title = title_idx.get(wkt_step, {}) if wkt_step is not None else {}

        # Nom exercice (depuis title ou None)
        ex_name = title.get("name")
        # Catégorie string (depuis title)
        cat_str = title.get("category")

        # Catégorie index (depuis le champ category du set — premier entier du tuple)
        cat_idx = None
        cat_tuple = d.get("category")
        if isinstance(cat_tuple, (list, tuple)):
            for c in cat_tuple:
                if isinstance(c, int) and c != 65534:
                    cat_idx = c
                    break

        # Résolution finale de la catégorie
        if not cat_str and cat_idx is not None:
            cat_str = GARMIN_CAT_IDX.get(cat_idx, None)

        # Essai depuis le nom si cat toujours inconnue
        if not cat_str and ex_name:
            cat_str = name_to_cat(ex_name)

        mg, sub = resolve_muscle(cat_str)

        # Reps
        reps = d.get("repetitions")
        try:
            reps = int(reps) if reps is not None else None
        except (ValueError, TypeError):
            reps = None

        # Durée (Garmin stocke en ms)
        dur_raw = d.get("duration")
        try:
            dur_s = float(dur_raw) / 1000 if dur_raw is not None else None
        except (ValueError, TypeError):
            dur_s = None

        # Poids (Garmin stocke en g)
        weight_raw = d.get("weight")
        try:
            weight_kg = float(weight_raw) / 1000 if weight_raw is not None and float(weight_raw) > 0 else None
        except (ValueError, TypeError):
            weight_kg = None

        # Timestamp
        ts = d.get("timestamp")
        if isinstance(ts, datetime):
            ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
        elif ts:
            ts_str = str(ts)[:19]
        else:
            ts_str = None

        set_index += 1
        sets.append({
            "started_at":        ts_str,
            "exercise_name":     ex_name,
            "exercise_category": cat_str or "unknown",
            "muscle_group":      mg,
            "muscle_subgroup":   sub,
            "set_index":         set_index,
            "set_type":          "active",
            "reps":              reps,
            "duration_s":        dur_s,
            "weight_kg":         weight_kg,
        })

    # Type par défaut si on a des sets
    if sets and activity["type"] in ("Unknown", ""):
        activity["type"] = "Strength Training"

    return {"activity": activity, "sets": sets}


# ─────────────────────────────────────────────────────────────────
# STRAVA CSV LOADER
# ─────────────────────────────────────────────────────────────────
FR_MONTHS = {
    'janv.': 'Jan', 'févr.': 'Feb', 'mars': 'Mar', 'avr.': 'Apr',
    'mai': 'May', 'juin': 'Jun', 'juil.': 'Jul', 'août': 'Aug',
    'sept.': 'Sep', 'oct.': 'Oct', 'nov.': 'Nov', 'déc.': 'Dec'
}

def parse_fr_date(s: str) -> str | None:
    if not isinstance(s, str):
        return None
    for fr, en in FR_MONTHS.items():
        s = s.replace(fr, en)
    for fmt in ('%d %b %Y, %H:%M:%S', '%d %b %Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass
    return None


def load_strava_csv(strava_dir: Path) -> dict[str, dict]:
    """
    Charge activities.csv Strava (colonnes EN ou FR selon la locale de l'export).
    Retourne un dict {nom_fichier_base → row}.
    """
    csv_path = strava_dir / "activities.csv"
    if not csv_path.exists():
        print(f"   ⚠️  activities.csv non trouvé : {csv_path}")
        return {}

    # Mapping colonnes FR → clés internes
    FR_COL = {
        "ID de l'activité":            "activity_id",
        "Date de l'activité":          "Activity Date",
        "Nom de l'activité":           "Activity Name",
        "Type d'activité":             "Activity Type",
        "Nom du fichier":              "Filename",
        "Temps écoulé":                "Elapsed Time",
        "Distance":                    "Distance",
        "Fréquence cardiaque moyenne": "Average Heart Rate",
        "Fréquence cardiaque max.":    "Max Heart Rate",
        "Calories":                    "Calories",
        "Dénivelé positif":            "Elevation Gain",
        "Vitesse moyenne":             "Average Speed",
    }
    # Mapping EN → clés internes (export anglais)
    EN_COL = {
        "Activity ID":     "activity_id",
        "Activity Date":   "Activity Date",
        "Activity Name":   "Activity Name",
        "Activity Type":   "Activity Type",
        "Filename":        "Filename",
        "Elapsed Time":    "Elapsed Time",
        "Distance":        "Distance",
        "Average Heart Rate": "Average Heart Rate",
        "Max Heart Rate":  "Max Heart Rate",
        "Calories":        "Calories",
        "Elevation Gain":  "Elevation Gain",
        "Average Speed":   "Average Speed",
    }

    index = {}
    no_file = 0  # activités sans FIT

    with open(csv_path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Détection locale
        is_fr = any(k in fieldnames for k in FR_COL)
        col_map = FR_COL if is_fr else EN_COL

        for row in reader:
            # Normaliser les colonnes
            norm = {}
            for orig_col, std_col in col_map.items():
                if orig_col in row:
                    norm[std_col] = row[orig_col]
            # Garder toutes les colonnes originales aussi
            norm.update(row)

            # Trouver le nom de fichier
            fname = norm.get("Filename", "").strip()
            if not fname:
                no_file += 1
                continue

            basename = Path(fname).name
            index[basename] = norm

    print(f"   → {len(index)} activités dans Strava CSV ({no_file} sans FIT, locale={'FR' if is_fr else 'EN'})")
    return index


# ─────────────────────────────────────────────────────────────────
# CANONICAL KEY (déduplication)
# ─────────────────────────────────────────────────────────────────
def canonical_key(act_type: str, started_at: str, duration_s) -> str:
    t8  = act_type[:8].lower().replace(" ", "_")
    d   = started_at[:10] if started_at else "0000-00-00"
    dur = round((int(duration_s) if duration_s else 0) / 300) * 300
    return f"{t8}|{d}|{dur}"


# ─────────────────────────────────────────────────────────────────
# INSERTION EN BASE
# ─────────────────────────────────────────────────────────────────
def insert_fit_data(conn: sqlite3.Connection, parsed: dict, csv_row: dict | None) -> bool:
    act  = parsed["activity"]
    sets = parsed["sets"]

    # Enrichissement depuis CSV
    if csv_row:
        if not act["started_at"]:
            act["started_at"] = parse_fr_date(csv_row.get("Activity Date", ""))
        if not act["name"]:
            act["name"] = csv_row.get("Activity Name", "").strip() or act["name"]
        if not act["distance_m"]:
            try:
                raw = str(csv_row.get("Distance", "")).replace(",", ".")
                act["distance_m"] = float(raw) * 1000 if raw else None
            except ValueError:
                pass

    if not act["started_at"]:
        return False

    ck = canonical_key(act["type"], act["started_at"], act["duration_s"])
    source_id = str(csv_row.get("Activity ID", "")) if csv_row else None

    cursor = conn.cursor()

    # Insertion activité
    cursor.execute("""
        INSERT OR IGNORE INTO activities
          (source, source_id, type, name, started_at, duration_s,
           distance_m, elev_gain_m, calories, avg_hr, max_hr,
           avg_pace_mpm, tss_proxy, training_load, canonical_key)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        "strava_fit", source_id, act["type"], act["name"],
        act["started_at"], act["duration_s"], act["distance_m"],
        act["elev_gain"], act["calories"], act["avg_hr"], act["max_hr"],
        None, None, None, ck,
    ))

    activity_db_id  = cursor.lastrowid
    activity_inserted = cursor.rowcount > 0

    if not activity_inserted:
        row = cursor.execute("SELECT id FROM activities WHERE canonical_key=?", (ck,)).fetchone()
        activity_db_id = row[0] if row else None

    # Insertion séance musculation
    if sets and act["type"] in ("Strength Training", "Unknown", "training"):
        total_reps = sum(s["reps"] or 0 for s in sets)

        existing = cursor.execute(
            "SELECT id FROM strength_sessions WHERE started_at=?",
            (act["started_at"],)
        ).fetchone()

        if existing:
            session_id = existing[0]
        else:
            cursor.execute("""
                INSERT INTO strength_sessions
                  (activity_id, started_at, workout_name, duration_s, total_sets, total_reps, source)
                VALUES (?,?,?,?,?,?,?)
            """, (
                activity_db_id, act["started_at"], act["name"],
                act["duration_s"], len(sets), total_reps, "strava_fit",
            ))
            session_id = cursor.lastrowid

            for s in sets:
                cursor.execute("""
                    INSERT INTO exercise_sets
                      (session_id, started_at, exercise_name, exercise_category,
                       muscle_group, muscle_subgroup, set_index, set_type,
                       reps, duration_s, weight_kg)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    session_id, s["started_at"], s["exercise_name"],
                    s["exercise_category"], s["muscle_group"], s["muscle_subgroup"],
                    s["set_index"], s["set_type"],
                    s["reps"], s["duration_s"], s["weight_kg"],
                ))

    return activity_inserted


# ─────────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────────
def run(
    strava_dir: Path = STRAVA_DIR,
    db_path:    Path = DB_PATH,
    verbose:    bool = True,
) -> dict:
    if fitparse is None:
        print("❌ fitparse non disponible")
        return {}

    from pipeline.schema import init_db
    conn = init_db(db_path)

    csv_index = load_strava_csv(strava_dir)

    activities_dir = strava_dir / "activities"
    fit_files = sorted(
        list(activities_dir.glob("*.fit")) +
        list(activities_dir.glob("*.fit.gz"))
    )
    print(f"📂 {len(fit_files)} fichiers FIT dans {activities_dir}")

    stats = {"parsed": 0, "inserted": 0, "skipped": 0,
             "strength": 0, "sets_total": 0, "errors": 0}

    for fit_path in fit_files:
        try:
            parsed = parse_fit_file(fit_path)
            if parsed is None:
                stats["errors"] += 1
                continue

            stats["parsed"] += 1

            # Matching CSV
            basename = fit_path.name
            csv_row  = csv_index.get(basename)
            if not csv_row:
                for key in csv_index:
                    if basename.replace(".fit.gz", "").replace(".fit", "") in key:
                        csv_row = csv_index[key]
                        break

            inserted = insert_fit_data(conn, parsed, csv_row)
            if inserted:
                stats["inserted"] += 1
                if parsed["sets"]:
                    stats["strength"] += 1
                    stats["sets_total"] += len(parsed["sets"])
            else:
                stats["skipped"] += 1

        except Exception as e:
            stats["errors"] += 1
            if verbose:
                print(f"   ⚠️  {fit_path.name}: {e}")

    conn.commit()
    conn.close()

    print(f"\n✅ FIT Pipeline :")
    print(f"   Parsés    : {stats['parsed']}")
    print(f"   Insérés   : {stats['inserted']}")
    print(f"   Doublons  : {stats['skipped']}")
    print(f"   Muscu     : {stats['strength']} séances, {stats['sets_total']} séries")
    print(f"   Erreurs   : {stats['errors']}")
    return stats


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--strava", default=str(STRAVA_DIR))
    p.add_argument("--db",     default=str(DB_PATH))
    args = p.parse_args()
    run(Path(args.strava), Path(args.db))
