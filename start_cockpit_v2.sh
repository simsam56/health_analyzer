#!/bin/bash
# PerformOS Cockpit v2 — Lancement Python API + Next.js frontend

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "PerformOS Cockpit v2"
echo "========================"

# Cleanup propre a la fermeture
cleanup() {
    echo ""
    echo "Arret du cockpit..."
    kill $NEXT_PID $API_PID 2>/dev/null
    wait $NEXT_PID $API_PID 2>/dev/null
    echo "Arrete."
}
trap cleanup EXIT INT TERM

# 1. Lancer l'API Python (FastAPI)
echo "-> Demarrage API Python (port 8765)..."
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8765 &
API_PID=$!

sleep 2

# 2. Lancer le frontend Next.js
echo "-> Demarrage frontend Next.js (port 3000)..."
cd "$DIR/frontend"

# Utiliser le build production si disponible, sinon dev
if [ -d ".next" ]; then
    ./node_modules/.bin/next start -p 3000 &
else
    echo "Build non trouve, lancement en mode dev..."
    ./node_modules/.bin/next dev -p 3000 &
fi
NEXT_PID=$!

cd "$DIR"

sleep 2

echo ""
echo "Cockpit pret !"
echo "   Frontend : http://localhost:3000"
echo "   API docs : http://localhost:8765/docs"
echo "   Ancien UI: http://localhost:8765"
echo ""
echo "   Appuyez sur Ctrl+C pour arreter."

# Ouvrir le navigateur
open http://localhost:3000 2>/dev/null || true

wait
