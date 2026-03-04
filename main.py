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
import sqlite3
import sys
import shutil
import importlib.util
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ─── Defaults ────────────────────────────────────────────────────
DB_PATH     = ROOT / "athlete.db"
AH_XML      = ROOT / "export.xml"
STRAVA_DIR  = ROOT / "export_strava"
REPORTS_DIR = ROOT / "reports"


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


def backup_db(db_path: Path) -> None:
    """Sauvegarde la DB avant un reset."""
    if db_path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = db_path.with_suffix(f".bak_{ts}.db")
        shutil.copy2(db_path, bak)
        print(f"  💾 Backup DB : {bak}")


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
    parser.add_argument("--skip-parse", action="store_true",
                        help="Sauter Apple Health + Strava (utiliser DB existante)")
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

    garmin_connected = False
    calendar_sync = {"enabled": False, "error": "disabled", "events_synced": 0}

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

    if not args.skip_parse:
        # ─── 2. Apple Health ─────────────────────────────────────
        if ah_xml.exists():
            print("🍎 Pipeline Apple Health…")
            from pipeline.parse_apple_health import run as run_ah
            result_ah = run_ah(xml_path=ah_xml, db_path=db_path)
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
            print("⚠️  Apple Health XML non trouvé — étape ignorée\n")

        # ─── 3. Strava FIT ───────────────────────────────────────
        if strava_dir.exists():
            print("🏃 Pipeline Strava FIT…")
            from pipeline.parse_strava_fit import run as run_strava
            run_strava(strava_dir=strava_dir, db_path=db_path)
            print()
        else:
            print("⚠️  Dossier Strava non trouvé — étape ignorée\n")

    else:
        print("⏭️  Parsing Apple Health + Strava ignoré (--skip-parse)\n")

    # ─── 4. Garmin Connect (optionnel) ───────────────────────────
    if args.garmin:
        print(f"⌚ Pipeline Garmin Connect ({args.days} derniers jours)…")
        from pipeline.parse_garmin_connect import run as run_garmin
        from dotenv import load_dotenv
        import os
        load_dotenv(ROOT / ".env")
        result_gc = run_garmin(
            db_path=db_path,
            days=args.days,
            email=os.environ.get("GARMIN_EMAIL"),
            password=os.environ.get("GARMIN_PASSWORD"),
        )
        if "error" not in result_gc:
            garmin_connected = True
            print(f"   Activités : {result_gc.get('activities_inserted',0)} nouvelles")
            print(f"   Métriques : {result_gc.get('metrics_inserted',0)} nouvelles")
        else:
            print(f"   ⚠️  {result_gc.get('error','erreur inconnue')}")
        print()
    else:
        print("ℹ️  Garmin Connect : non activé (utilisez --garmin pour synchroniser)\n")

    # ─── 4.5 Dédup activités (optionnel) ────────────────────────
    if not args.no_dedup:
        removed = deduplicate_activities(db_path)
        print(f"🧹 Dédup activités : {removed} doublons supprimés")
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

    conn.close()

    training["garmin_connected"] = garmin_connected or has_garmin_data
    training["calendar_sync"] = calendar_sync
    training["agenda_events"] = agenda_events
    training["data_quality"] = data_quality
    training["pilotage"] = {
        "events": planner_events,
        "week_start": str(week_start),
        "summary": planner_summary,
        "series": planner_series,
    }

    # ─── 8. Dashboard HTML ───────────────────────────────────────
    print("🎨 Génération dashboard HTML…")
    from dashboard.generator import generate_html
    generate_html(
        training=training,
        muscles=muscles,
        metrics_history=metrics_history,
        daily_load_rows=daily_load_rows,
        output_path=output_path,
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
