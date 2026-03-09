#!/usr/bin/env python3
"""
garmin_sync_full.py — Sync COMPLÈTE Garmin Connect → athlete.db
Récupère TOUTES les données historiques + quotidien en mode incrémental.

Usage :
  python3 garmin_sync_full.py              # Sync quotidienne (60j)
  python3 garmin_sync_full.py --full       # Sync complète depuis 2017
  python3 garmin_sync_full.py --days 90    # Sync N derniers jours
  python3 garmin_sync_full.py --from 2024-01-01  # Depuis une date

Ce script s'auto-installe comme tâche quotidienne (voir --install).
"""
import sys
import os
import json
import sqlite3
import argparse
import time
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent

# ── Dépendances ───────────────────────────────────────────────────
def check_deps():
    missing = []
    for pkg in ["garminconnect", "dotenv"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg if pkg != "dotenv" else "python-dotenv")
    if missing:
        print(f"❌ Dépendances manquantes : {', '.join(missing)}")
        print(f"   Lance : pip3 install {' '.join(missing)}")
        sys.exit(1)

check_deps()

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
import garminconnect

EMAIL    = os.environ.get("GARMIN_EMAIL", "")
PASSWORD = os.environ.get("GARMIN_PASSWORD", "")
DB_PATH  = ROOT / "athlete.db"
LOG_PATH = ROOT / "garmin_sync.log"
PROGRESS = ROOT / ".garmin_sync_progress.json"  # Pour résumer si interrompu

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


# ── Logging ───────────────────────────────────────────────────────
def log(msg: str):
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


# ── Connexion ─────────────────────────────────────────────────────
def connect_garmin() -> garminconnect.Garmin:
    tokendir = os.path.expanduser("~/.garth")
    client   = garminconnect.Garmin()

    # Token sauvegardé
    try:
        client.login(tokenstore=tokendir)
        name = client.get_full_name()
        log(f"✅ Connecté (token) — {name}")
        return client
    except Exception:
        pass

    # Credentials
    if not EMAIL or not PASSWORD:
        log("❌ GARMIN_EMAIL / GARMIN_PASSWORD manquants dans .env")
        sys.exit(1)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = garminconnect.Garmin(email=EMAIL, password=PASSWORD)
            client.login()
            os.makedirs(tokendir, exist_ok=True)
            client.garth.dump(tokendir)
            name = client.get_full_name()
            log(f"✅ Connecté — {name} (token sauvegardé)")
            return client
        except garminconnect.GarminConnectAuthenticationError:
            log("❌ Email ou mot de passe incorrect — vérifie .env")
            sys.exit(1)
        except garminconnect.GarminConnectTooManyRequestsError:
            wait = 60 * (attempt + 1)
            log(f"⏳ Trop de requêtes, attente {wait}s...")
            time.sleep(wait)
        except Exception as e:
            log(f"⚠️  Tentative {attempt+1}/{max_retries} — {e}")
            time.sleep(10)

    log("❌ Connexion impossible après plusieurs tentatives")
    sys.exit(1)


# ── DB ────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    if not DB_PATH.exists():
        log(f"❌ DB non trouvée : {DB_PATH}")
        log("   Lance d'abord : python3 main.py --skip-parse (depuis le dossier health_analyzer)")
        sys.exit(1)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def already_synced_dates(conn: sqlite3.Connection) -> set[str]:
    """Dates qui ont déjà des métriques Garmin Connect en base."""
    rows = conn.execute(
        "SELECT DISTINCT date FROM health_metrics WHERE source='garmin_connect'"
    ).fetchall()
    return {r[0] for r in rows}


def last_activity_date(conn: sqlite3.Connection) -> str:
    r = conn.execute(
        "SELECT MAX(date(started_at)) FROM activities WHERE source='garmin_connect'"
    ).fetchone()
    return r[0] if r and r[0] else "2017-01-01"


# ── Activités ─────────────────────────────────────────────────────
def fetch_and_insert_activities(client, conn, start: str, end: str) -> tuple[int, int]:
    log(f"📋 Activités {start} → {end}...")
    try:
        acts = client.get_activities_by_date(start, end, activitytype="")
    except garminconnect.GarminConnectTooManyRequestsError:
        log("   ⏳ Rate limit — pause 60s")
        time.sleep(60)
        acts = client.get_activities_by_date(start, end, activitytype="")
    except Exception as e:
        log(f"   ⚠️  Erreur fetch activités : {e}")
        return 0, 0

    ins = skip = 0
    for act in acts:
        raw_type = str((act.get("activityType") or {}).get("typeKey", "other")).lower()
        act_type = GARMIN_TYPE_MAP.get(raw_type, raw_type.replace("_", " ").title())

        start_str = act.get("startTimeLocal") or act.get("startTimeGMT", "")
        try:
            dt = datetime.strptime(start_str[:19], "%Y-%m-%d %H:%M:%S")
            started_at = dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            started_at = start_str[:19] if start_str else ""

        if not started_at:
            continue

        duration_s = int(act.get("duration", 0) or 0)
        distance_m = float(act.get("distance", 0) or 0)
        calories   = int(act.get("calories", 0) or 0)
        avg_hr     = act.get("averageHR")
        max_hr     = act.get("maxHR")
        elev_gain  = act.get("elevationGain")
        act_name   = act.get("activityName") or ""
        act_id     = str(act.get("activityId", ""))

        avg_pace = None
        if act_type == "Running" and distance_m > 0 and duration_s > 0:
            avg_pace = (duration_s / 60) / (distance_m / 1000)

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
                  duration_s, distance_m or None,
                  float(elev_gain) if elev_gain else None,
                  calories or None,
                  float(avg_hr) if avg_hr else None,
                  float(max_hr) if max_hr else None,
                  avg_pace, ck))
            if conn.execute("SELECT changes()").fetchone()[0]:
                ins += 1
            else:
                skip += 1
        except sqlite3.Error:
            skip += 1

    conn.commit()
    log(f"   → {len(acts)} récupérées, {ins} nouvelles, {skip} déjà présentes")
    return ins, skip


# ── Métriques santé (avec backoff intelligent) ────────────────────
def fetch_day_metrics(client, ds: str) -> list[dict]:
    """Récupère toutes les métriques d'un jour donné."""
    metrics = []

    # HRV
    try:
        d = client.get_hrv_data(ds)
        if isinstance(d, dict):
            val = ((d.get("lastNight") or {}).get("avg5MinHrv") or
                   (d.get("hrvSummary") or {}).get("lastNight") or
                   d.get("hrv5MinAvg"))
            if val and float(val) > 0:
                metrics.append({"date": ds, "metric": "hrv_sdnn", "value": float(val)})
    except Exception:
        pass

    # FC repos
    try:
        d = client.get_rhr_day(ds)
        if isinstance(d, dict):
            mm  = ((d.get("allMetrics") or {}).get("metricsMap") or {})
            lst = mm.get("WELLNESS_RESTING_HEART_RATE", [{}])
            val = (lst[0].get("value") if lst else None) or \
                  d.get("restingHeartRate") or d.get("value")
            if val and float(val) > 0:
                metrics.append({"date": ds, "metric": "rhr", "value": float(val)})
    except Exception:
        pass

    # Sommeil
    try:
        d = client.get_sleep_data(ds)
        if isinstance(d, dict):
            dto  = d.get("dailySleepDTO") or {}
            secs = (dto.get("sleepTimeSeconds") or dto.get("totalSleepSeconds") or
                    d.get("sleepTimeSeconds"))
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
            vals = [r.get("charged") for r in d
                    if (r.get("charged") or 0) > 0]
            if vals:
                metrics.append({"date": ds, "metric": "body_battery",
                                 "value": float(max(vals))})
    except Exception:
        pass

    # Stress
    try:
        d = client.get_stress_data(ds)
        if isinstance(d, dict):
            val = d.get("avgStressLevel")
            if val and float(val) > 0:
                metrics.append({"date": ds, "metric": "stress_avg",
                                 "value": float(val)})
        elif isinstance(d, list) and d:
            # Certaines versions retournent une liste
            vals = [r.get("avgStressLevel") for r in d
                    if (r.get("avgStressLevel") or 0) > 0]
            if vals:
                metrics.append({"date": ds, "metric": "stress_avg",
                                 "value": float(sum(vals) / len(vals))})
    except Exception:
        pass

    return metrics


def fetch_and_insert_metrics(client, conn,
                              start_date: date, end_date: date,
                              skip_existing: bool = True) -> int:
    existing = already_synced_dates(conn) if skip_existing else set()
    total_days = (end_date - start_date).days + 1
    ins_total  = 0
    errors     = 0

    log(f"💓 Métriques {start_date} → {end_date} ({total_days} jours)...")

    current = end_date  # Du plus récent au plus ancien
    day_num = 0
    while current >= start_date:
        ds = str(current)
        day_num += 1

        if ds in existing:
            current -= timedelta(days=1)
            continue

        # Backoff sur rate limit
        retry = 0
        while retry < 3:
            try:
                day_metrics = fetch_day_metrics(client, ds)
                break
            except garminconnect.GarminConnectTooManyRequestsError:
                wait = 30 * (retry + 1)
                log(f"   ⏳ Rate limit — pause {wait}s")
                time.sleep(wait)
                retry += 1
            except Exception:
                errors += 1
                day_metrics = []
                break

        # Insertion
        for m in day_metrics:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO health_metrics (date, metric, value, source)
                    VALUES (?,?,?,?)
                """, (m["date"], m["metric"], m["value"], "garmin_connect"))
                if conn.execute("SELECT changes()").fetchone()[0]:
                    ins_total += 1
            except sqlite3.Error:
                pass

        conn.commit()

        # Pause légère pour éviter rate limit (1 req/s)
        time.sleep(0.5)

        # Feedback progression
        if day_num % 30 == 0 or current == start_date:
            pct = day_num / total_days * 100
            log(f"   {pct:.0f}% — {ds} — {ins_total} métriques insérées")

        # Sauvegarder la progression
        PROGRESS.write_text(json.dumps({
            "last_date": ds, "ins": ins_total, "ts": datetime.now().isoformat()
        }))

        current -= timedelta(days=1)

    # Nettoyer le fichier de progression
    if PROGRESS.exists():
        PROGRESS.unlink()

    log(f"   ✅ {ins_total} métriques insérées, {errors} erreurs")
    return ins_total


# ── PIPELINE PRINCIPAL ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Garmin Connect → athlete.db")
    parser.add_argument("--days",    type=int,   default=60,
                        help="Nb jours à synchroniser (défaut: 60)")
    parser.add_argument("--from",    dest="from_date", default=None,
                        help="Date de début YYYY-MM-DD (ex: 2024-01-01)")
    parser.add_argument("--full",    action="store_true",
                        help="Sync COMPLÈTE depuis 2017 (prend 10-20 min)")
    parser.add_argument("--install", action="store_true",
                        help="Installer la sync automatique quotidienne")
    args = parser.parse_args()

    # Installation auto-run
    if args.install:
        install_launchagent()
        return

    log("=" * 56)
    log("  Garmin Connect Sync — PerformOS v3")
    log("=" * 56)

    # Calculer les dates
    end_date = date.today()
    if args.full:
        start_date = date(2017, 1, 1)
        log(f"Mode COMPLET : 2017-01-01 → {end_date}")
    elif args.from_date:
        start_date = date.fromisoformat(args.from_date)
        log(f"Mode depuis : {start_date} → {end_date}")
    else:
        start_date = end_date - timedelta(days=args.days)
        log(f"Mode incrémental : {start_date} → {end_date} ({args.days}j)")

    # Connexion
    client = connect_garmin()
    conn   = get_conn()

    # Activités (par blocs de 100j pour éviter timeouts)
    total_ins_a = 0
    chunk_end   = end_date
    while chunk_end >= start_date:
        chunk_start = max(start_date, chunk_end - timedelta(days=99))
        ins, _      = fetch_and_insert_activities(
            client, conn, str(chunk_start), str(chunk_end)
        )
        total_ins_a += ins
        chunk_end    = chunk_start - timedelta(days=1)
        if chunk_end >= start_date:
            time.sleep(2)  # Pause entre chunks

    # Métriques santé
    fetch_and_insert_metrics(client, conn, start_date, end_date,
                              skip_existing=not args.full)

    conn.close()

    # Stats finales
    conn2 = sqlite3.connect(str(DB_PATH))
    total_acts = conn2.execute(
        "SELECT COUNT(*) FROM activities WHERE source='garmin_connect'"
    ).fetchone()[0]
    total_m = conn2.execute(
        "SELECT COUNT(*) FROM health_metrics WHERE source='garmin_connect'"
    ).fetchone()[0]
    last_act = conn2.execute(
        "SELECT MAX(date(started_at)) FROM activities WHERE source='garmin_connect'"
    ).fetchone()[0]
    conn2.close()

    log("")
    log("✅ SYNC TERMINÉE")
    log(f"   Activités Garmin en base : {total_acts} (dernière : {last_act})")
    log(f"   Métriques Garmin en base : {total_m}")
    log("")
    log("→ Régénère le dashboard : python3 main.py --skip-parse")


# ── AUTO-RUN macOS (LaunchAgent) ──────────────────────────────────
def install_launchagent():
    """Installe une tâche automatique quotidienne à 06:30."""
    plist_id  = "com.performos.garmin-sync"
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_path = plist_dir / f"{plist_id}.plist"

    python_bin = sys.executable
    script_path = str(ROOT.resolve() / "garmin_sync_full.py")
    log_out = str(ROOT.resolve() / "garmin_sync.log")

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{plist_id}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_bin}</string>
        <string>{script_path}</string>
        <string>--days</string>
        <string>7</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{str(ROOT.resolve())}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>{log_out}</string>

    <key>StandardErrorPath</key>
    <string>{log_out}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>"""

    plist_dir.mkdir(parents=True, exist_ok=True)

    # Décharger l'ancien si existant
    subprocess.run(["launchctl", "unload", str(plist_path)],
                   capture_output=True, text=True)

    plist_path.write_text(plist_content)
    ret = subprocess.run(["launchctl", "load", str(plist_path)],
                        capture_output=True, text=True).returncode

    if ret == 0:
        print(f"✅ LaunchAgent installé : {plist_path}")
        print("   → Sync automatique chaque jour à 06h30")
        print(f"   → Logs : {log_out}")
        print()
        print(f"   Pour désinstaller : launchctl unload '{plist_path}' && rm '{plist_path}'")
        print(f"   Pour forcer maintenant : launchctl start {plist_id}")
    else:
        print(f"⚠️  Erreur lors du chargement du LaunchAgent (code {ret})")
        print(f"   Essaie manuellement : launchctl load '{plist_path}'")


if __name__ == "__main__":
    main()
