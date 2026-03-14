#!/bin/bash
# Script de lancement PerformOS v3

cd "$(dirname "$0")"

echo "🚀 Lancement PerformOS v3..."
echo "📅 Date: $(date)"
echo "📍 Dossier: $(pwd)"
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non trouvé"
    exit 1
fi

echo "✅ Python3 trouvé: $(python3 --version)"

# Vérifier dépendances critiques
echo "🔍 Vérification dépendances..."
python3 -c "
try:
    import sqlite3, json, pathlib
    from defusedxml import ElementTree
    import joblib
    print('✅ Dépendances de base OK')
except ImportError as e:
    print(f'❌ Dépendance manquante: {e}')
    exit(1)
"

# Lancer l'application
echo ""
echo "🎯 Lancement de l'application..."
python3 main.py "$@"
