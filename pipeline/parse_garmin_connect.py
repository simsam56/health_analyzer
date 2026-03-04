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
# RÉCUPÉRATION MÉTRIQUES SANTÉ
# ─────────────────────────────────────────────────────────────────
def fetch_health_metrics(
    client,
    days: int = 30,
) -> list[dict]:
    """Récupère HRV, FC repos, sommeil, Body Battery des N derniers jours."""
    metrics = []
    end   = date.today()
    start = end - timedelta(days=days)

    current = start
    while current <= end:
        ds = str(current)

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

    # 2. Métriques santé
    metrics = fetch_health_metrics(client, days=days)
    ins_m = insert_health_metrics(conn, metrics)
    print(f"   ✅ Métriques santé : {ins_m} insérées")

    conn.close()

    return {
        "activities_fetched":  len(activities),
        "activities_inserted": ins_a,
        "activities_skipped":  skip_a,
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

    result = run(Path(args.db), days=args.days, email=args.email, password=args.password)
    print(f"\n📊 Résultat : {result}")
