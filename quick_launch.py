#!/usr/bin/env python3
"""
Bord Quick Launcher - Icône bureau avec calendrier intégré
"""

import subprocess
import sys
import time
from pathlib import Path

# Configuration
ROOT = Path(__file__).parent
CALENDAR_DAYS = 30  # Plus de jours pour le calendrier


def check_dependencies():
    """Vérifier les dépendances critiques"""
    missing = []
    try:
        import sqlite3

        import defusedxml
        import joblib
    except ImportError as e:
        missing.append(str(e))

    if missing:
        print(f"❌ Dépendances manquantes: {', '.join(missing)}")
        print("Installez avec: pip install -r requirements.txt")
        return False
    return True


def launch_bord():
    """Lancer Bord avec calendrier intégré"""
    print("🚀 Bord - Lancement rapide avec calendrier")
    print("=" * 60)

    if not check_dependencies():
        return

    # Commande optimisée pour calendrier
    cmd = [
        sys.executable,
        str(ROOT / "main.py"),
        "--serve",  # Interface web
        "--calendar-days",
        str(CALENDAR_DAYS),  # Plus de jours calendrier
        "--weeks-muscle",
        "8",  # Analyse musculaire étendue
        "--serve-port",
        "8765",  # Port fixe
    ]

    print(f"📅 Calendrier: {CALENDAR_DAYS} jours")
    print("🌐 Interface: http://127.0.0.1:8765")
    print("💪 Analyse musculaire: 8 semaines")
    print()

    try:
        # Lancer en arrière-plan
        process = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Attendre que le serveur démarre
        time.sleep(3)

        # Ouvrir le navigateur automatiquement
        try:
            subprocess.run(["open", "http://127.0.0.1:8765"], check=False)
        except:
            pass

        print("✅ Bord lancé!")
        print("📱 Interface ouverte dans le navigateur")
        print("🗓️ Calendrier Apple synchronisé")
        print()
        print("💡 Fonctionnalités disponibles:")
        print("   • Planning hebdomadaire")
        print("   • Synchronisation calendrier Apple")
        print("   • Création/modification d'événements")
        print("   • Analyse santé et performance")
        print()
        print("🔄 Le serveur tourne en arrière-plan...")
        print("   Appuyez Ctrl+C pour arrêter")

        # Garder le processus en vie
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Arrêt du serveur...")
            process.terminate()
            process.wait()

    except Exception as e:
        print(f"❌ Erreur lancement: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(launch_bord())
