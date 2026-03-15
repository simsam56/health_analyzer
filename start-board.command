#!/bin/bash
# Lance le dashboard Bord (health_analyzer) : backend Python + frontend Next.js
cd "$(dirname "$0")"

cleanup() {
  echo ""
  echo "Arrêt des serveurs…"
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}
trap cleanup INT TERM

# Lancer le backend Python (port 8765)
echo "🚀 Démarrage du backend Python (port 8765)…"
python3 -m api.main &
BACKEND_PID=$!

# Lancer le frontend Next.js (port 3001)
echo "🚀 Démarrage du frontend Next.js (port 3001)…"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Ouvrir le navigateur après un court délai
sleep 4
open http://localhost:3001

echo ""
echo "✅ Board lancé :"
echo "   Frontend → http://localhost:3001"
echo "   Backend  → http://localhost:8765"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter les deux serveurs."

# Attendre les deux processus
wait $BACKEND_PID $FRONTEND_PID
