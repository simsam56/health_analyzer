#!/usr/bin/env python3
# PerformOS - Serveur web simplifié

import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from cockpit_server import serve


def check_calendar_permissions():
    """Retourne True si le calendrier est déjà accessible.

    On délègue à la logique de `setup_calendar` qui sait gérer les
    différentes versions d'EventKit sans provoquer d'AttributeError.
    """
    try:
        from setup_calendar import test_calendar_access

        return test_calendar_access()
    except Exception:
        return False


def setup_calendar_if_needed():
    """Configure le calendrier si nécessaire."""
    if not check_calendar_permissions():
        print("🗓️  Configuration du calendrier Apple...")
        try:
            result = subprocess.run(
                [sys.executable, "setup_calendar.py"], capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                print("✅ Calendrier configuré")
                return True
            else:
                print("⚠️  Configuration calendrier échouée:")
                print(result.stderr)
                return False
        except Exception as e:
            print(f"⚠️  Erreur configuration calendrier: {e}")
            return False
    return True


def main():
    print("🚀 PerformOS - Serveur web")
    print("===========================")

    # Vérifications de base
    db_path = Path("athlete.db")
    reports_path = Path("reports")

    if not db_path.exists():
        print("❌ athlete.db non trouvé")
        sys.exit(1)

    if not reports_path.exists():
        print("❌ dossier reports non trouvé")
        sys.exit(1)

    # Créer le lien symbolique dashboard.html si nécessaire
    dashboard_link = reports_path / "dashboard.html"
    if not dashboard_link.exists():
        # Trouver le dashboard le plus récent
        dashboard_files = list(reports_path.glob("dashboard*.html"))
        if dashboard_files:
            latest_dashboard = max(dashboard_files, key=lambda x: x.stat().st_mtime)
            dashboard_link.symlink_to(latest_dashboard.name)
            print(f"✅ Lien dashboard créé: {latest_dashboard.name}")
        else:
            print("⚠️  Aucun fichier dashboard trouvé")

    # Stats rapides
    try:
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        activities_count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        conn.close()
        print(f"📊 Base de données: {activities_count} activités")
    except:
        print("📊 Base de données: OK")

    reports_count = len(list(reports_path.glob("dashboard_*.html")))
    print(f"📁 Dashboard: {reports_count} rapports")

    # Configuration calendrier
    setup_calendar_if_needed()

    # Assurer le lien vers le fichier dashboard
    dashboard_file = reports_path / "dashboard.html"
    if not dashboard_file.exists():
        print("⚠️  Fichier dashboard.html introuvable, exécutez ./update_dashboard_link.sh")
    else:
        print(f"📄 Dashboard file: {dashboard_file}")

    # Déterminer le token API à utiliser. On essaie dans l'ordre :
    # - variable d'environnement PERFORMOS_API_TOKEN
    # - extraction du token existant dans le fichier dashboard.html
    # - valeur de secours statique (performos) afin de rester rétrocompatible.
    import os
    import re

    def _extract_token(path: Path) -> str | None:
        try:
            txt = path.read_text(encoding="utf-8")
            m = re.search(r'const\s+API_TOKEN\s*=\s*"([^"]+)"', txt)
            if m:
                return m.group(1)
        except Exception:
            pass
        return None

    token = os.environ.get("PERFORMOS_API_TOKEN")
    if token:
        token = token.strip()
    if not token:
        token = _extract_token(dashboard_file)
    if not token:
        token = "performos"
    print(f"🔑 API token: {token}")

    # Lancer le serveur
    print("\n🌐 Lancement du serveur...")
    t = threading.Thread(
        target=serve,
        kwargs={
            "dashboard_path": dashboard_file,
            "db_path": db_path,
            "host": "127.0.0.1",
            "port": 8765,
            "api_token": token,
        },
    )
    t.daemon = True
    t.start()

    print("✅ Serveur lancé: http://127.0.0.1:8765")
    print("🖥️  Ouverture dans le navigateur...")

    # Ouvrir dans le navigateur
    time.sleep(1)
    try:
        webbrowser.open("http://127.0.0.1:8765")
    except:
        pass  # Ignore les erreurs de navigateur

    print("🔄 Serveur actif - Ctrl+C pour arrêter")
    try:
        while t.is_alive():
            t.join(timeout=1.0)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du serveur")


if __name__ == "__main__":
    main()
