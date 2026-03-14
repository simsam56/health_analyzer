#!/bin/bash
# Créer un raccourci bureau pour PerformOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$HOME/Desktop"
APP_NAME="PerformOS"
ICON_PATH="$SCRIPT_DIR/icon.icns"  # À créer

echo "🎯 Création du raccourci bureau PerformOS..."

# Créer le script de lancement
cat > "$DESKTOP/PerformOS Launcher.command" << 'EOF'
#!/bin/bash
cd "/Users/simonhingant/Documents/health_analyzer"
python3 quick_launch.py
EOF

chmod +x "$DESKTOP/PerformOS Launcher.command"

# Créer un AppleScript pour une meilleure intégration
cat > "$DESKTOP/PerformOS.scpt" << 'EOF'
tell application "Terminal"
    do script "cd \"/Users/simonhingant/Documents/health_analyzer\" && python3 quick_launch.py"
    activate
end tell
EOF

# Compiler l'AppleScript en application
osacompile -o "$DESKTOP/PerformOS.app" "$DESKTOP/PerformOS.scpt"

# Nettoyer
rm "$DESKTOP/PerformOS.scpt"

echo "✅ Raccourci créé: $DESKTOP/PerformOS.app"
echo "💡 Double-cliquez pour lancer PerformOS avec calendrier intégré"
