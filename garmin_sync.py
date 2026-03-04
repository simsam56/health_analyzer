#!/usr/bin/env python3
"""
garmin_sync.py — Synchronisation Garmin Connect → athlete.db
À lancer localement sur ton Mac (pas dans le VM Cowork)

Usage :
  python3 garmin_sync.py           # 60 derniers jours
  python3 garmin_sync.py --days 90 # 90 derniers jours

Pré-requis :
  pip3 install garminconnect python-dotenv
"""
import sys
import os
import json
import sqlite3
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Charger les credentials depuis .env ──────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # Variables d'env déjà définies

try:
    import garminconnect
except ImportError:
    print("❌ garminconnect non installé. Lance : pip3 install garminconnect python-dotenv")
    sys.exit(1)

EMAIL    = os.environ.get("GARMIN_EMAIL", "")
PASSWORD = os.environ.get("GARMIN_PASSWORD", "")
DB_PATH  = Path(__file__).parent / "athlete.db"
JSON_OUT = Path(__file__).parent / "garmin_data.json"

GARMIN_TYPE_MAP = {
    "running": "Running", "trail_running": "Running",
    "cycling": "Cycling", "mountain_biking": "Cycling",
    "swimming": "Swimming", "open_water_swimming": "Swimming",
    "strength_training": "Strength Training", "fitness_equipment": "Strength Training",
    "yoga": "Yoga", "hiking": "Hiking", "walking": "Walking",
    "snowboarding": "Snowboarding", "snow_skiing": "Snowboarding",
    "backcountry_skiing_snowboarding_ws": "Snowboarding",
    "cross_country_skiing": "Cross_country_skiing",
    "stand_up_paddleboarding": "Paddling", "wakeboarding": "Wakeboarding",
    "tennis": "Tennis", "rowing": "Rowing", "other": "Other",
}


def connect_garmin():
    print(f"🔗 Connexion Garmin Connect ({EMAIL[:5]}...)...")
    tokendir = os.path.expanduser("~/.garth")

    client = garminconnect.Garmin()

    # Essai token sauvegardé
    try:
        client.login(tokenstore=tokendir)
        name = client.get_full_name()
        print(f"✅ Connecté (token) — Bonjour {name}")
        return client
    except Exception:
        pass

    # Login avec credentials
    if not EMAIL or not PASSWORD:
        print("❌ GARMIN_EMAIL / GARMIN_PASSWORD manquants dans .env")
        sys.exit(1)

    try:
        client = garminconnect.Garmin(email=EMAIL, password=PASSWORD)
        client.login()
        os.makedirs(tokendir, exist_ok=True)
        client.garth.dump(tokendir)
        name = client.get_full_name()
        print(f"✅ Connecté — Bonjour {name} (token sauvegardé)")
        return client
    except garminconnect.GarminConnectAuthenticationError:
        print("❌ Email ou mot de passe incorrect")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur connexion : {e}")
        sys.exit(1)


def fetch_activities(client, days):
    start = str(date.today() - timedelta(days=days))
    end   = str(date.today())
    print(f"\n📋 Récupération activités ({start} → {end})...")
    try:
        acts = client.get_activities_by_date(start, end, activitytype="")
        print(f"   → {len(acts)} activités trouvées")
        return acts
    except Exception as e:
        print(f"   ⚠️  Erreur : {e}")
        return []


def fetch_daily_metrics(client, days):
    print(f"\n💓 Récupération métriques santé ({days} jours)...")
    metrics = []
    today = date.today()

    for i in range(days):
        day = today - timedelta(days=i)
        ds  = str(day)

        # HRV
        try:
            d = client.get_hrv_data(ds)
            if isinstance(d, dict):
                val = (d.get("lastNight", {}) or {}).get("avg5MinHrv") or \
                      (d.get("hrvSummary", {}) or {}).get("lastNight") or \
                      d.get("hrv5MinAvg")
                if val and float(val) > 0:
                    metrics.append({"date": ds, "metric": "hrv_sdnn", "value": float(val)})
        except Exception:
            pass

        # FC repos
        try:
            d = client.get_rhr_day(ds)
            if isinstance(d, dict):
                val = None
                mm  = (d.get("allMetrics", {}) or {}).get("metricsMap", {}) or {}
                lst = mm.get("WELLNESS_RESTING_HEART_RATE", [{}])
                if lst:
                    val = lst[0].get("value")
                if not val:
                    val = d.get("restingHeartRate") or d.get("value")
                if val and float(val) > 0:
                    metrics.append({"date": ds, "metric": "rhr", "value": float(val)})
        except Exception:
            pass

        # Sommeil
        try:
            d = client.get_sleep_data(ds)
            if isinstance(d, dict):
                dto  = d.get("dailySleepDTO", {}) or {}
                secs = dto.get("sleepTimeSeconds") or dto.get("totalSleepSeconds") or \
                       d.get("sleepTimeSeconds")
                if secs and int(secs) > 0:
                    h = round(secs / 3600, 2)
                    if 2 < h < 14:
                        metrics.append({"date": ds, "metric": "sleep_h", "value": h})
        except Exception:
            pass

        # Body Battery
        try:
            d = client.get_body_battery(ds)
            if isinstance(d, list) and d:
                vals = [r.get("charged") for r in d if r.get("charged") and r.get("charged") > 0]
                if vals:
                    metrics.append({"date": ds, "metric": "body_battery", "value": max(vals)})
        except Exception:
            pass

        # Stress
        try:
            d = client.get_stress_data(ds)
            if isinstance(d, dict):
                val = d.get("avgStressLevel")
                if val and float(val) > 0:
                    metrics.append({"date": ds, "metric": "stress_avg", "value": float(val)})
        except Exception:
            pass

        # Feedback visuel tous les 10 jours
        if i % 10 == 9:
            print(f"   ... {i+1}/{days} jours traités ({len(metrics)} métriques)")

    print(f"   → {len(metrics)} métriques récupérées")
    return metrics


def save_to_db(activities, metrics):
    if not DB_PATH.exists():
        print(f"⚠️  DB non trouvée : {DB_PATH}")
        print("   Lance d'abord : python3 main.py --skip-parse")
        return

    print(f"\n💾 Écriture dans {DB_PATH}...")
    conn = sqlite3.connect(str(DB_PATH))

    # ── Activités ────────────────────────────────────────────────
    ins_a = skip_a = 0
    for act in activities:
        raw_type = str((act.get("activityType") or {}).get("typeKey", "other")).lower()
        act_type = GARMIN_TYPE_MAP.get(raw_type, raw_type.replace("_", " ").title())

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

        # Clé de dédup : type + date (arrondi 5min)
        t8  = act_type[:8].lower().replace(" ", "_")
        d   = started_at[:10]
        dur = round(duration_s / 300) * 300
        ck  = f"{t8}|{d}|{dur}"

        try:
            conn.execute("""
                INSERT OR IGNORE INTO activities
                  (source, source_id, type, name, started_at, duration_s,
                   distance_m, elev_gain_m, calories, avg_hr, max_hr,
                   avg_pace_mpm, canonical_key)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, ("garmin_connect", act_id, act_type, act_name, started_at,
                  duration_s, distance_m or None, float(elev_gain) if elev_gain else None,
                  calories or None, float(avg_hr) if avg_hr else None,
                  float(max_hr) if max_hr else None, avg_pace, ck))
            if conn.execute("SELECT changes()").fetchone()[0]:
                ins_a += 1
            else:
                skip_a += 1
        except sqlite3.Error:
            skip_a += 1

    # ── Métriques santé ──────────────────────────────────────────
    ins_m = 0
    for m in metrics:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO health_metrics (date, metric, value, source)
                VALUES (?,?,?,?)
            """, (m["date"], m["metric"], m["value"], "garmin_connect"))
            if conn.execute("SELECT changes()").fetchone()[0]:
                ins_m += 1
        except sqlite3.Error:
            pass

    conn.commit()
    conn.close()

    print(f"   ✅ Activités : {ins_a} nouvelles, {skip_a} déjà présentes")
    print(f"   ✅ Métriques santé : {ins_m} nouvelles")


def save_json(activities, metrics):
    data = {
        "synced_at":  datetime.now().isoformat(),
        "activities": activities,
        "metrics":    metrics,
    }
    JSON_OUT.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"   💾 Backup JSON : {JSON_OUT} ({JSON_OUT.stat().st_size // 1024}KB)")


def main():
    parser = argparse.ArgumentParser(description="Sync Garmin Connect → athlete.db")
    parser.add_argument("--days", type=int, default=60, help="Nb jours à récupérer (défaut: 60)")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════╗")
    print("║  Garmin Connect Sync — PerformOS v3          ║")
    print(f"║  {date.today()} · {args.days} derniers jours          ║")
    print("╚══════════════════════════════════════════════╝")

    client     = connect_garmin()
    activities = fetch_activities(client, args.days)
    metrics    = fetch_daily_metrics(client, args.days)

    save_to_db(activities, metrics)
    save_json(activities, metrics)

    print("\n✅ Sync terminée !")
    print(f"   → Lance maintenant : python3 main.py --skip-parse")
    print(f"   → Ou directement  : ./sync.sh --skip-parse")


if __name__ == "__main__":
    main()
