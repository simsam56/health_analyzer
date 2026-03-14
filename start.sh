#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Bord — Lancement en un clic
# Démarre le backend Python + le frontend Next.js puis ouvre le navigateur.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DB="$ROOT/athlete.db"
DASHBOARD="$ROOT/reports/dashboard.html"
BACKEND_PORT=8765
FRONTEND_PORT=3000
URL="http://localhost:$FRONTEND_PORT/cockpit"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${CYAN}▸${NC} $1"; }
ok()   { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

cleanup() {
    log "Arrêt des serveurs..."
    [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null
    [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null
    wait 2>/dev/null
    ok "Tout est arrêté."
}
trap cleanup EXIT INT TERM

echo -e "${BOLD}"
echo "  ╔══════════════════════════════╗"
echo "  ║     B o r d  —  Cockpit      ║"
echo "  ╚══════════════════════════════╝"
echo -e "${NC}"

# ── 1. Vérifier la DB ────────────────────────────────────────
if [ ! -f "$DB" ]; then
    log "Base de données absente, création de la DB démo..."
    python3 "$ROOT/scripts/seed_demo.py" || fail "Impossible de créer la DB"
fi
ok "Base de données : $DB"

# ── 2. Vérifier les deps frontend ────────────────────────────
if [ ! -d "$ROOT/frontend/node_modules" ]; then
    log "Installation des dépendances frontend..."
    (cd "$ROOT/frontend" && npm install --silent) || fail "npm install a échoué"
fi
ok "Dépendances frontend OK"

# ── 3. Tuer les anciens processus sur les ports ──────────────
for port in $BACKEND_PORT $FRONTEND_PORT; do
    pid=$(lsof -ti ":$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        log "Port $port occupé (PID $pid), arrêt..."
        kill "$pid" 2>/dev/null || true
        sleep 1
    fi
done

# ── 4. Démarrer le backend Python ────────────────────────────
log "Démarrage du backend (port $BACKEND_PORT)..."
python3 "$ROOT/cockpit_server.py" \
    --dashboard "$DASHBOARD" \
    --db "$DB" \
    --port "$BACKEND_PORT" &
BACKEND_PID=$!

# Attendre que le backend soit prêt
for i in $(seq 1 15); do
    if curl -sf "http://127.0.0.1:$BACKEND_PORT/api/artifact" > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done
curl -sf "http://127.0.0.1:$BACKEND_PORT/api/artifact" > /dev/null 2>&1 \
    || fail "Le backend ne répond pas sur le port $BACKEND_PORT"
ok "Backend prêt (PID $BACKEND_PID)"

# ── 5. Démarrer le frontend Next.js ──────────────────────────
log "Démarrage du frontend (port $FRONTEND_PORT)..."
(cd "$ROOT/frontend" && npx next dev --port "$FRONTEND_PORT" > /dev/null 2>&1) &
FRONTEND_PID=$!

# Attendre que le frontend soit prêt
for i in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:$FRONTEND_PORT" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done
curl -sf "http://127.0.0.1:$FRONTEND_PORT" > /dev/null 2>&1 \
    || fail "Le frontend ne répond pas sur le port $FRONTEND_PORT"
ok "Frontend prêt (PID $FRONTEND_PID)"

# ── 6. Ouvrir le navigateur ──────────────────────────────────
log "Ouverture du navigateur..."
if command -v open &> /dev/null; then
    open "$URL"                          # macOS
elif command -v xdg-open &> /dev/null; then
    xdg-open "$URL"                      # Linux
elif command -v start &> /dev/null; then
    start "$URL"                         # Windows/Git Bash
else
    log "Ouvre manuellement : $URL"
fi

echo ""
echo -e "${GREEN}${BOLD}  ✓ Bord est prêt !${NC}"
echo -e "  ${CYAN}→${NC} $URL"
echo ""
echo -e "  Appuie sur ${BOLD}Ctrl+C${NC} pour tout arrêter."
echo ""

# Rester en vie jusqu'à Ctrl+C
wait
