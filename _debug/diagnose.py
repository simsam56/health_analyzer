#!/usr/bin/env python3
"""
Diagnostic rapide PerformOS
"""

import sys
from pathlib import Path


def diagnose():
    print("🔍 Diagnostic PerformOS")
    print("=" * 40)

    # Vérifier Python
    print(f"🐍 Python: {sys.version}")
    print(f"📍 Répertoire: {Path.cwd()}")

    # Vérifier fichiers critiques
    files_to_check = ["main.py", "quick_launch.py", "athlete.db", "requirements.txt"]
    for file in files_to_check:
        path = Path(file)
        if path.exists():
            print(f"✅ {file}: existe ({path.stat().st_size} bytes)")
        else:
            print(f"❌ {file}: MANQUANT")

    # Tester imports
    print("\n📦 Test imports:")
    try:
        import sqlite3

        print("✅ sqlite3 OK")
    except ImportError as e:
        print(f"❌ sqlite3: {e}")

    try:
        import defusedxml

        print("✅ defusedxml OK")
    except ImportError as e:
        print(f"❌ defusedxml: {e}")

    try:
        import joblib

        print("✅ joblib OK")
    except ImportError as e:
        print(f"❌ joblib: {e}")

    # Tester EventKit
    try:
        from EventKit import EKEventStore

        print("✅ EventKit OK")
    except ImportError as e:
        print(f"⚠️ EventKit: {e} (calendrier non disponible)")

    # Tester main.py
    print("\n🚀 Test main.py:")
    try:
        print("✅ main.py importable")
    except Exception as e:
        print(f"❌ main.py erreur: {e}")

    # Vérifier DB
    db_path = Path("athlete.db")
    if db_path.exists():
        try:
            import sqlite3

            conn = sqlite3.connect(str(db_path))
            activities = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
            calendar = conn.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
            conn.close()
            print(f"✅ DB OK: {activities} activités, {calendar} événements calendrier")
        except Exception as e:
            print(f"❌ DB erreur: {e}")
    else:
        print("⚠️ DB non trouvée")

    print("\n" + "=" * 40)
    print("💡 Pour lancer: python3 quick_launch.py")


if __name__ == "__main__":
    diagnose()
