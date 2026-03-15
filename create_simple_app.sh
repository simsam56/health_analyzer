#!/bin/bash
# Créer une version simplifiée de l'app Board
# NOTE: Préférez create_board_app.sh pour la version complète (FastAPI + Next.js)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$HOME/Desktop/Board.app"

echo "Création de Board..."

# Créer la structure
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Script exécutable simplifié (chemin dynamique)
cat > "$APP_PATH/Contents/MacOS/Board" << SCRIPT
#!/bin/bash
cd "$SCRIPT_DIR"
exec /bin/bash board.sh
SCRIPT

chmod +x "$APP_PATH/Contents/MacOS/Board"

# Info.plist
cat > "$APP_PATH/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Board</string>
    <key>CFBundleIdentifier</key>
    <string>com.bord.dashboard</string>
    <key>CFBundleName</key>
    <string>Board</string>
    <key>CFBundleVersion</key>
    <string>4.0</string>
    <key>CFBundleShortVersionString</key>
    <string>4.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Copier l'icône
if [ -f "$SCRIPT_DIR/assets/board-icon.icns" ]; then
    cp "$SCRIPT_DIR/assets/board-icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
else
    cp "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericApplicationIcon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null || echo "Icône système non trouvée"
fi

echo "Application créée: $APP_PATH"
echo "Double-cliquez pour lancer Board"
