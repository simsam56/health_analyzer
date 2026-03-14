#!/bin/bash
# 🔄 RESET COMPLET PerformOS - MacBook Pro M5

set -e

echo "🔄 Reset complet PerformOS"
echo "=========================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Nettoyer les anciennes installations
echo "🧹 Nettoyage..."
rm -rf ~/Desktop/PerformOS*.app
rm -f *.pyc
rm -rf __pycache__
rm -rf .pytest_cache

# 2. Vérifier Python
echo "🐍 Vérification Python..."
python3 --version
python3 -c "import sys; print(f'Version: {sys.version}')"

# 3. Installer/Mettre à jour les dépendances
echo "📦 Installation dépendances..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# 4. Vérifier les imports critiques
echo "🔍 Test imports..."
python3 -c "
try:
    import sqlite3, defusedxml, joblib
    print('✅ Imports de base OK')
except ImportError as e:
    print(f'❌ Import manquant: {e}')
    exit(1)
"

# 5. Tester EventKit (optionnel)
echo "🗓️ Test calendrier..."
python3 -c "
try:
    from EventKit import EKEventStore
    print('✅ EventKit disponible')
except ImportError:
    print('⚠️ EventKit non disponible (calendrier limité)')
"

# 6. Tester main.py
echo "🚀 Test main.py..."
python3 -c "
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('main', 'main.py')
    main_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_module)
    print('✅ main.py OK')
except Exception as e:
    print(f'❌ main.py erreur: {e}')
    exit(1)
"

# 7. Créer l'application simplifiée
echo "📱 Création application..."
./create_simple_app.sh

# 8. Test final
echo "🧪 Test final..."
if python3 test_launch.py; then
    echo ""
    echo "🎉 RESET RÉUSSI !"
    echo ""
    echo "🚀 Utilisation:"
    echo "   • Double-cliquez sur PerformOS_Simple.app (bureau)"
    echo "   • Ou lancez: python3 main.py --serve"
    echo ""
    echo "📖 Guide: TROUBLESHOOTING.md"
else
    echo ""
    echo "❌ Test échoué. Voir TROUBLESHOOTING.md"
    exit 1
fi
