#!/bin/bash
# PerformOS - Lanceur Terminal

echo "🚀 PerformOS - Ouverture dans Terminal"
echo "======================================"

# Ouvrir une nouvelle fenêtre Terminal et lancer le serveur
osascript -e "
tell application \"Terminal\"
    do script \"cd '/Users/simonhingant/Documents/health_analyzer' && ./server_simple.sh\"
    activate
end tell
"
