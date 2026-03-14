#!/bin/bash
# 🚀 PerformOS Desktop Setup - Icône bureau avec calendrier intégré

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎯 Configuration PerformOS - Icône Bureau"
echo "=========================================="
echo ""

# 1. Vérifier les dépendances
echo "📦 Vérification des dépendances..."
python3 -c "
import sys
try:
    import defusedxml, joblib, sqlite3
    from EventKit import EKEventStore
    from Foundation import NSDate
    print('✅ Toutes les dépendances OK')
except ImportError as e:
    print(f'❌ Manquant: {e}')
    print('Installation: pip install defusedxml joblib pyobjc-framework-EventKit')
    exit(1)
"

# 2. Créer l'application macOS
echo ""
echo "📱 Création de l'application macOS..."
./create_app.sh

# 3. Vérifier les permissions calendrier
echo ""
echo "🗓️ Vérification calendrier Apple..."
python3 -c "
from integrations.apple_calendar import diagnose_apple_calendar
diag = diagnose_apple_calendar()
if diag.get('enabled'):
    print('✅ Calendrier Apple connecté')
    print(f'   📅 {diag.get(\"calendars_count\", 0)} calendriers trouvés')
else:
    error = diag.get('error', 'unknown')
    print(f'⚠️ Calendrier: {error}')
    if error == 'calendar_permission_denied':
        echo '🔧 Autorisez dans: Réglages Système > Confidentialité > Calendriers'
"

# 4. Test rapide
echo ""
echo "🧪 Test rapide du système..."
python3 -c "
import sqlite3
from pathlib import Path
db = Path('athlete.db')
if db.exists():
    conn = sqlite3.connect(str(db))
    activities = conn.execute('SELECT COUNT(*) FROM activities').fetchone()[0]
    calendar = conn.execute('SELECT COUNT(*) FROM calendar_events').fetchone()[0]
    conn.close()
    print(f'✅ DB OK: {activities} activités, {calendar} événements calendrier')
else:
    print('⚠️ DB non trouvée - lancez d\\'abord python3 main.py')
"

echo ""
echo "🎉 Configuration terminée!"
echo ""
echo "🚀 Utilisation:"
echo "   • Double-cliquez sur l'icône 'PerformOS.app' sur votre bureau"
echo "   • Interface web s'ouvre automatiquement"
echo "   • Calendrier Apple synchronisé et modifiable"
echo ""
echo "📋 Fonctionnalités calendrier:"
echo "   • Synchronisation automatique (30 jours)"
echo "   • Création d'événements via l'interface"
echo "   • Modification directe des événements"
echo "   • Intégration avec les tâches planner"
echo ""
echo "🔧 Dépannage:"
echo "   • Permissions: Réglages Système > Confidentialité > Calendriers"
echo "   • Logs: ~/Library/Logs/PerformOS/"
echo "   • Reset: rm -rf ~/Desktop/PerformOS.app && ./create_app.sh"
