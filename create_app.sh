#!/bin/bash
# Créer l'application macOS Bord (bureau)
# Usage: bash create_app.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="Bord"
APP_PATH="$HOME/Desktop/$APP_NAME.app"

echo "🎯 Création de l'application $APP_NAME..."

# Supprimer l'ancienne app si elle existe (PerformOS ou Bord)
rm -rf "$HOME/Desktop/PerformOS.app" 2>/dev/null
rm -rf "$APP_PATH" 2>/dev/null

# Créer la structure de l'app
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Créer le script exécutable
cat > "$APP_PATH/Contents/MacOS/$APP_NAME" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
exec bash start_bord.sh
EOF

chmod +x "$APP_PATH/Contents/MacOS/$APP_NAME"

# Créer Info.plist
cat > "$APP_PATH/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>com.bord.app</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
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
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
EOF

# Icône système par défaut (remplacer par une icône custom si disponible)
cp "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericApplicationIcon.icns" \
    "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null || true

echo ""
echo "✅ Application créée : $APP_PATH"
echo ""
echo "🚀 Double-cliquez sur Bord.app pour lancer l'application"
echo "   Backend API  → http://127.0.0.1:8765"
echo "   Frontend     → http://localhost:3000"
echo ""
echo "🔧 Pour supprimer : rm -rf '$APP_PATH'"
