#!/usr/bin/env bash
# start_bord.sh — lancement Bord (tableau de bord personnel)
#
# Usage:
#   bash start_bord.sh
#   BORD_PORT=8770 bash start_bord.sh
#
# Comportement:
# - run rapide: skip parse local + Garmin 90j (smart-skip actif)
# - ouvre automatiquement le navigateur sur le dashboard
# - board tâches + calendrier hebdo + sync Apple Calendar bidirectionnelle
# - garde les logs dans le terminal (Ctrl+C pour arrêter)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DEFAULT_PORT="${BORD_PORT:-8765}"
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

echo "🚀 Démarrage Bord sur http://127.0.0.1:${PORT}"
echo "   (Ctrl+C pour arrêter)"
echo ""

# Ouvre le navigateur après 2 secondes
(sleep 2; open "http://127.0.0.1:${PORT}" >/dev/null 2>&1 || true) &

# Token API:
# - si BORD_API_TOKEN défini: utilisé
# - sinon: main.py génère un token temporaire automatiquement
exec python3 -u main.py --skip-parse --garmin --days 90 --garmin-refresh-tail-days 3 --serve --serve-port "$PORT"
