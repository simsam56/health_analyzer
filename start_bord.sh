#!/usr/bin/env bash
# start_bord.sh — Lancement de l'application Bord (FastAPI + Next.js)
#
# Usage:
#   bash start_bord.sh
#   BORD_PORT=8770 bash start_bord.sh
#
# Double-clic ou terminal : démarre le backend + frontend, ouvre le navigateur.
# Ctrl+C pour tout arrêter proprement.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Configuration ──────────────────────────────────────────────────
API_PORT="${BORD_PORT:-8765}"
FRONTEND_PORT="${BORD_FRONTEND_PORT:-3000}"
BACKEND_PID=""
FRONTEND_PID=""

# ── Nettoyage propre à la fermeture ───────────────────────────────
cleanup() {
    echo ""
    echo "🛑 Arrêt de Bord..."
    [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null && wait "$FRONTEND_PID" 2>/dev/null
    [[ -n "$BACKEND_PID" ]]  && kill "$BACKEND_PID"  2>/dev/null && wait "$BACKEND_PID"  2>/dev/null
    echo "✅ Bord arrêté."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ── Trouver un port libre ─────────────────────────────────────────
find_free_port() {
    local port="$1"
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        for p in $(seq "$((port + 1))" "$((port + 10))"); do
            if ! lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
                echo "$p"
                return
            fi
        done
        echo "❌ Impossible de trouver un port libre autour de $port" >&2
        exit 1
    fi
    echo "$port"
}

# ── Vérifications ─────────────────────────────────────────────────
echo "╔═══════════════════════════════════════════╗"
echo "║         🎯  Bord — Lancement              ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Python
if ! command -v python3 &>/dev/null; then
    echo "❌ python3 introuvable. Installez Python 3.11+."
    exit 1
fi

# Node.js
if ! command -v node &>/dev/null; then
    echo "❌ node introuvable. Installez Node.js 18+."
    exit 1
fi

# Dépendances Python (test rapide)
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "📦 Installation des dépendances Python..."
    pip3 install -r requirements.txt
fi

# Dépendances frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installation des dépendances frontend..."
    (cd frontend && npm install)
fi

# Base de données
if [ ! -f "athlete.db" ]; then
    echo "🗄️  Initialisation de la base de données..."
    python3 -c "from pipeline.schema import init_db; init_db('athlete.db')"
    echo "✅ athlete.db créée (vide)"
    echo "   💡 Pour importer des données : python3 main.py --force-parse"
fi

# ── Ports libres ──────────────────────────────────────────────────
API_PORT=$(find_free_port "$API_PORT")
FRONTEND_PORT=$(find_free_port "$FRONTEND_PORT")

echo ""
echo "🔧 Backend API  → http://127.0.0.1:${API_PORT}"
echo "🌐 Frontend     → http://localhost:${FRONTEND_PORT}"
echo "   (Ctrl+C pour arrêter)"
echo ""

# ── Démarrer le backend FastAPI ───────────────────────────────────
BORD_DB="athlete.db" BORD_PORT="$API_PORT" \
    python3 -m uvicorn api.main:app \
    --host 127.0.0.1 \
    --port "$API_PORT" \
    --log-level info &
BACKEND_PID=$!

# ── Démarrer le frontend Next.js ─────────────────────────────────
(cd frontend && PORT="$FRONTEND_PORT" npm run dev) &
FRONTEND_PID=$!

# ── Attendre que les services soient prêts ────────────────────────
echo "⏳ Démarrage des services..."
MAX_WAIT=30
for i in $(seq 1 $MAX_WAIT); do
    BACKEND_OK=false
    FRONTEND_OK=false

    if curl -s "http://127.0.0.1:${API_PORT}/docs" >/dev/null 2>&1; then
        BACKEND_OK=true
    fi
    if curl -s "http://localhost:${FRONTEND_PORT}" >/dev/null 2>&1; then
        FRONTEND_OK=true
    fi

    if $BACKEND_OK && $FRONTEND_OK; then
        break
    fi

    # Vérifier que les processus sont encore vivants
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "❌ Le backend a crashé."
        exit 1
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "❌ Le frontend a crashé."
        exit 1
    fi

    sleep 1
done

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║  ✅  Bord est prêt !                       ║"
echo "║  🌐  http://localhost:${FRONTEND_PORT}                  ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# ── Ouvrir le navigateur ─────────────────────────────────────────
if command -v open &>/dev/null; then
    open "http://localhost:${FRONTEND_PORT}"
elif command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:${FRONTEND_PORT}"
fi

# ── Garder le script en vie ──────────────────────────────────────
wait
