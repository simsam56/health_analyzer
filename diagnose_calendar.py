#!/usr/bin/env python3
"""
Diagnostic Apple Calendar pour PerformOS v3
"""

import sqlite3
import sys
from pathlib import Path


def diagnose_calendar():
    print("🗓️  Diagnostic Apple Calendar")
    print("=" * 50)

    # 1. Vérifier la plateforme
    print(f"📍 Plateforme: {sys.platform}")
    if sys.platform != "darwin":
        print("❌ Apple Calendar nécessite macOS")
        return

    # 2. Vérifier les dépendances
    try:
        from EventKit import EKEventStore

        print("✅ EventKit disponible")
    except ImportError:
        print("❌ EventKit non installé")
        print("   → Installez: pip install pyobjc-framework-EventKit")
        return

    try:
        from Foundation import NSDate

        print("✅ Foundation disponible")
    except ImportError:
        print("❌ Foundation non installé")
        return

    # 3. Tester les permissions
    print("\n🔐 Test des permissions...")
    try:
        from integrations.apple_calendar import diagnose_apple_calendar

        diag = diagnose_apple_calendar()
        print(f"EventKit: {diag.get('eventkit', 'unknown')}")
        print(f"Permission: {diag.get('permission', 'unknown')}")
        print(f"Calendriers: {diag.get('calendars_count', 0)}")

        if not diag.get("enabled", False):
            error = diag.get("error", "unknown")
            print(f"❌ Problème détecté: {error}")
            if error == "calendar_permission_denied":
                print("\n🔧 Solution:")
                print("1. Ouvrez les Réglages Système")
                print("2. Allez dans 'Confidentialité et sécurité' > 'Calendriers'")
                print("3. Cochez Python/EventKit")
                print("4. Relancez l'application")
        else:
            print("✅ Permissions accordées")

    except Exception as e:
        print(f"❌ Erreur diagnostic: {e}")

    # 4. Vérifier la base de données
    print("\n💾 État de la base de données...")
    db_path = Path("athlete.db")
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            count = conn.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
            print(f"📅 Événements synchronisés: {count}")

            if count > 0:
                recent = conn.execute("""
                    SELECT title, start_at, calendar_name
                    FROM calendar_events
                    ORDER BY start_at
                    LIMIT 5
                """).fetchall()

                print("📅 Événements récents:")
                for event in recent:
                    start_date = event[1][:10] if event[1] else "?"
                    print(f"  • {event[0]} - {start_date} ({event[2]})")

            conn.close()
        except Exception as e:
            print(f"❌ Erreur DB: {e}")
    else:
        print("❌ Base de données non trouvée")

    print("\n" + "=" * 50)
    print("💡 Pour tester: python3 main.py --calendar-days 7")


if __name__ == "__main__":
    diagnose_calendar()
