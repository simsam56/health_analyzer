#!/bin/bash
# Bord — Lance l'API Python + le frontend Next.js et ouvre le navigateur

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "Bord - Démarrage"
echo "================"

cleanup() {
    echo ""
    echo "Arrêt de Bord..."
    kill $API_PID $NEXT_PID 2>/dev/null
    wait $API_PID $NEXT_PID 2>/dev/null
    echo "Arrêté."
}
trap cleanup EXIT INT TERM

# Vérifier les dépendances frontend
if [ ! -d "$DIR/frontend/node_modules" ]; then
    echo "-> Installation des dépendances frontend..."
    cd "$DIR/frontend" && npm install
    cd "$DIR"
fi

echo "-> API Python (port 8765)..."
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8765 &
API_PID=$!

sleep 2

echo "-> Frontend Next.js (port 3001)..."
cd "$DIR/frontend"
npm run dev &
NEXT_PID=$!

cd "$DIR"
sleep 2

echo ""
echo "Bord prêt !"
echo "   http://localhost:3001"
echo "   API : http://localhost:8765/docs"
echo ""

open http://localhost:3001 2>/dev/null || true

wait
