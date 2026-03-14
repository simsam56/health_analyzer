#!/bin/bash
# Créer une version simplifiée de l'app PerformOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$HOME/Desktop/PerformOS_Simple.app"

echo "🎯 Création de PerformOS Simple..."

# Créer la structure
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Script exécutable simplifié
cat > "$APP_PATH/Contents/MacOS/PerformOS" << 'EOF'
#!/bin/bash
cd "/Users/simonhingant/Documents/health_analyzer"
exec /bin/bash launch_simple.sh
EOF

chmod +x "$APP_PATH/Contents/MacOS/PerformOS"

# Info.plist simplifié
cat > "$APP_PATH/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>PerformOS</string>
    <key>CFBundleIdentifier</key>
    <string>com.performos.simple</string>
    <key>CFBundleName</key>
    <string>PerformOS Simple</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
</dict>
</plist>
EOF

# Copier une icône système
cp "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericApplicationIcon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null || echo "Icône système non trouvée"

echo "✅ Application créée: $APP_PATH"
echo "💡 Double-cliquez pour lancer PerformOS (version simplifiée)"
