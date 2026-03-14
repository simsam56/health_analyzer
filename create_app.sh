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

# Script exécutable — ouvre Terminal.app avec le bon PATH
cat > "$APP_PATH/Contents/MacOS/$APP_NAME" << 'WRAPPER'
#!/bin/bash
# Lancer dans Terminal.app pour que l'utilisateur voie les logs et puisse Ctrl+C
SCRIPT_DIR="PLACEHOLDER_SCRIPT_DIR"
osascript -e "
tell application \"Terminal\"
    activate
    do script \"export PATH=\\\"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:\\$PATH\\\"; cd '$SCRIPT_DIR' && python3 quick_launch.py; exit\"
end tell
"
WRAPPER
# Injecter le vrai chemin (pas d'expansion dans le heredoc single-quoted)
sed -i '' "s|PLACEHOLDER_SCRIPT_DIR|$SCRIPT_DIR|g" "$APP_PATH/Contents/MacOS/$APP_NAME"
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
