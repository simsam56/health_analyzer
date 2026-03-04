#!/usr/bin/env python3
"""
main.py — PerformOS v3 · Point d'entrée unique
Simon Hingant · Lorient

Usage :
  python3 main.py                              # Pipeline complet (données locales)
  python3 main.py --garmin --days 60          # + sync Garmin Connect
  python3 main.py --skip-parse                # Dashboard seulement (DB existante)
  python3 main.py --reset                     # Réinitialise la DB et re-parse

Sources de données :
  1. Apple Health XML   → export.xml (symlink ou copie)
  2. Strava FIT/CSV     → export_strava/ (symlink ou copie)
  3. Garmin Connect API → via .env (GARMIN_EMAIL / GARMIN_PASSWORD)

Architecture :
  pipeline/
    schema.py              → DDL SQLite
    parse_apple_health.py  → HK records + workouts
    parse_strava_fit.py    → FIT + CSV activities + musculation
    parse_garmin_connect.py → API activités + métriques santé temps réel
  analytics/
    training_load.py       → TSS, PMC (CTL/ATL/TSB), ACWR, Wakeboard Score
    muscle_groups.py       → Volume, imbalances, score musculaire
  dashboard/
    generator.py           → HTML dark mobile-first (Whoop/Oura/Garmin style)
"""
import argparse
import os
import secrets
import json
import sqlite3
import socket
import sys
import shutil
import importlib.util
import subprocess
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ─── Defaults ────────────────────────────────────────────────────
DB_PATH     = ROOT / "athlete.db"
AH_XML      = ROOT / "export.xml"
STRAVA_DIR  = ROOT / "export_strava"
REPORTS_DIR = ROOT / "reports"
STATE_PATH  = ROOT / ".performos_state.json"


def banner():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  ⚡  PerformOS v3 · Sport Performance Intelligence       ║")
    print(f"║     Simon Hingant · {date.today().strftime('%d %b %Y')} · {datetime.now().strftime('%H:%M')}             ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


def check_sources(ah_xml: Path, strava_dir: Path) -> None:
    """Vérifie les sources de données disponibles et alerte si manquantes."""
    print("📦 Sources de données :")
    if ah_xml.exists():
        size_mb = ah_xml.stat().st_size // (1024 * 1024)
        print(f"  ✅ Apple Health XML  : {ah_xml} ({size_mb}MB)")
    else:
        print(f"  ⚠️  Apple Health XML  : {ah_xml} — MANQUANT")
        print("     → Exporter depuis iPhone : Santé > Profil > Exporter les données")

    if strava_dir.exists():
        fit_count = len(list(strava_dir.glob("activities/*.fit"))) + \
                    len(list(strava_dir.glob("activities/*.fit.gz")))
        print(f"  ✅ Strava FIT         : {strava_dir} ({fit_count} fichiers FIT)")
    else:
        print(f"  ⚠️  Strava FIT         : {strava_dir} — MANQUANT")
        print("     → Exporter depuis strava.com > Paramètres > Mes données")
    print()


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def check_runtime_dependencies(args) -> None:
    """Affiche les dépendances critiques manquantes selon les options choisies."""
    missing = []

    if not args.skip_parse and not _has_module("fitparse"):
        missing.append("fitparse (requis pour parse Strava FIT)")

    if args.garmin and not _has_module("garminconnect"):
        missing.append("garminconnect (requis pour Garmin Connect)")
    if args.garmin and not _has_module("dotenv"):
        missing.append("python-dotenv (recommandé pour charger .env)")
    if not args.no_calendar and sys.platform == "darwin" and not _has_module("EventKit"):
        missing.append("pyobjc-framework-EventKit (requis pour sync Apple Calendar)")

    if missing:
        print("⚠️  Dépendances manquantes détectées :")
        for dep in missing:
            print(f"   - {dep}")
        print("   Installez avec : python3 -m pip install fitparse garminconnect python-dotenv pyobjc-framework-EventKit --break-system-packages")
        print()


def _compute_data_quality(conn: sqlite3.Connection) -> dict:
    """Calcule des indicateurs qualité data pour l'affichage dashboard."""
    activity_by_source = [dict(r) for r in conn.execute(
        """
        SELECT source, COUNT(*) AS n, MIN(date(started_at)) AS first_date, MAX(date(started_at)) AS last_date
        FROM activities GROUP BY source ORDER BY source
        """
    ).fetchall()]

    metrics_by_source = [dict(r) for r in conn.execute(
        "SELECT source, COUNT(*) AS n FROM health_metrics GROUP BY source ORDER BY source"
    ).fetchall()]

    freshness = [dict(r) for r in conn.execute(
        """
        SELECT metric, MAX(date) AS last_date,
               CAST(julianday('now') - julianday(MAX(date)) AS INT) AS days_old
        FROM health_metrics
        GROUP BY metric
        ORDER BY days_old ASC
        """
    ).fetchall()]

    duplicates = conn.execute(
        """
        WITH g AS (
          SELECT lower(type) AS t, date(started_at) AS d,
                 CAST(ROUND(COALESCE(duration_s,0)/300.0)*300 AS INT) AS dur5,
                 COUNT(*) AS n
          FROM activities
          WHERE started_at IS NOT NULL
          GROUP BY t,d,dur5
          HAVING COUNT(*) > 1
        )
        SELECT COALESCE(SUM(n),0) FROM g
        """
    ).fetchone()[0] or 0

    ex_total, ex_name_missing, ex_weight_missing = conn.execute(
        """
        SELECT COUNT(*),
               SUM(CASE WHEN exercise_name IS NULL OR trim(exercise_name)='' OR lower(exercise_name)='none' THEN 1 ELSE 0 END),
               SUM(CASE WHEN weight_kg IS NULL OR weight_kg<=0 THEN 1 ELSE 0 END)
        FROM exercise_sets
        """
    ).fetchone()
    ex_total = ex_total or 0
    ex_name_missing = ex_name_missing or 0
    ex_weight_missing = ex_weight_missing or 0

    stale_critical = [
        x for x in freshness
        if x["metric"] in ("hrv_sdnn", "rhr", "sleep_h") and (x["days_old"] or 9999) > 45
    ]

    completeness_penalty = 0
    if ex_total:
        completeness_penalty += (ex_name_missing / ex_total) * 12
        completeness_penalty += (ex_weight_missing / ex_total) * 8
    duplicate_penalty = min(15, duplicates / 10)
    stale_penalty = min(25, len(stale_critical) * 8)
    score = max(0.0, 100.0 - completeness_penalty - duplicate_penalty - stale_penalty)

    return {
        "score": round(score, 1),
        "activity_by_source": activity_by_source,
        "metrics_by_source": metrics_by_source,
        "freshness": freshness,
        "duplicates_rows": int(duplicates),
        "exercise_sets_total": int(ex_total),
        "exercise_name_missing_pct": round((ex_name_missing / ex_total) * 100, 1) if ex_total else 0.0,
        "exercise_weight_missing_pct": round((ex_weight_missing / ex_total) * 100, 1) if ex_total else 0.0,
    }


def _compute_progress_series(conn: sqlite3.Connection) -> dict:
    """Séries longues simplifiées pour la page Progression."""
    training_hours_weekly = [dict(r) for r in conn.execute(
        """
        SELECT strftime('%Y-W%W', started_at) AS label,
               ROUND(SUM(COALESCE(duration_s,0))/3600.0, 2) AS value
        FROM activities
        WHERE started_at IS NOT NULL
        GROUP BY label
        ORDER BY label
        """
    ).fetchall()]

    running_km_weekly = [dict(r) for r in conn.execute(
        """
        SELECT strftime('%Y-W%W', started_at) AS label,
               ROUND(SUM(COALESCE(distance_m,0))/1000.0, 2) AS value
        FROM activities
        WHERE type='Running' AND distance_m > 0
        GROUP BY label
        ORDER BY label
        """
    ).fetchall()]

    # Estimation 10k hebdo plus robuste via Riegel (plutôt que simple allure moyenne)
    run_rows = conn.execute(
        """
        SELECT started_at, duration_s, distance_m
        FROM activities
        WHERE type='Running' AND distance_m > 0 AND duration_s > 0
        ORDER BY started_at
        """
    ).fetchall()
    by_week: dict[str, list[float]] = defaultdict(list)
    for r in run_rows:
        started_at, dur_s, dist_m = r
        if not started_at:
            continue
        label = str(started_at)[:10]
        # Même convention de label que les autres séries
        wk = datetime.fromisoformat(label).strftime("%Y-W%W")
        d = float(dist_m or 0)
        t_min = float(dur_s or 0) / 60.0
        if d < 3000 or d > 21100 or t_min <= 0:
            continue
        pred_10k = t_min * ((10000.0 / d) ** 1.06)
        if 25 <= pred_10k <= 120:
            by_week[wk].append(pred_10k)

    est_10k_weekly = []
    for wk in sorted(by_week.keys()):
        vals = sorted(by_week[wk])
        if not vals:
            continue
        top_n = max(1, min(len(vals), len(vals) // 2))
        value = vals[0] if len(vals) == 1 else sum(vals[:top_n]) / top_n
        est_10k_weekly.append({"label": wk, "value": round(value, 2)})

    vo2max_series = [dict(r) for r in conn.execute(
        """
        SELECT date AS label, ROUND(value, 2) AS value
        FROM health_metrics
        WHERE metric='vo2max' AND value IS NOT NULL
        ORDER BY date
        """
    ).fetchall()]

    return {
        "training_hours_weekly": training_hours_weekly,
        "running_km_weekly": running_km_weekly,
        "est_10k_weekly": est_10k_weekly,
        "vo2max_series": vo2max_series,
    }


def deduplicate_activities(db_path: Path) -> int:
    """
    Supprime les doublons inter-sources (type + date + durée arrondie 5 min),
    en conservant la meilleure source (Strava > Garmin > Apple).
    Ne touche pas aux activités liées aux séances de musculation.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")

    before = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    conn.execute(
        """
        WITH ranked AS (
            SELECT
                a.id,
                ROW_NUMBER() OVER (
                    PARTITION BY lower(COALESCE(a.type,'')),
                                 date(a.started_at),
                                 CAST(ROUND(COALESCE(a.duration_s,0)/300.0)*300 AS INT)
                    ORDER BY
                        CASE a.source
                            WHEN 'strava_fit' THEN 0
                            WHEN 'garmin_connect' THEN 1
                            WHEN 'apple_health' THEN 2
                            ELSE 9
                        END ASC,
                        (CASE WHEN a.avg_hr IS NOT NULL THEN 1 ELSE 0 END +
                         CASE WHEN a.calories IS NOT NULL THEN 1 ELSE 0 END +
                         CASE WHEN a.distance_m IS NOT NULL THEN 1 ELSE 0 END) DESC,
                        a.id ASC
                ) AS rn
            FROM activities a
            WHERE a.started_at IS NOT NULL
        )
        DELETE FROM activities
        WHERE id IN (
            SELECT r.id
            FROM ranked r
            WHERE r.rn > 1
        )
        AND id NOT IN (
            SELECT activity_id FROM strength_sessions WHERE activity_id IS NOT NULL
        )
        """
    )
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    conn.close()
    return max(0, before - after)


def _strength_session_quality(conn: sqlite3.Connection, session_id: int) -> float:
    row = conn.execute(
        """
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN muscle_group IS NOT NULL AND muscle_group NOT IN ('Inconnu','Cardio') THEN 1 ELSE 0 END) AS known,
          SUM(CASE WHEN reps IS NOT NULL AND reps > 0 THEN 1 ELSE 0 END) AS reps_sets,
          SUM(CASE WHEN weight_kg IS NOT NULL AND weight_kg > 0 THEN 1 ELSE 0 END) AS weighted_sets
        FROM exercise_sets
        WHERE session_id=?
        """,
        (session_id,),
    ).fetchone()
    if not row:
        return 0.0
    total = float(row[0] or 0)
    known = float(row[1] or 0)
    reps_sets = float(row[2] or 0)
    weighted_sets = float(row[3] or 0)
    return known * 2.0 + reps_sets * 3.0 + weighted_sets * 4.0 + total * 0.05


def deduplicate_strength_sessions(db_path: Path) -> int:
    """
    Fusionne les doublons de séances muscu cross-source (souvent Garmin vs Strava),
    en conservant la version la plus riche en données de séries.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")

    # Backfill source manquante depuis l'activité liée.
    conn.execute(
        """
        UPDATE strength_sessions
        SET source = (
            SELECT a.source
            FROM activities a
            WHERE a.id = strength_sessions.activity_id
        )
        WHERE (source IS NULL OR source='')
          AND activity_id IS NOT NULL
        """
    )

    merged = 0

    while True:
        pair = conn.execute(
            """
            SELECT
              s1.id, COALESCE(s1.source,''), COALESCE(s1.activity_id,0), COALESCE(s1.total_reps,0),
              s2.id, COALESCE(s2.source,''), COALESCE(s2.activity_id,0), COALESCE(s2.total_reps,0)
            FROM strength_sessions s1
            JOIN strength_sessions s2 ON s1.id < s2.id
            WHERE s1.started_at IS NOT NULL
              AND s2.started_at IS NOT NULL
              AND date(s1.started_at) = date(s2.started_at)
              AND ABS(COALESCE(s1.total_sets,0) - COALESCE(s2.total_sets,0)) <= 1
              AND ABS(COALESCE(s1.duration_s,0) - COALESCE(s2.duration_s,0)) <= 180
              AND ABS(strftime('%s', s1.started_at) - strftime('%s', s2.started_at)) <= 7200
              AND COALESCE(s1.source,'') <> COALESCE(s2.source,'')
              AND (COALESCE(s1.source,'')='garmin_connect' OR COALESCE(s2.source,'')='garmin_connect')
            ORDER BY s1.id ASC, s2.id ASC
            LIMIT 1
            """
        ).fetchone()

        if not pair:
            break

        id_a, src_a, act_a, reps_a, id_b, src_b, act_b, reps_b = pair

        def src_score(src: str) -> float:
            return {
                "garmin_connect": 6.0,
                "strava_fit": 4.0,
                "apple_health": 2.0,
            }.get(src, 1.0)

        score_a = _strength_session_quality(conn, id_a) + src_score(src_a)
        score_b = _strength_session_quality(conn, id_b) + src_score(src_b)

        keep_id, drop_id = (id_a, id_b) if score_a >= score_b else (id_b, id_a)
        keep_src, drop_src = (src_a, src_b) if keep_id == id_a else (src_b, src_a)
        keep_act, drop_act = (act_a, act_b) if keep_id == id_a else (act_b, act_a)
        keep_reps, drop_reps = (reps_a, reps_b) if keep_id == id_a else (reps_b, reps_a)

        keep_quality = _strength_session_quality(conn, keep_id)
        drop_quality = _strength_session_quality(conn, drop_id)
        if drop_quality > keep_quality + 0.5:
            conn.execute("DELETE FROM exercise_sets WHERE session_id=?", (keep_id,))
            conn.execute(
                """
                INSERT INTO exercise_sets
                  (session_id, started_at, exercise_name, exercise_category, muscle_group,
                   muscle_subgroup, set_index, set_type, reps, duration_s, weight_kg)
                SELECT ?, started_at, exercise_name, exercise_category, muscle_group,
                       muscle_subgroup, set_index, set_type, reps, duration_s, weight_kg
                FROM exercise_sets
                WHERE session_id=?
                ORDER BY id
                """,
                (keep_id, drop_id),
            )

        if (not keep_act or int(keep_act) == 0) and drop_act and int(drop_act) > 0:
            conn.execute("UPDATE strength_sessions SET activity_id=? WHERE id=?", (drop_act, keep_id))
        if (not keep_reps or int(keep_reps) == 0) and drop_reps and int(drop_reps) > 0:
            conn.execute("UPDATE strength_sessions SET total_reps=? WHERE id=?", (drop_reps, keep_id))
        if keep_src in ("", "local") and drop_src:
            conn.execute("UPDATE strength_sessions SET source=? WHERE id=?", (drop_src, keep_id))

        conn.execute("DELETE FROM exercise_sets WHERE session_id=?", (drop_id,))
        conn.execute("DELETE FROM strength_sessions WHERE id=?", (drop_id,))
        merged += 1

    conn.commit()
    conn.close()
    return merged


def backup_db(db_path: Path) -> None:
    """Sauvegarde la DB avant un reset."""
    if db_path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = db_path.with_suffix(f".bak_{ts}.db")
        shutil.copy2(db_path, bak)
        print(f"  💾 Backup DB : {bak}")


def _safe_file_signature(path: Path) -> dict | None:
    if not path.exists() or not path.is_file():
        return None
    st = path.stat()
    return {
        "path": str(path),
        "size": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def _strava_signature(strava_dir: Path) -> dict | None:
    if not strava_dir.exists():
        return None
    csv_sig = _safe_file_signature(strava_dir / "activities.csv")
    acts_dir = strava_dir / "activities"
    fit_count = 0
    latest_ns = 0
    if acts_dir.exists():
        for p in acts_dir.iterdir():
            if not p.is_file():
                continue
            n = p.name.lower()
            if not (n.endswith(".fit") or n.endswith(".fit.gz")):
                continue
            fit_count += 1
            st = p.stat()
            mt = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
            if mt > latest_ns:
                latest_ns = mt
    return {
        "dir": str(strava_dir),
        "csv": csv_sig,
        "fit_count": fit_count,
        "fit_latest_mtime_ns": latest_ns,
    }


def _load_state(path: Path = STATE_PATH) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict, path: Path = STATE_PATH) -> None:
    try:
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _db_has_local_data(db_path: Path) -> bool:
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        act = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        hm = conn.execute("SELECT COUNT(*) FROM health_metrics").fetchone()[0]
        conn.close()
        return act > 0 and hm > 0
    except Exception:
        return False


def _pick_available_port(preferred: int, host: str = "127.0.0.1", tries: int = 10) -> int:
    for p in [preferred] + [preferred + i for i in range(1, tries)]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((host, p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    return preferred


def main():
    parser = argparse.ArgumentParser(
        description="PerformOS v3 — Sport Performance Dashboard"
    )
    parser.add_argument("--export",     default=str(AH_XML),
                        help="Chemin vers export.xml Apple Health")
    parser.add_argument("--strava",     default=str(STRAVA_DIR),
                        help="Dossier export Strava")
    parser.add_argument("--db",         default=str(DB_PATH),
                        help="Chemin base SQLite")
    parser.add_argument("--output",     default=None,
                        help="Fichier HTML de sortie")
    parser.add_argument("--garmin",     action="store_true",
                        help="Synchroniser Garmin Connect (nécessite .env)")
    parser.add_argument("--days",       type=int, default=30,
                        help="Nb jours Garmin à synchroniser")
    parser.add_argument("--garmin-min-interval-min", type=int, default=45,
                        help="Intervalle minimum entre deux sync Garmin (minutes, smart skip)")
    parser.add_argument("--force-garmin", action="store_true",
                        help="Forcer la sync Garmin même si une sync récente existe (plus lent)")
    parser.add_argument("--garmin-refresh-tail-days", type=int, default=3,
                        help="Même en sync forcée, ne refresh complètement que les N derniers jours (incrémental)")
    parser.add_argument("--skip-parse", action="store_true",
                        help="Sauter Apple Health + Strava (utiliser DB existante)")
    parser.add_argument("--force-parse", action="store_true",
                        help="Forcer le parsing Apple Health + Strava même si sources inchangées")
    parser.add_argument("--reset",      action="store_true",
                        help="Réinitialiser la DB (backup automatique)")
    parser.add_argument("--weeks-muscle", type=int, default=8,
                        help="Fenêtre analyse musculaire (semaines)")
    parser.add_argument("--audit",      action="store_true",
                        help="Afficher rapport d'audit des données")
    parser.add_argument("--calendar-days", type=int, default=21,
                        help="Fenêtre agenda Apple Calendar (jours à venir)")
    parser.add_argument("--no-calendar", action="store_true",
                        help="Désactiver la sync agenda Apple Calendar")
    parser.add_argument("--no-dedup", action="store_true",
                        help="Désactiver la déduplication inter-sources des activités")
    parser.add_argument("--add-task", default=None,
                        help="Ajouter une tâche pilotage (titre)")
    parser.add_argument("--task-category", default="sante",
                        help="Catégorie tâche: sante|travail|relationnel|apprentissage|autre")
    parser.add_argument("--task-date", default=None,
                        help="Date tâche (YYYY-MM-DD)")
    parser.add_argument("--task-time", default="09:00:00",
                        help="Heure tâche (HH:MM[:SS])")
    parser.add_argument("--task-duration-min", type=int, default=60,
                        help="Durée tâche en minutes")
    parser.add_argument("--task-notes", default=None,
                        help="Notes tâche")
    parser.add_argument("--task-sync-apple", action="store_true",
                        help="Créer aussi l'événement dans Apple Calendar")
    parser.add_argument("--task-calendar", default=None,
                        help="Nom calendrier Apple cible (optionnel)")
    parser.add_argument("--serve", action="store_true",
                        help="Lance un serveur local pour interactions UI persistantes")
    parser.add_argument("--serve-port", type=int, default=8765,
                        help="Port du serveur local PerformOS")
    args = parser.parse_args()

    banner()

    db_path    = Path(args.db)
    ah_xml     = Path(args.export)
    strava_dir = Path(args.strava)
    output_path = Path(args.output) if args.output else \
                  REPORTS_DIR / f"dashboard_{date.today()}.html"

    check_sources(ah_xml, strava_dir)
    check_runtime_dependencies(args)

    # ─── Reset optionnel ─────────────────────────────────────────
    if args.reset:
        print("🔄 Reset base de données…")
        backup_db(db_path)
        if db_path.exists():
            db_path.unlink()
        print()

    # ─── 1. Initialisation DB ────────────────────────────────────
    print("🗄️  Initialisation base de données…")
    from pipeline.schema import init_db, get_connection
    conn = init_db(db_path)
    conn.close()
    print(f"   DB : {db_path}")
    print()

    serve_port = None
    api_token = ""
    serve_thread = None
    early_server_started = False
    if args.serve:
        api_token = (os.getenv("PERFORMOS_API_TOKEN") or "").strip() or secrets.token_urlsafe(24)
        serve_port = _pick_available_port(args.serve_port, host="127.0.0.1", tries=10)
        if output_path.exists():
            try:
                from cockpit_server import serve as serve_cockpit
                serve_thread = threading.Thread(
                    target=serve_cockpit,
                    kwargs={
                        "dashboard_path": output_path,
                        "db_path": db_path,
                        "host": "127.0.0.1",
                        "port": serve_port,
                        "api_token": api_token,
                    },
                    daemon=True,
                )
                serve_thread.start()
                if serve_port != args.serve_port:
                    print(f"⚠️  Port {args.serve_port} occupé — utilisation du port {serve_port}")
                url = f"http://127.0.0.1:{serve_port}"
                print(f"⚡ Cockpit lancé immédiatement: {url}")
                print("   Données en cours de rafraîchissement…")
                try:
                    subprocess.Popen(["open", url])
                except Exception:
                    pass
                print()
                early_server_started = True
            except Exception:
                early_server_started = False

    garmin_connected = False
    calendar_sync = {"enabled": False, "error": "disabled", "events_synced": 0}
    local_parse_performed = False
    new_activities_hint = 0

    # ─── 1.5 Ajout tâche pilotage (optionnel) ───────────────────
    if args.add_task:
        from analytics.planner import add_task, parse_task_datetime
        task_date = args.task_date or str(date.today())
        try:
            start_at, end_at = parse_task_datetime(
                task_date=task_date,
                task_time=args.task_time,
                duration_min=args.task_duration_min,
            )
        except Exception as e:
            print(f"❌ Format date/heure tâche invalide: {e}")
            return

        add_res = add_task(
            db_path=db_path,
            title=args.add_task,
            category=args.task_category,
            start_at=start_at,
            end_at=end_at,
            notes=args.task_notes,
            sync_to_apple=args.task_sync_apple,
            apple_calendar_name=args.task_calendar,
        )
        print(
            f"📝 Tâche ajoutée: #{add_res.get('task_id')} "
            f"[{add_res.get('category')}] {start_at} → {end_at}"
        )
        if add_res.get("apple_sync_error"):
            print(f"   ⚠️  Sync Apple: {add_res.get('apple_sync_error')}")
        elif args.task_sync_apple:
            print(f"   ✅ Sync Apple OK (uid={add_res.get('apple_uid')})")
        print()

    state = _load_state()
    source_state = state.get("local_sources", {})
    apple_sig = _safe_file_signature(ah_xml)
    strava_sig = _strava_signature(strava_dir)
    bootstrap_skip = False

    parse_apple = False
    parse_strava = False
    if args.skip_parse:
        print("⏭️  Parsing Apple Health + Strava ignoré (--skip-parse)\n")
    else:
        force_parse = args.force_parse or args.reset
        if force_parse:
            parse_apple = ah_xml.exists()
            parse_strava = strava_dir.exists()
        else:
            if not source_state and _db_has_local_data(db_path):
                bootstrap_skip = True
                print("⚡ Smart skip initialisé (DB déjà peuplée): Apple/Strava ignorés par défaut.")
                print("   Utilisez --force-parse si vous avez un nouvel export local.")
                print()
            parse_apple = ah_xml.exists() and (not bootstrap_skip) and (apple_sig != source_state.get("apple"))
            parse_strava = strava_dir.exists() and (not bootstrap_skip) and (strava_sig != source_state.get("strava"))

        # ─── 2. Apple Health ─────────────────────────────────────
        if ah_xml.exists():
            if parse_apple:
                print("🍎 Pipeline Apple Health…")
                from pipeline.parse_apple_health import run as run_ah
                result_ah = run_ah(xml_path=ah_xml, db_path=db_path)
                local_parse_performed = True
                new_activities_hint += int(result_ah.get("workouts_inserted", 0) or 0)
                print(f"   Workouts : {result_ah.get('workouts_inserted',0)} insérés")
                print(
                    "   Métriques : "
                    f"{result_ah.get('metrics_new',0)} nouvelles, "
                    f"{result_ah.get('metrics_updated',0)} mises à jour, "
                    f"{result_ah.get('metrics_unchanged',0)} inchangées "
                    f"({result_ah.get('days_covered',0)} jours)"
                )
                print()
            else:
                print("⏭️  Apple Health inchangé — parsing ignoré (smart skip)\n")
        else:
            print("⚠️  Apple Health XML non trouvé — étape ignorée\n")

        # ─── 3. Strava FIT ───────────────────────────────────────
        if strava_dir.exists():
            if parse_strava:
                print("🏃 Pipeline Strava FIT…")
                from pipeline.parse_strava_fit import run as run_strava
                st = run_strava(strava_dir=strava_dir, db_path=db_path)
                local_parse_performed = True
                new_activities_hint += int((st or {}).get("inserted", 0) or 0)
                print()
            else:
                print("⏭️  Strava inchangé — parsing ignoré (smart skip)\n")
        else:
            print("⚠️  Dossier Strava non trouvé — étape ignorée\n")

    state["local_sources"] = {"apple": apple_sig, "strava": strava_sig}
    state["updated_at"] = datetime.now().replace(microsecond=0).isoformat()
    _save_state(state)

    # ─── 4. Garmin Connect (optionnel) ───────────────────────────
    if args.garmin:
        garmin_state = state.get("garmin", {})
        should_sync_garmin = True
        if not args.force_garmin and garmin_state.get("last_sync_at"):
            try:
                last_dt = datetime.fromisoformat(str(garmin_state.get("last_sync_at")))
                age_min = (datetime.now() - last_dt).total_seconds() / 60.0
                last_days = int(garmin_state.get("last_days") or 0)
                if age_min < max(1, args.garmin_min_interval_min) and last_days >= args.days:
                    should_sync_garmin = False
                    print(
                        f"⏭️  Garmin ignoré (sync récente il y a {age_min:.0f} min, "
                        f"fenêtre {last_days}j déjà couverte)"
                    )
            except Exception:
                pass

        if should_sync_garmin:
            print(f"⌚ Pipeline Garmin Connect ({args.days} derniers jours)…")
            from pipeline.parse_garmin_connect import run as run_garmin
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
            result_gc = run_garmin(
                db_path=db_path,
                days=args.days,
                email=os.environ.get("GARMIN_EMAIL"),
                password=os.environ.get("GARMIN_PASSWORD"),
                refresh_tail_days=max(1, int(args.garmin_refresh_tail_days)),
            )
            if "error" not in result_gc:
                garmin_connected = True
                new_activities_hint += int(result_gc.get("activities_inserted", 0) or 0)
                print(f"   Activités : {result_gc.get('activities_inserted',0)} nouvelles")
                print(f"   Métriques : {result_gc.get('metrics_inserted',0)} nouvelles")
                state["garmin"] = {
                    "last_sync_at": datetime.now().replace(microsecond=0).isoformat(),
                    "last_days": int(args.days),
                }
                _save_state(state)
            else:
                print(f"   ⚠️  {result_gc.get('error','erreur inconnue')}")
        print()
    else:
        print("ℹ️  Garmin Connect : non activé (utilisez --garmin pour synchroniser)\n")

    # ─── 4.5 Dédup activités (optionnel) ────────────────────────
    if not args.no_dedup:
        if local_parse_performed or new_activities_hint > 0:
            removed = deduplicate_activities(db_path)
            print(f"🧹 Dédup activités : {removed} doublons supprimés")
        else:
            print("⏭️  Dédup activités : ignorée (aucune activité nouvelle)")
        merged_strength = deduplicate_strength_sessions(db_path)
        if merged_strength > 0:
            print(f"🧹 Dédup musculation : {merged_strength} séance(s) fusionnée(s)")
        else:
            print("⏭️  Dédup musculation : rien à fusionner")
        print()

    # ─── 5.0 Agenda Apple Calendar (optionnel) ──────────────────
    if not args.no_calendar:
        try:
            from integrations.apple_calendar import sync_apple_calendar
            calendar_sync = sync_apple_calendar(
                db_path=db_path,
                days_ahead=args.calendar_days,
            )
            if calendar_sync.get("enabled"):
                print(f"🗓️  Apple Calendar : {calendar_sync.get('events_synced',0)} événements synchronisés")
            else:
                err = calendar_sync.get("error", "indisponible")
                print(f"🗓️  Apple Calendar : {err}")
                if err == "calendar_permission_denied":
                    print("   → Autorisez le calendrier dans:")
                    print("     Réglages Système > Confidentialité et sécurité > Calendriers")
                    print("     puis relancez python3 main.py")
                elif err == "eventkit_unavailable":
                    print("   → Installez EventKit: python3 -m pip install pyobjc-framework-EventKit --break-system-packages")
        except Exception as e:
            calendar_sync = {"enabled": False, "error": str(e), "events_synced": 0}
            print(f"🗓️  Apple Calendar : erreur ({e})")
        print()

    # ─── 6. Audit optionnel ──────────────────────────────────────
    if args.audit:
        _print_audit(db_path)

    # ─── 6. Analytics ────────────────────────────────────────────
    print("📈 Calcul charge d'entraînement…")
    from analytics.training_load import run as run_training
    training = run_training(db_path=db_path, verbose=True)
    print()

    print(f"💪 Analyse musculaire ({args.weeks_muscle} semaines)…")
    from analytics.muscle_groups import run as run_muscles
    muscles = run_muscles(db_path=db_path, weeks=args.weeks_muscle)
    print()

    # ─── 7. Métriques santé pour le dashboard ────────────────────
    conn = get_connection(db_path)
    metrics_history = [
        dict(row) for row in conn.execute(
            "SELECT date, metric, value, source FROM health_metrics ORDER BY date"
        ).fetchall()
    ]
    daily_load_rows = [
        dict(row) for row in conn.execute(
            "SELECT date, ctl, atl, tsb, tss FROM daily_load ORDER BY date"
        ).fetchall()
    ]
    has_garmin_data = conn.execute(
        "SELECT COUNT(*) FROM activities WHERE source='garmin_connect'"
    ).fetchone()[0] > 0
    data_quality = _compute_data_quality(conn)
    progress_series = _compute_progress_series(conn)

    agenda_events = []
    if not args.no_calendar:
        try:
            from integrations.apple_calendar import get_upcoming_events
            agenda_events = get_upcoming_events(
                db_path=db_path,
                days_ahead=args.calendar_days,
                limit=40,
            )
        except Exception:
            agenda_events = []

    # ─── 7.5 Pilotage hebdo ─────────────────────────────────────
    from analytics.planner import get_planner_events, weekly_category_summary, weekly_series
    start_window = (date.today() - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00")
    end_window = (date.today() + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59")
    planner_events = get_planner_events(conn, start_at=start_window, end_at=end_window)
    week_start = date.today() - timedelta(days=date.today().weekday())
    planner_summary = weekly_category_summary(planner_events, week_start=week_start)
    planner_series = weekly_series(conn)
    pending_calendar_sync = conn.execute(
        """
        SELECT COUNT(*) FROM planner_tasks
        WHERE status!='cancelled' AND (calendar_uid IS NULL OR calendar_uid='')
        """
    ).fetchone()[0]

    conn.close()

    training["garmin_connected"] = garmin_connected or has_garmin_data
    training["calendar_sync"] = calendar_sync
    training["calendar_sync"]["pending_tasks"] = int(pending_calendar_sync or 0)
    training["agenda_events"] = agenda_events
    training["data_quality"] = data_quality
    training["progress"] = progress_series
    training["pilotage"] = {
        "events": planner_events,
        "week_start": str(week_start),
        "summary": planner_summary,
        "series": planner_series,
    }
    if args.serve and not api_token:
        api_token = (os.getenv("PERFORMOS_API_TOKEN") or "").strip() or secrets.token_urlsafe(24)

    # ─── 8. Sports Agent ─────────────────────────────────────────
    print("🤖 Sports Analysis Agent…")
    sports_agent_data = {}
    try:
        from analytics.sports_agent import run_sports_agent
        acwr_current = float(training.get("acwr", {}).get("acwr", 1.0) or 1.0)
        sports_agent_data = run_sports_agent(db_path=DB_PATH, acwr_val=acwr_current)
        recs = sports_agent_data.get("recommendations", [])
        print(f"  ✅ {len(recs)} recommandations générées")
        if recs:
            print(f"     Top: [{recs[0].get('severity','?').upper()}] {recs[0].get('title','')}")
    except Exception as e:
        print(f"  ⚠️  Sports agent error: {e}")

    # ─── 9. Dashboard HTML ───────────────────────────────────────
    print("🎨 Génération dashboard premium…")
    try:
        from dashboard.generator_premium import generate_html
    except ImportError:
        from dashboard.generator import generate_html
    generate_html(
        training=training,
        muscles=muscles,
        metrics_history=metrics_history,
        daily_load_rows=daily_load_rows,
        output_path=output_path,
        api_token=api_token,
        sports_agent=sports_agent_data,
    )
    print()

    # ─── Résumé ──────────────────────────────────────────────────
    wbs   = training.get("wakeboard", {})
    acwr  = training.get("acwr", {})
    pmc   = training.get("pmc", {})
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Wakeboard Score : {wbs.get('score',0):.0f}/100 ({wbs.get('label','—')})")
    print(f"  ACWR            : {acwr.get('acwr',0):.2f} (zone: {acwr.get('zone','—')})")
    print(f"  CTL/ATL/TSB     : {pmc.get('ctl',0):.1f} / {pmc.get('atl',0):.1f} / {pmc.get('tsb',0):+.1f}")
    print(f"  Muscle Score    : {muscles.get('muscle_score',0):.0f}/100")
    print(f"  Dashboard       : {output_path}")
    if not args.garmin:
        print()
        print("  Tip : Ajoutez --garmin pour synchroniser les donnees Garmin")
        print("        et enrichir les métriques récentes")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    if args.serve:
        if serve_port is None:
            serve_port = _pick_available_port(args.serve_port, host="127.0.0.1", tries=10)
        if early_server_started and serve_thread is not None:
            print("🌐 Cockpit déjà lancé — rafraîchissez la page pour voir les données mises à jour.")
            try:
                serve_thread.join()
            except KeyboardInterrupt:
                pass
        else:
            if serve_port != args.serve_port:
                print(f"⚠️  Port {args.serve_port} occupé — utilisation du port {serve_port}")
            url = f"http://127.0.0.1:{serve_port}"
            print(f"🌐 Lancement serveur cockpit: {url}")
            try:
                subprocess.Popen(["open", url])
            except Exception:
                pass
            from cockpit_server import serve as serve_cockpit
            serve_cockpit(
                dashboard_path=output_path,
                db_path=db_path,
                host="127.0.0.1",
                port=serve_port,
                api_token=api_token,
            )


def _print_audit(db_path: Path):
    """Rapport d'audit des données en base."""
    conn = sqlite3.connect(str(db_path))
    print("=" * 60)
    print("AUDIT DES DONNÉES")
    print("=" * 60)

    # Comptes par table
    for tbl in ["activities", "strength_sessions", "exercise_sets",
                "health_metrics", "daily_load", "weekly_muscle_volume",
                "calendar_events", "planner_tasks"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:<25} {n:>6} lignes")
    print()

    # Activités par source et plage
    print("ACTIVITÉS PAR SOURCE :")
    for row in conn.execute("""
        SELECT source, COUNT(*), MIN(date(started_at)), MAX(date(started_at))
        FROM activities GROUP BY source ORDER BY source
    """).fetchall():
        print(f"  {row[0]:<20} {row[1]:4d} activités  {row[2]} → {row[3]}")
    print()

    # Gaps temporels (> 30 jours sans activité, 1 an glissant)
    print("GAPS TEMPORELS (>21j sans activité) :")
    acts = conn.execute("""
        SELECT date(started_at) as d FROM activities
        WHERE started_at > date('now', '-365 days')
        ORDER BY d
    """).fetchall()
    from datetime import date as ddate, timedelta
    prev = None
    for (d,) in acts:
        curr = ddate.fromisoformat(d)
        if prev and (curr - prev).days > 21:
            print(f"  GAP {prev} → {d} ({(curr-prev).days}j)")
        prev = curr
    print()

    # Métriques santé
    print("METRIQUES SANTE (dernieres valeurs) :")
    for row in conn.execute("""
        SELECT metric, MAX(date), AVG(value), COUNT(*)
        FROM health_metrics GROUP BY metric ORDER BY MAX(date) DESC
    """).fetchall():
        print(f"  {row[0]:<25} last={row[1]}  avg={row[2]:.1f}  n={row[3]}")
    print()

    # Sessions muscu détail
    print("SESSIONS MUSCU RECENTES :")
    for row in conn.execute("""
        SELECT started_at, workout_name, total_sets
        FROM strength_sessions ORDER BY started_at DESC LIMIT 5
    """).fetchall():
        print(f"  {row[0][:10]} | {str(row[1])[:30]:<30} | {row[2]} sets")

    print("=" * 60)
    print()
    conn.close()


if __name__ == "__main__":
    main()
