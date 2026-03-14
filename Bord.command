#!/bin/bash
# ═══════════════════════════════════════════════════════
#  Bord — Double-cliquez pour lancer le tableau de bord
# ═══════════════════════════════════════════════════════

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo -e "\033]0;Bord\007"
clear
echo "╔═══════════════════════════════════╗"
echo "║       Bord — Tableau de bord      ║"
echo "╚═══════════════════════════════════╝"
echo ""

# Arrêter proprement à la fermeture
cleanup() {
    echo ""
    echo "Arrêt de Bord..."
    kill $API_PID 2>/dev/null
    wait $API_PID 2>/dev/null
    echo "Terminé."
}
trap cleanup EXIT INT TERM

# Vérifier Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 non trouvé. Installez-le depuis python.org"
    echo "   Appuyez sur Entrée pour fermer..."
    read -r
    exit 1
fi

# Installer les dépendances si nécessaire
python3 -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "→ Installation des dépendances..."
    pip3 install fastapi uvicorn --quiet
}

# Initialiser la DB
echo "→ Préparation base de données..."
python3 -c "
from pipeline.schema import init_db, migrate_db
conn = init_db('athlete.db')
migrate_db(conn)
conn.close()
print('  ✅ DB prête')
"

# Générer le dashboard HTML
echo "→ Génération du dashboard..."
python3 -c "
from dashboard.generator import generate_html
import os
generate_html(training={}, muscles={}, metrics_history=[], daily_load_rows=[], output_path='reports/dashboard_latest.html')
try: os.remove('reports/dashboard.html')
except: pass
os.symlink('dashboard_latest.html', 'reports/dashboard.html')
print('  ✅ Dashboard généré')
"

# Lancer l'API
echo "→ Démarrage serveur..."
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8765 2>/dev/null &
API_PID=$!
sleep 2

# Vérifier que ça tourne
if curl -s -o /dev/null -w "" http://localhost:8765/ 2>/dev/null; then
    echo ""
    echo "✅ Bord est prêt !"
    echo "   → http://localhost:8765"
    echo ""
    echo "   Laissez cette fenêtre ouverte."
    echo "   Fermez-la pour arrêter Bord."
    echo ""

    # Ouvrir le navigateur
    open http://localhost:8765 2>/dev/null

    # Attendre (le serveur tourne en arrière-plan)
    wait $API_PID
else
    echo "❌ Le serveur n'a pas démarré."
    echo "   Appuyez sur Entrée pour fermer..."
    read -r
fi
