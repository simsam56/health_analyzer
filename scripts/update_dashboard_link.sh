#!/bin/bash
# Régénérer le lien symbolique vers le dernier dashboard

cd "$(dirname "$0")"

if [ ! -d "reports" ]; then
    echo "❌ Dossier reports non trouvé"
    exit 1
fi

cd reports

# Supprimer l'ancien lien s'il existe
if [ -L "dashboard.html" ]; then
    rm dashboard.html
fi

# Trouver le dashboard le plus récent
LATEST=$(ls -t dashboard*.html 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
    echo "❌ Aucun fichier dashboard trouvé"
    exit 1
fi

# Créer le lien symbolique
ln -s "$LATEST" dashboard.html

echo "✅ Lien dashboard mis à jour: $LATEST"
