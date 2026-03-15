#!/bin/bash
# Bord — Lancement API + frontend
#
# Ports configurables via variables d'environnement :
#   BORD_API_PORT      (défaut: 8765)  — port du backend FastAPI
#   BORD_FRONTEND_PORT (défaut: 3000)  — port du frontend Next.js
#
# Exemples :
#   bash start_cockpit_v2.sh
#   BORD_FRONTEND_PORT=3001 BORD_API_PORT=8766 bash start_cockpit_v2.sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

API_PORT="${BORD_API_PORT:-8765}"
FRONTEND_PORT="${BORD_FRONTEND_PORT:-3000}"

echo "Bord - Demarrage"
echo "================"
echo "   API port:      $API_PORT"
echo "   Frontend port:  $FRONTEND_PORT"

# Vérifier que les ports ne sont pas déjà utilisés (sans tuer les processus !)
for port in "$API_PORT" "$FRONTEND_PORT"; do
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        pid=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null | head -1)
        cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "inconnu")
        echo "ERREUR: Le port $port est deja utilise par PID $pid ($cmd)"
        echo "   Choisissez un autre port ou arretez le processus manuellement."
        exit 1
    fi
done

cleanup() {
    echo ""
    echo "Arret de Bord..."
    kill $NEXT_PID $API_PID 2>/dev/null
    wait $NEXT_PID $API_PID 2>/dev/null
    echo "Arrete."
}
trap cleanup EXIT INT TERM

echo "-> API Python (port $API_PORT)..."
BORD_PORT="$API_PORT" BORD_FRONTEND_PORT="$FRONTEND_PORT" \
    python3 -m uvicorn api.main:app --host 127.0.0.1 --port "$API_PORT" &
API_PID=$!

sleep 2

echo "-> Frontend Next.js (port $FRONTEND_PORT)..."
cd "$DIR/frontend"

if [ -d ".next" ]; then
    BORD_API_PORT="$API_PORT" ./node_modules/.bin/next start -p "$FRONTEND_PORT" &
else
    echo "Build non trouve, lancement en mode dev..."
    BORD_API_PORT="$API_PORT" ./node_modules/.bin/next dev -p "$FRONTEND_PORT" &
fi
NEXT_PID=$!

cd "$DIR"
sleep 2

echo ""
echo "Bord pret !"
echo "   http://localhost:$FRONTEND_PORT"
echo "   API : http://localhost:$API_PORT/docs"
echo ""

open "http://localhost:$FRONTEND_PORT" 2>/dev/null || true

wait
