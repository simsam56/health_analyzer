#!/bin/bash
# Bord — Lance le backend Python + frontend Next.js et ouvre le navigateur
cd "$(dirname "$0")"

# Lancer le backend Python
python3 cockpit_server.py &
BACKEND_PID=$!

# Lancer le frontend Next.js
cd frontend
npm run dev &
FRONTEND_PID=$!

# Ouvrir le navigateur après 3s
sleep 3
open http://localhost:3001

# Attendre les deux processus
wait $BACKEND_PID $FRONTEND_PID
