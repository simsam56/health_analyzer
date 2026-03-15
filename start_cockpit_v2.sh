#!/bin/bash
# Bord — Lancement API + frontend

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "Bord - Demarrage"
echo "================"

cleanup() {
    echo ""
    echo "Arret de Bord..."
    kill $NEXT_PID $API_PID 2>/dev/null
    wait $NEXT_PID $API_PID 2>/dev/null
    echo "Arrete."
}
trap cleanup EXIT INT TERM

echo "-> API Python (port 8765)..."
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8765 &
API_PID=$!

sleep 2

echo "-> Frontend Next.js (port 3001)..."
cd "$DIR/frontend"

if [ -d ".next" ]; then
    ./node_modules/.bin/next start -p 3001 &
else
    echo "Build non trouve, lancement en mode dev..."
    ./node_modules/.bin/next dev -p 3001 &
fi
NEXT_PID=$!

cd "$DIR"
sleep 2

echo ""
echo "Bord pret !"
echo "   http://localhost:3001"
echo "   API : http://localhost:8765/docs"
echo ""

open http://localhost:3001 2>/dev/null || true

wait
