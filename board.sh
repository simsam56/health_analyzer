#!/usr/bin/env bash
# board.sh — Board · Lanceur unifié (FastAPI + Next.js)
#
# Usage:
#   bash board.sh            # Lance backend + frontend + ouvre navigateur
#   BOARD_PORT=8770 bash board.sh   # Port custom backend
#
# Double-cliquez sur Board.app ou lancez depuis le terminal.
# Ctrl+C pour tout arrêter proprement.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Configuration ─────────────────────────────────────────────
API_PORT="${BOARD_PORT:-8765}"
FRONT_PORT="${BOARD_FRONT_PORT:-3000}"
PIDS=()

# ── Nettoyage à la sortie ─────────────────────────────────────
cleanup() {
    echo ""
    echo "Arrêt de Board..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null && wait "$pid" 2>/dev/null || true
    done
    echo "Board arrêté."
}
trap cleanup EXIT INT TERM

# ── Bannière ──────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Board · Tableau de bord santé & performance            ║"
echo "║  $(date '+%d %b %Y · %H:%M')                                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Vérification des dépendances ─────────────────────────────
echo "[SETUP] Vérification des dépendances..."

# Python
if ! python3 -c "import fastapi, uvicorn, pandas, defusedxml, joblib" 2>/dev/null; then
    echo "[SETUP] Installation des dépendances Python..."
    pip install -r requirements.txt 2>/dev/null || {
        # Sur macOS, pyobjc s'installe ; sur Linux on l'exclut
        grep -v pyobjc requirements.txt | grep -v fitparse > /tmp/board_req.txt
        pip install -r /tmp/board_req.txt
    }
    pip install fastapi uvicorn 2>/dev/null || true
fi

# Node.js / Frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "[SETUP] Installation des dépendances frontend..."
    (cd frontend && npm install)
fi

# DB
if ! python3 -c "
import sqlite3
c = sqlite3.connect('athlete.db')
tables = [r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
c.close()
assert len(tables) >= 5, 'DB vide'
" 2>/dev/null; then
    echo "[SETUP] Initialisation de la base de données..."
    python3 -c "from pipeline.schema import init_db, get_connection, migrate_db; conn = init_db('athlete.db'); conn.close(); conn = get_connection('athlete.db'); migrate_db(conn); conn.close()"
fi

echo "[SETUP] OK"
echo ""

# ── Port libre ────────────────────────────────────────────────
is_port_busy() {
    lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

if is_port_busy "$API_PORT"; then
    for p in 8770 8771 8772 8773 8774 8775; do
        if ! is_port_busy "$p"; then
            API_PORT="$p"
            break
        fi
    done
fi

# ── Lancement backend FastAPI ─────────────────────────────────
echo "[API]   Démarrage sur http://127.0.0.1:${API_PORT}"

BORD_DB="$SCRIPT_DIR/athlete.db" \
BORD_DASHBOARD="$SCRIPT_DIR/reports/dashboard.html" \
python3 -m uvicorn api.main:app \
    --host 127.0.0.1 \
    --port "$API_PORT" \
    --log-level info 2>&1 | sed 's/^/[API]   /' &
PIDS+=($!)

# Attendre que l'API soit prête
echo "[API]   Attente du démarrage..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:${API_PORT}/docs" >/dev/null 2>&1; then
        echo "[API]   Prêt"
        break
    fi
    sleep 1
done

# ── Lancement frontend Next.js ────────────────────────────────
echo "[FRONT] Démarrage sur http://localhost:${FRONT_PORT}"

(cd frontend && PORT="$FRONT_PORT" npm run dev 2>&1 | sed 's/^/[FRONT] /') &
PIDS+=($!)

# Attendre que le frontend soit prêt
echo "[FRONT] Attente du démarrage..."
for i in $(seq 1 30); do
    if curl -s "http://localhost:${FRONT_PORT}" >/dev/null 2>&1; then
        echo "[FRONT] Prêt"
        break
    fi
    sleep 1
done

# ── Ouvrir le navigateur ──────────────────────────────────────
echo ""
echo "Board est prêt !"
echo "  Frontend : http://localhost:${FRONT_PORT}"
echo "  API      : http://127.0.0.1:${API_PORT}/docs"
echo ""
echo "Ctrl+C pour arrêter"
echo ""

# Ouvrir le navigateur (macOS: open, Linux: xdg-open, fallback: python)
if command -v open >/dev/null 2>&1; then
    open "http://localhost:${FRONT_PORT}"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:${FRONT_PORT}"
else
    python3 -m webbrowser "http://localhost:${FRONT_PORT}" 2>/dev/null || true
fi

# ── Garder le script en vie ───────────────────────────────────
wait
