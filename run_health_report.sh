#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# run_health_report.sh
# Lance le générateur de dashboard Health et ouvre le résultat dans le navigateur.
# Appelé automatiquement chaque dimanche soir par launchd.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/health_report.log"
PYTHON_BIN="/usr/bin/python3"
DATE_TAG=$(date '+%Y-%m-%d')
OUTPUT="$SCRIPT_DIR/reports/dashboard_${DATE_TAG}.html"

# Crée les dossiers si besoin
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/reports"

echo "──────────────────────────────────────────" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S')  Démarrage du dashboard Health" >> "$LOG_FILE"

# Lance le script Python
"$PYTHON_BIN" "$SCRIPT_DIR/build_dashboard.py" \
    --export "$SCRIPT_DIR/export.xml" \
    --strava "$SCRIPT_DIR/export_strava/activities.csv" \
    --output "$OUTPUT" \
    >> "$LOG_FILE" 2>&1

STATUS=$?
if [ $STATUS -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S')  ✅ Dashboard généré : $OUTPUT" >> "$LOG_FILE"

    # Ouvre dans le navigateur par défaut
    open "$OUTPUT" 2>/dev/null || true

    # Notification macOS
    osascript -e 'display notification "Ton dashboard santé de la semaine est prêt ! 💪" with title "Health Dashboard" sound name "Glass"' 2>/dev/null || true
else
    echo "$(date '+%Y-%m-%d %H:%M:%S')  ❌ Erreur lors de la génération (code $STATUS)" >> "$LOG_FILE"

    # Notification d'erreur
    osascript -e 'display notification "Erreur lors de la génération du dashboard. Consulte les logs." with title "Health Dashboard ❌"' 2>/dev/null || true
fi

echo "──────────────────────────────────────────" >> "$LOG_FILE"
exit $STATUS
