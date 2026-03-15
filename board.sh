#!/usr/bin/env bash
# board.sh — Lancement rapide de Bord (API + Frontend)
#
# Ports configurables :
#   BORD_API_PORT      (défaut: 8765)
#   BORD_FRONTEND_PORT (défaut: 3000)
#
# Pour éviter les conflits avec un autre projet sur le port 3000 :
#   BORD_FRONTEND_PORT=3001 bash board.sh
#
# Pour tout personnaliser :
#   BORD_FRONTEND_PORT=3001 BORD_API_PORT=8766 bash board.sh

exec "$(dirname "$0")/start_cockpit_v2.sh" "$@"
