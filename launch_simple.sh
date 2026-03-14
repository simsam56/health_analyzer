#!/bin/bash
# PerformOS Launcher - Version simplifiée

echo "🚀 PerformOS - Lancement simplifié"
echo "=================================="

# Vérifier le répertoire
if [ ! -f "main.py" ]; then
    echo "❌ main.py non trouvé dans $(pwd)"
    exit 1
fi

echo "📍 Répertoire: $(pwd)"
echo "🐍 Python: $(python3 --version 2>&1)"

# Vérifier les dépendances de base
echo "📦 Vérification dépendances..."
python3 -c "
try:
    import sqlite3, sys
    print('✅ Base OK')
except ImportError as e:
    print(f'❌ Import: {e}')
    exit(1)
"

# Lancer avec options simples
echo "🌐 Lancement serveur..."
python3 main.py --serve --calendar-days 7 --serve-port 8765

echo "✅ Terminé"
