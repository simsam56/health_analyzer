#!/usr/bin/env python3
"""
Test de lancement minimal PerformOS
"""

import subprocess
import sys
import time


def test_launch():
    print("🧪 Test de lancement minimal PerformOS")
    print("=" * 50)

    # Test 1: Vérifier Python
    print(f"🐍 Python: {sys.version}")

    # Test 2: Vérifier imports de base
    try:
        import sqlite3

        print("✅ sqlite3 OK")
    except ImportError as e:
        print(f"❌ sqlite3: {e}")
        return False

    # Test 3: Vérifier main.py
    try:
        # Essayer d'importer main.py
        import importlib.util

        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        print("✅ main.py importable")
    except Exception as e:
        print(f"❌ main.py: {e}")
        return False

    # Test 4: Lancement rapide avec timeout
    print("\n🚀 Test lancement serveur (10 secondes)...")
    try:
        cmd = [sys.executable, "main.py", "--serve", "--serve-port", "8766", "--calendar-days", "1"]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd="."
        )

        # Attendre 10 secondes
        time.sleep(10)

        if proc.poll() is None:
            print("✅ Serveur démarré et fonctionne")
            proc.terminate()
            proc.wait()
            print("✅ Arrêt propre")
            return True
        else:
            stdout, _ = proc.communicate()
            print("❌ Serveur arrêté prématurément")
            print("Sortie:", stdout[-500:])  # Derniers 500 caractères
            return False

    except Exception as e:
        print(f"❌ Erreur lancement: {e}")
        return False


if __name__ == "__main__":
    success = test_launch()
    if success:
        print("\n🎉 Test réussi! L'application peut démarrer.")
        print("💡 Créez l'icône bureau avec: ./create_simple_app.sh")
    else:
        print("\n❌ Test échoué. Vérifiez les erreurs ci-dessus.")
    sys.exit(0 if success else 1)
