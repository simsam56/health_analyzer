#!/bin/bash
# Bord — Lancement API + Dashboard
# Double-cliquez sur ce fichier pour démarrer

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "╔═══════════════════════════════════╗"
echo "║       Bord — Tableau de bord      ║"
echo "╚═══════════════════════════════════╝"
echo ""

cleanup() {
    echo ""
    echo "Arrêt de Bord..."
    kill $API_PID 2>/dev/null
    wait $API_PID 2>/dev/null
    echo "Arrêté."
}
trap cleanup EXIT INT TERM

# Initialiser la DB si nécessaire
echo "→ Initialisation DB..."
python3 -c "
from pipeline.schema import init_db, migrate_db
conn = init_db('athlete.db')
migrate_db(conn)
conn.close()
print('  DB prête.')
" 2>/dev/null || echo "  DB déjà initialisée."

# Regénérer le dashboard HTML
echo "→ Génération dashboard..."
python3 -c "
from dashboard.generator import generate_html
generate_html(
    training={}, muscles={}, metrics_history=[],
    daily_load_rows=[], output_path='reports/dashboard_latest.html',
)
import os
try: os.remove('reports/dashboard.html')
except: pass
os.symlink('dashboard_latest.html', 'reports/dashboard.html')
print('  Dashboard généré.')
" 2>/dev/null || echo "  Dashboard existant."

# Lancer l'API
echo "→ Démarrage API (port 8765)..."
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8765 &
API_PID=$!

sleep 2

echo ""
echo "✅ Bord prêt !"
echo "   → http://localhost:8765"
echo ""

# Ouvrir le navigateur
open http://localhost:8765 2>/dev/null || xdg-open http://localhost:8765 2>/dev/null || true

wait
