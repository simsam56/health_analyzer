#!/usr/bin/env bash
# start_cockpit.sh — lancement Board Cockpit v5
#
# Usage:
#   bash start_cockpit.sh
#   BOARD_PORT=8770 bash start_cockpit.sh
#
# Comportement:
# - run rapide: skip parse local + Garmin 90j (smart-skip actif)
# - ouvre automatiquement le navigateur sur la page Pilotage
# - board tâches + calendrier hebdo + sync Apple Calendar bidirectionnelle
# - garde les logs dans le terminal (Ctrl+C pour arrêter)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DEFAULT_PORT="${BOARD_PORT:-${PERFORMOS_PORT:-8765}}"
PORT="$DEFAULT_PORT"

# Choisir un port libre si le port souhaité est déjà pris
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  for p in 8770 8771 8772 8773 8774 8775; do
    if ! lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
      PORT="$p"
      break
    fi
  done
fi

echo "Démarrage Board sur http://127.0.0.1:${PORT}"
echo "   (Ctrl+C pour arrêter)"
echo ""

# Ouvre le navigateur après 2 secondes (macOS: open, Linux: xdg-open, fallback: python)
(sleep 2
 if command -v open >/dev/null 2>&1; then
   open "http://127.0.0.1:${PORT}"
 elif command -v xdg-open >/dev/null 2>&1; then
   xdg-open "http://127.0.0.1:${PORT}"
 else
   python3 -m webbrowser "http://127.0.0.1:${PORT}" 2>/dev/null
 fi
) &

# Token API:
# - si BOARD_API_TOKEN ou PERFORMOS_API_TOKEN défini: utilisé
# - sinon: main.py génère un token temporaire automatiquement
exec python3 -u main.py --skip-parse --garmin --days 90 --garmin-refresh-tail-days 3 --serve --serve-port "$PORT"
