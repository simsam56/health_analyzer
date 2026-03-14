#!/bin/bash
# PerformOS - Lanceur Terminal Automatique

echo "🚀 PerformOS - Lancement automatique"
echo "===================================="

# Ouvrir une nouvelle fenêtre Terminal et lancer le serveur
osascript -e "
tell application \"Terminal\"
    do script \"cd '/Users/simonhingant/Documents/health_analyzer' && python3 server_simple.py\"
    activate
end tell
"
