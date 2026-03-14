#!/bin/bash
# PerformOS - Script de lancement direct

echo "🚀 PerformOS - Lancement direct"
echo "==============================="

cd "$(dirname "$0")" || exit 1

# Vérifier les fichiers
if [ ! -f "server_simple.py" ]; then
    echo "❌ server_simple.py non trouvé"
    read -p "Appuyez sur Entrée pour quitter..."
    exit 1
fi

if [ ! -f "athlete.db" ]; then
    echo "❌ athlete.db non trouvé"
    read -p "Appuyez sur Entrée pour quitter..."
    exit 1
fi

echo "✅ Fichiers présents"
echo ""

# Lancer le serveur
echo "🌐 Lancement du serveur..."
python3 server_simple.py

echo ""
echo "Serveur arrêté. Appuyez sur Entrée pour quitter..."
read -p ""
