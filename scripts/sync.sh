#!/bin/bash
# sync.sh — PerformOS v3 · Script de synchronisation complète
# Utilisation : ./sync.sh [--garmin] [--reset] [--days 60]
#
# Ce script :
#   1. Lance main.py avec les options passées
#   2. Copie le dashboard dans iCloud
#   3. Ouvre le dashboard dans Safari
#   4. Commit git automatique

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Config
ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/PerformOS"
DASHBOARD_FILE="reports/dashboard_$(date +%Y-%m-%d).html"
GARMIN_FLAG=""
RESET_FLAG=""
DAYS_FLAG="--days 30"

# Parse args
for arg in "$@"; do
    case $arg in
        --garmin) GARMIN_FLAG="--garmin" ;;
        --reset)  RESET_FLAG="--reset" ;;
        --days*) DAYS_FLAG="$arg" ;;
    esac
done

echo "╔════════════════════════════════════════════╗"
echo "║  PerformOS v3 · Sync & Dashboard           ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# 1. Pipeline + Dashboard
python3 main.py $GARMIN_FLAG $RESET_FLAG $DAYS_FLAG --weeks-muscle 6 --output "$DASHBOARD_FILE"

# 2. Copie iCloud (si disponible)
if [ -d "$HOME/Library/Mobile Documents/com~apple~CloudDocs" ]; then
    mkdir -p "$ICLOUD_DIR"
    cp "$DASHBOARD_FILE" "$ICLOUD_DIR/dashboard_latest.html"
    echo "  ☁️  Copié dans iCloud : $ICLOUD_DIR"
fi

# 3. Ouvrir dans Safari
if [ "$(uname)" == "Darwin" ]; then
    open -a Safari "$SCRIPT_DIR/$DASHBOARD_FILE"
    echo "  🌐 Ouvert dans Safari"
fi

# 4. Git commit automatique
git add -A -- '*.py' '*.sh' '*.md' reports/
CHANGED=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
if [ "$CHANGED" -gt "0" ]; then
    DATE=$(date +"%Y-%m-%d %H:%M")
    git commit -m "perf: dashboard PerformOS v3 - $DATE"
    echo "  ✅ Git commit : $CHANGED fichiers"
else
    echo "  ℹ️  Aucun changement à committer"
fi

echo ""
echo "Terminé ! Dashboard : $SCRIPT_DIR/$DASHBOARD_FILE"
