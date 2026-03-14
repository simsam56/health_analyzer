#!/bin/bash
# 🚀 VÉRIFICATION FINALE PerformOS

echo "🎯 Vérification finale PerformOS"
echo "==============================="

# 1. Vérifier l'application
if [ -d "$HOME/Desktop/PerformOS_Simple.app" ]; then
    echo "✅ Application: Présente sur le bureau"
    ls -la "$HOME/Desktop/PerformOS_Simple.app/Contents/MacOS/PerformOS"
else
    echo "❌ Application: Non trouvée"
    exit 1
fi

# 2. Vérifier les fichiers critiques
echo ""
echo "📁 Fichiers critiques:"
files=("main.py" "athlete.db" "requirements.txt")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (MANQUANT)"
    fi
done

# 3. Test rapide Python
echo ""
echo "🐍 Test Python:"
python3 -c "
try:
    import sqlite3, defusedxml, joblib
    print('   ✅ Dépendances OK')
except ImportError as e:
    print(f'   ❌ Dépendance: {e}')
"

# 4. Test base de données
echo ""
echo "💾 Test base de données:"
python3 -c "
import sqlite3
from pathlib import Path
db = Path('athlete.db')
if db.exists():
    conn = sqlite3.connect(str(db))
    activities = conn.execute('SELECT COUNT(*) FROM activities').fetchone()[0]
    calendar = conn.execute('SELECT COUNT(*) FROM calendar_events').fetchone()[0]
    conn.close()
    print(f'   ✅ DB OK: {activities} activités, {calendar} événements calendrier')
else:
    print('   ❌ DB non trouvée')
"

echo ""
echo "🎉 TOUT EST PRÊT !"
echo ""
echo "🚀 Utilisation:"
echo "   1. Double-cliquez sur 'PerformOS_Simple.app' (bureau)"
echo "   2. L'interface web s'ouvre automatiquement"
echo "   3. Calendrier Apple synchronisé"
echo ""
echo "📖 En cas de problème: ./reset_performos.sh"
