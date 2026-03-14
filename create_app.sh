#!/bin/bash
# Créer une application macOS pour PerformOS avec icône

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="PerformOS"
APP_PATH="$HOME/Desktop/$APP_NAME.app"
SCRIPT_PATH="$SCRIPT_DIR/quick_launch.py"

echo "🎯 Création de l'application $APP_NAME..."

# Créer la structure de l'app
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Créer le script exécutable
cat > "$APP_PATH/Contents/MacOS/$APP_NAME" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
exec python3 quick_launch.py
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
    <string>com.performos.healthanalyzer</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleVersion</key>
    <string>3.0</string>
    <key>CFBundleShortVersionString</key>
    <string>3.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Créer une icône simple (utiliser une icône système)
# Pour une vraie icône, il faudrait créer un .icns
cp "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericApplicationIcon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null || echo "Icône système non trouvée"

echo "✅ Application créée: $APP_PATH"
echo ""
echo "🚀 Double-cliquez sur l'icône pour lancer PerformOS"
echo "📅 Calendrier Apple intégré et modifiable"
echo "🌐 Interface web automatique"
echo ""
echo "🔧 Pour supprimer: rm -rf '$APP_PATH'"
