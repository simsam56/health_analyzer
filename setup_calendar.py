#!/usr/bin/env python3
# PerformOS - Vérification et demande des permissions calendrier

import sys
import threading
from pathlib import Path

def check_calendar_permissions():
    """Vérifie et demande les permissions calendrier Apple."""
    print("🗓️  Vérification des permissions Apple Calendar...")

    try:
        from EventKit import EKEntityTypeEvent, EKEventStore  # type: ignore
    except ImportError:
        print("❌ EventKit non disponible (pyobjc-framework-EventKit manquant)")
        return False

    store = EKEventStore.alloc().init()
    grant = {"ok": False, "err": None}
    done = threading.Event()

    def completion(granted, error):
        grant["ok"] = bool(granted)
        if error is not None:
            grant["err"] = str(error)
        done.set()

    print("🔐 Demande d'accès au calendrier...")
    print("   📋 Une boîte de dialogue va apparaître - cliquez sur 'Autoriser'")

    store.requestAccessToEntityType_completion_(EKEntityTypeEvent, completion)

    # Attendre la réponse de l'utilisateur (timeout plus long pour laisser le temps)
    if done.wait(timeout=30):
        if grant["ok"]:
            print("✅ Permissions accordées !")
            return True
        else:
            print(f"❌ Permissions refusées: {grant['err'] or 'inconnue'}")
            print("   💡 Allez dans : Système > Confidentialité > Calendriers")
            print("   💡 Cherchez PerformOS et activez l'accès")
            return False
    else:
        print("⏰ Timeout - pas de réponse de l'utilisateur")
        return False

def test_calendar_access():
    """Test l'accès au calendrier après permissions."""
    print("\n🧪 Test de l'accès au calendrier...")

    try:
        from EventKit import EKEntityTypeEvent, EKEventStore  # type: ignore
    except ImportError:
        print("❌ EventKit non disponible")
        return False

    store = EKEventStore.alloc().init()

    # Pour les anciennes versions d'EventKit, on teste simplement l'accès
    try:
        calendars = list(store.calendarsForEntityType_(EKEntityTypeEvent) or [])
        print("✅ Accès autorisé")
        print(f"📅 {len(calendars)} calendriers trouvés")

        for cal in calendars[:3]:  # Montrer les 3 premiers
            print(f"   • {cal.title()}")

        return True
    except Exception as e:
        print(f"❌ Accès refusé ou erreur: {e}")
        return False

if __name__ == "__main__":
    print("🚀 PerformOS - Configuration calendrier Apple")
    print("=" * 50)

    # Vérifier les dépendances
    try:
        import EventKit
        import Foundation
        print("✅ Dépendances EventKit/Foundation OK")
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        print("   Installez avec: pip install pyobjc-framework-EventKit")
        sys.exit(1)

    # Demander les permissions si nécessaire
    if not test_calendar_access():
        if check_calendar_permissions():
            test_calendar_access()
        else:
            print("\n💡 Pour corriger:")
            print("   1. Allez dans Préférences Système > Sécurité et confidentialité > Confidentialité")
            print("   2. Cliquez sur 'Calendriers' dans la barre latérale")
            print("   3. Cherchez 'Python' ou relancez l'application")
            sys.exit(1)

    print("\n🎉 Calendrier Apple configuré avec succès !")
