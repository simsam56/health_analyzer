#!/bin/bash
# Board - Script de lancement direct

echo "Board - Lancement"
echo "================="

cd "$(dirname "$0")" || exit 1

# Vérifier les fichiers
if [ ! -f "board.sh" ]; then
    echo "board.sh non trouvé"
    read -p "Appuyez sur Entrée pour quitter..."
    exit 1
fi

# Lancer Board (FastAPI + Next.js)
exec bash board.sh
