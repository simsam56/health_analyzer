#!/bin/bash
# Créer l'application macOS "Bord" pour le Bureau

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="Bord"
APP_PATH="$HOME/Desktop/$APP_NAME.app"

echo "Création de $APP_NAME.app sur le Bureau..."

# Supprimer l'ancienne app si présente
rm -rf "$APP_PATH"
# Supprimer aussi l'ancien PerformOS.app
rm -rf "$HOME/Desktop/PerformOS.app"

# Créer la structure
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Script exécutable
cat > "$APP_PATH/Contents/MacOS/$APP_NAME" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
exec python3 quick_launch.py
EOF
chmod +x "$APP_PATH/Contents/MacOS/$APP_NAME"

# Info.plist
cat > "$APP_PATH/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>com.bord.cockpit</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleVersion</key>
    <string>4.0</string>
    <key>CFBundleShortVersionString</key>
    <string>4.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Icône système
cp "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericApplicationIcon.icns" \
   "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null || true

echo ""
echo "Bord.app cree sur le Bureau !"
echo ""
echo "Double-cliquez pour lancer :"
echo "  -> Backend Python + Frontend Next.js"
echo "  -> Navigateur s'ouvre sur le Cockpit"
echo "  -> Ctrl+C dans le terminal pour arreter"
