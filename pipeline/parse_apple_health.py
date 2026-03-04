"""
parse_apple_health.py — PerformOS v3
Parse Apple Health export.xml → SQLite

Métriques importées (v3) :
  HKQuantityTypeIdentifierHeartRateVariabilitySDNN  → hrv_sdnn
  HKQuantityTypeIdentifierRestingHeartRate           → rhr
  HKQuantityTypeIdentifierVO2Max                     → vo2max
  HKQuantityTypeIdentifierBodyMass                   → weight_kg
  HKCategoryTypeIdentifierSleepAnalysis              → sleep_h
  HKQuantityTypeIdentifierStepCount                  → steps
  HKQuantityTypeIdentifierActiveEnergyBurned         → active_cal
  HKQuantityTypeIdentifierBasalEnergyBurned          → basal_cal
  HKQuantityTypeIdentifierDistanceWalkingRunning     → distance_km
  HKQuantityTypeIdentifierDistanceCycling            → distance_cycling_km
  HKQuantityTypeIdentifierFlightsClimbed             → flights
  HKQuantityTypeIdentifierAppleExerciseTime          → exercise_min
  HKQuantityTypeIdentifierAppleStandTime             → stand_min
  HKQuantityTypeIdentifierWalkingSpeed               → walk_speed_kmh
  HKQuantityTypeIdentifierWalkingHeartRateAverage    → walk_hr
  HKQuantityTypeIdentifierWalkingAsymmetryPercentage → walk_asymmetry
  HKQuantityTypeIdentifierWalkingDoubleSupportPercentage → walk_double_support
  HKQuantityTypeIdentifierHeartRate                  → hr_avg (daily mean)
  HKQuantityTypeIdentifierBodyFatPercentage          → body_fat_pct
"""
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


# ─────────────────────────────────────────────────────────────────────
# Mapping HK type → nom interne
# ─────────────────────────────────────────────────────────────────────
HK_QUANTITY_MAP = {
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":       "hrv_sdnn",
    "HKQuantityTypeIdentifierRestingHeartRate":               "rhr",
    "HKQuantityTypeIdentifierVO2Max":                         "vo2max",
    "HKQuantityTypeIdentifierBodyMass":                       "weight_kg",
    "HKQuantityTypeIdentifierStepCount":                      "steps",
    "HKQuantityTypeIdentifierActiveEnergyBurned":             "active_cal",
    "HKQuantityTypeIdentifierBasalEnergyBurned":              "basal_cal",
    "HKQuantityTypeIdentifierDistanceWalkingRunning":         "distance_km",
    "HKQuantityTypeIdentifierDistanceCycling":                "distance_cycling_km",
    "HKQuantityTypeIdentifierFlightsClimbed":                 "flights",
    "HKQuantityTypeIdentifierAppleExerciseTime":              "exercise_min",
    "HKQuantityTypeIdentifierAppleStandTime":                 "stand_min",
    "HKQuantityTypeIdentifierWalkingSpeed":                   "walk_speed_kmh",
    "HKQuantityTypeIdentifierWalkingHeartRateAverage":        "walk_hr",
    "HKQuantityTypeIdentifierWalkingAsymmetryPercentage":     "walk_asymmetry",
    "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage": "walk_double_support",
    "HKQuantityTypeIdentifierHeartRate":                      "hr_sample",  # aggregated to hr_avg
    "HKQuantityTypeIdentifierBodyFatPercentage":              "body_fat_pct",
}

# Métriques qui doivent être sommées par jour (pas moyennées)
SUM_METRICS = {"steps", "active_cal", "basal_cal", "distance_km",
               "distance_cycling_km", "flights", "exercise_min", "stand_min"}

# Métriques qui doivent être moyennées par jour
AVG_METRICS = {"hrv_sdnn", "rhr", "vo2max", "weight_kg", "walk_speed_kmh",
               "walk_hr", "walk_asymmetry", "walk_double_support",
               "hr_sample", "body_fat_pct"}

# Conversions d'unités Apple Health → unités internes
UNIT_CONVERSIONS = {
    # distance : cm ou m → km
    "distance_km": lambda v, u: v / 100000 if u == "cm" else (v / 1000 if u == "m" else v),
    "distance_cycling_km": lambda v, u: v / 100000 if u == "cm" else (v / 1000 if u == "m" else v),
    # poids : lb → kg
    "weight_kg": lambda v, u: v * 0.453592 if u in ("lb", "lbs") else v,
    # vitesse : m/s → km/h
    "walk_speed_kmh": lambda v, u: v * 3.6 if u == "m/s" else v,
    # body fat : fraction → %
    "body_fat_pct": lambda v, u: v * 100 if v <= 1.0 else v,
}


def _convert(metric: str, value: float, unit: str) -> float:
    if metric in UNIT_CONVERSIONS:
        return UNIT_CONVERSIONS[metric](value, unit)
    return value


def parse_workouts(xml_path: str | Path) -> list[dict]:
    """Parse workouts → liste d'activités."""
    workouts = []
    xml_path = str(xml_path)

    def _f(value, default=0.0) -> float:
        try:
            return float(value or default)
        except (TypeError, ValueError):
            return float(default)

    AH_TYPE_MAP = {
        "HKWorkoutActivityTypeRunning":          "Running",
        "HKWorkoutActivityTypeCycling":          "Cycling",
        "HKWorkoutActivityTypeSwimming":         "Swimming",
        "HKWorkoutActivityTypeTraditionalStrengthTraining": "Strength Training",
        "HKWorkoutActivityTypeFunctionalStrengthTraining":  "Strength Training",
        "HKWorkoutActivityTypeHighIntensityIntervalTraining": "HIIT",
        "HKWorkoutActivityTypeWalking":          "Walking",
        "HKWorkoutActivityTypeYoga":             "Yoga",
        "HKWorkoutActivityTypeElliptical":       "Elliptical",
        "HKWorkoutActivityTypeRowing":           "Rowing",
        "HKWorkoutActivityTypeSurfingSports":    "Surfing",
        "HKWorkoutActivityTypeSnowboarding":     "Snowboarding",
        "HKWorkoutActivityTypeSkatingSports":    "Skating",
        "HKWorkoutActivityTypeTennis":           "Tennis",
        "HKWorkoutActivityTypeCrossCountrySkiing": "Cross Country Skiing",
        "HKWorkoutActivityTypeMindAndBody":      "Mindfulness",
        "HKWorkoutActivityTypeOther":            "Other",
        "HKWorkoutActivityTypeCrossTraining":    "Cross Training",
        "HKWorkoutActivityTypeMixedCardio":      "Cardio",
        "HKWorkoutActivityTypePilates":          "Pilates",
        "HKWorkoutActivityTypeBarre":            "Barre",
        "HKWorkoutActivityTypeCoreTraining":     "Core Training",
        "HKWorkoutActivityTypeDance":            "Dance",
        "HKWorkoutActivityTypeFlexibility":      "Flexibility",
        "HKWorkoutActivityTypeCooldown":         "Cooldown",
    }

    # Important: utiliser l'événement "end" pour lire les WorkoutStatistics enfants
    for event, elem in ET.iterparse(xml_path, events=["end"]):
        if elem.tag != "Workout":
            continue

        ah_type = elem.get("workoutActivityType", "")
        activity_type = AH_TYPE_MAP.get(ah_type, ah_type.replace("HKWorkoutActivityType", ""))
        started = elem.get("startDate", "")[:19]
        duration_s = _f(elem.get("duration", 0)) * 60  # AH stocke en minutes
        distance_m = _f(elem.get("totalDistance", 0)) * 1000  # km → m

        # calories : chercher dans les statistiques
        calories = 0
        avg_hr = None
        for stat in elem:
            if stat.tag == "WorkoutStatistics":
                qtype = stat.get("type", "")
                if "ActiveEnergyBurned" in qtype:
                    calories = _f(stat.get("sum", 0))
                elif "HeartRate" in qtype:
                    avg_hr = _f(stat.get("average", 0)) or None

        key_raw = f"ah_{started}"
        canonical_key = hashlib.md5(key_raw.encode()).hexdigest()[:16]

        workouts.append({
            "source":        "apple_health",
            "source_id":     None,
            "type":          activity_type,
            "name":          None,
            "started_at":    started,
            "duration_s":    int(duration_s),
            "distance_m":    distance_m if distance_m > 0 else None,
            "calories":      int(calories) if calories else None,
            "avg_hr":        avg_hr,
            "canonical_key": canonical_key,
        })
        elem.clear()

    return workouts


def parse_health_records(xml_path: str | Path) -> dict[str, dict[str, float]]:
    """
    Parse HKRecord → {date: {metric: value}}
    Agrège par jour (somme ou moyenne selon le type).
    Retourne aussi le sleep séparément.
    """
    xml_path = str(xml_path)

    # Accumulateurs par jour
    sums  = defaultdict(lambda: defaultdict(float))
    counts = defaultdict(lambda: defaultdict(int))

    # Sleep : phases par date de réveil
    sleep_phases = defaultdict(float)  # {date: total_asleep_hours}

    SLEEP_ASLEEP = {
        "HKCategoryValueSleepAnalysisAsleep",
        "HKCategoryValueSleepAnalysisAsleepCore",
        "HKCategoryValueSleepAnalysisAsleepDeep",
        "HKCategoryValueSleepAnalysisAsleepREM",
    }

    for event, elem in ET.iterparse(xml_path, events=["start"]):
        tag = elem.tag

        if tag == "Record":
            rec_type = elem.get("type", "")

            # Sleep
            if rec_type == "HKCategoryTypeIdentifierSleepAnalysis":
                val = elem.get("value", "")
                if val in SLEEP_ASLEEP:
                    try:
                        start = datetime.fromisoformat(elem.get("startDate", "")[:19])
                        end   = datetime.fromisoformat(elem.get("endDate",   "")[:19])
                        dur_h = (end - start).total_seconds() / 3600
                        if 0 < dur_h < 16:
                            # Attribuer au jour de réveil
                            wake_date = end.date()
                            if end.hour < 14:  # réveil avant 14h → nuit précédente
                                sleep_phases[str(wake_date)] += dur_h
                    except Exception:
                        pass
                elem.clear()
                continue

            # Quantités
            metric = HK_QUANTITY_MAP.get(rec_type)
            if not metric:
                elem.clear()
                continue

            try:
                raw_val = float(elem.get("value", 0) or 0)
                unit    = elem.get("unit", "")
                value   = _convert(metric, raw_val, unit)
                date    = elem.get("startDate", "")[:10]
                if not date or value <= 0:
                    elem.clear()
                    continue

                sums[date][metric]   += value
                counts[date][metric] += 1

            except (ValueError, TypeError):
                pass
            elem.clear()

        else:
            continue

    # Construire le résultat final
    result = defaultdict(dict)

    all_dates = set(sums.keys()) | set(sleep_phases.keys())
    for date in all_dates:
        for metric, total in sums[date].items():
            if metric == "hr_sample":
                # Moyenne des samples HR → hr_avg
                n = counts[date][metric]
                result[date]["hr_avg"] = total / n if n > 0 else None
            elif metric in SUM_METRICS:
                result[date][metric] = total
            else:
                n = counts[date][metric]
                result[date][metric] = total / n if n > 0 else None

        # Sleep
        if date in sleep_phases:
            h = sleep_phases[date]
            if 1 < h < 16:  # filtrer les valeurs aberrantes
                result[date]["sleep_h"] = round(h, 2)

    return dict(result)


def insert_activities(conn: sqlite3.Connection, workouts: list[dict]) -> tuple[int, int]:
    inserted = skipped = 0
    for w in workouts:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO activities
                   (source, source_id, type, name, started_at, duration_s,
                    distance_m, calories, avg_hr, canonical_key)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (w["source"], w["source_id"], w["type"], w["name"],
                 w["started_at"], w["duration_s"], w["distance_m"],
                 w["calories"], w["avg_hr"], w["canonical_key"]),
            )
            if conn.execute("SELECT changes()").fetchone()[0]:
                inserted += 1
            else:
                skipped += 1
        except sqlite3.Error:
            skipped += 1
    conn.commit()
    return inserted, skipped


def insert_health_metrics(conn: sqlite3.Connection,
                          daily: dict[str, dict]) -> int:
    inserted = 0
    for date, metrics in daily.items():
        for metric, value in metrics.items():
            if value is None:
                continue
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO health_metrics (date, metric, value, source)
                       VALUES (?,?,?,?)""",
                    (date, metric, float(value), "apple_health"),
                )
                inserted += 1
            except sqlite3.Error:
                pass
    conn.commit()
    return inserted


def run(xml_path: str | Path, db_path: str | Path) -> dict:
    from pipeline.schema import get_connection, init_db

    print(f"  Parsing Apple Health XML : {xml_path}")
    xml_path = Path(xml_path)
    if not xml_path.exists():
        print(f"  ⚠️  Fichier non trouvé : {xml_path}")
        return {"error": "fichier non trouvé"}

    conn = get_connection(db_path)

    # 1. Workouts
    print("  → Workouts…", end="", flush=True)
    workouts = parse_workouts(xml_path)
    ins_w, skip_w = insert_activities(conn, workouts)
    print(f" {ins_w} insérés, {skip_w} existants")

    # 2. Health records
    print("  → Health records (peut prendre 2-3 min)…", end="", flush=True)
    daily = parse_health_records(xml_path)
    ins_m = insert_health_metrics(conn, daily)
    print(f" {ins_m} métriques insérées ({len(daily)} jours)")

    conn.close()
    return {
        "workouts_inserted": ins_w,
        "workouts_skipped":  skip_w,
        "metrics_inserted":  ins_m,
        "days_covered":      len(daily),
    }


if __name__ == "__main__":
    import sys
    xml = sys.argv[1] if len(sys.argv) > 1 else "export.xml"
    db  = sys.argv[2] if len(sys.argv) > 2 else "athlete.db"
    result = run(xml, db)
    print(result)
