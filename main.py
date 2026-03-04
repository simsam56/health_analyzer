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
from datetime import date, datetime
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
        fit_count = len(list(strava_dir.glob("activities/*.fit.gz")))
        print(f"  ✅ Strava FIT         : {strava_dir} ({fit_count} fichiers FIT)")
    else:
        print(f"  ⚠️  Strava FIT         : {strava_dir} — MANQUANT")
        print("     → Exporter depuis strava.com > Paramètres > Mes données")
    print()


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
                        help="Sauter le parsing (utiliser DB existante)")
    parser.add_argument("--reset",      action="store_true",
                        help="Réinitialiser la DB (backup automatique)")
    parser.add_argument("--weeks-muscle", type=int, default=4,
                        help="Fenêtre analyse musculaire (semaines)")
    parser.add_argument("--audit",      action="store_true",
                        help="Afficher rapport d'audit des données")
    args = parser.parse_args()

    banner()

    db_path    = Path(args.db)
    ah_xml     = Path(args.export)
    strava_dir = Path(args.strava)
    output_path = Path(args.output) if args.output else \
                  REPORTS_DIR / f"dashboard_{date.today()}.html"

    check_sources(ah_xml, strava_dir)

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

    if not args.skip_parse:
        # ─── 2. Apple Health ─────────────────────────────────────
        if ah_xml.exists():
            print("🍎 Pipeline Apple Health…")
            from pipeline.parse_apple_health import run as run_ah
            result_ah = run_ah(xml_path=ah_xml, db_path=db_path)
            print(f"   Workouts : {result_ah.get('workouts_inserted',0)} insérés")
            print(f"   Métriques : {result_ah.get('metrics_inserted',0)} lignes ({result_ah.get('days_covered',0)} jours)")
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

        # ─── 4. Garmin Connect (optionnel) ───────────────────────
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

    # ─── 5. Audit optionnel ──────────────────────────────────────
    if args.audit:
        _print_audit(db_path)

    # ─── 6. Analytics ────────────────────────────────────────────
    print("📈 Calcul charge d'entraînement…")
    from analytics.training_load import run as run_training
    training = run_training(db_path=db_path, verbose=True)
    training["garmin_connected"] = garmin_connected
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
    conn.close()

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
        print("        (incluant votre seance du 02/03/2026)")
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
                "health_metrics", "daily_load"]:
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
