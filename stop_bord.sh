#!/usr/bin/env bash
# stop_bord.sh — stop local Bord servers

set -euo pipefail

PORTS=${BORD_PORTS:-"8765 8766 8767 8768 8769 8770 8771 8772 8773 8774 8775"}
stopped=0

for port in $PORTS; do
  pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)
  for pid in $pids; do
    cmd=$(ps -p "$pid" -o command= 2>/dev/null || true)
    if [[ "$cmd" == *"uvicorn"* ]] || [[ "$cmd" == *"api.main"* ]] || [[ "$cmd" == *"main.py"* ]]; then
      kill "$pid" 2>/dev/null || true
      echo "🛑 arrêt PID $pid (port $port)"
      stopped=$((stopped + 1))
    fi
  done
done

if [[ "$stopped" -eq 0 ]]; then
  echo "ℹ️ Aucun serveur Bord à arrêter."
else
  echo "✅ $stopped serveur(s) Bord arrêté(s)."
fi
