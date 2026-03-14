#!/bin/bash
# ═════════════════════════════════════════════════════════════════════════════
# sync_and_generate.sh — Pipeline PerformOS v3
# ═════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATE_TAG=$(date '+%Y-%m-%d')
DATE_FR=$(date '+%d/%m/%Y')
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/dashboard_${DATE_TAG}.log"
REPORT="$SCRIPT_DIR/reports/dashboard_${DATE_TAG}.html"
ICLOUD_DIR="${HOME}/Library/Mobile Documents/com~apple~CloudDocs/SportApp"
PYTHON_BIN="$(which python3 || echo /usr/bin/python3)"

mkdir -p "$LOG_DIR" "$SCRIPT_DIR/reports"

log()    { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
notify() {
    local title="$1" msg="$2" sound="${3:-Glass}"
    osascript -e "display notification \"$msg\" with title \"$title\" sound name \"$sound\"" 2>/dev/null || true
}

log "═══════════════════════════════════════════════════════"
log "  ⚡ PerformOS v3 — Sport Dashboard"
log "  $DATE_FR"
log "═══════════════════════════════════════════════════════"

"$PYTHON_BIN" -c "import fitparse" 2>/dev/null || {
    log "⬇️  fitparse manquant, installation..."
    "$PYTHON_BIN" -m pip install fitparse python-dotenv --break-system-packages -q >> "$LOG_FILE" 2>&1 || true
}

log "🔄 Génération du dashboard..."
notify "PerformOS ⏳" "Analyse des données en cours..."

if "$PYTHON_BIN" "$SCRIPT_DIR/main.py" \
    --export "$SCRIPT_DIR/export.xml" \
    --strava "$SCRIPT_DIR/export_strava" \
    --db     "$SCRIPT_DIR/athlete.db" \
    --output "$REPORT" \
    --weeks-muscle 6 \
    >> "$LOG_FILE" 2>&1; then

    log "✅ Dashboard généré : $REPORT"
    REPORT_KB=$(du -k "$REPORT" | cut -f1)
    log "   Taille : ${REPORT_KB} KB"
else
    log "❌ Erreur lors de la génération — consultez $LOG_FILE"
    notify "PerformOS ❌" "Erreur de génération" "Basso"
    exit 1
fi

if [[ -d "${HOME}/Library/Mobile Documents/com~apple~CloudDocs" ]]; then
    mkdir -p "$ICLOUD_DIR"
    cp "$REPORT" "$ICLOUD_DIR/dashboard.html"
    cp "$REPORT" "$ICLOUD_DIR/dashboard_${DATE_TAG}.html"
    log "☁️  Synchronisé vers iCloud : SportApp/dashboard.html"
else
    log "ℹ️  iCloud non détecté — copie ignorée"
fi

if [[ "${OPEN_BROWSER:-1}" == "1" ]]; then
    open "$REPORT" 2>/dev/null || true
fi

log "🎉 Dashboard complet en ${SECONDS}s"
notify "⚡ PerformOS" "Rapport du ${DATE_FR} prêt" "Glass"
log "═══════════════════════════════════════════════════════"

exit 0
