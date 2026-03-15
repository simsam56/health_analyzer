#!/usr/bin/env bash
# create_board_app.sh — Crée Board.app sur le bureau macOS
#
# Usage:
#   bash create_board_app.sh
#
# Résultat: ~/Desktop/Board.app (double-cliquez pour lancer)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$HOME/Desktop/Board.app"

echo ""
echo "Board — Création de l'application macOS"
echo "========================================"
echo ""

# ── Supprimer l'ancienne version si elle existe ───────────────
if [ -d "$APP_PATH" ]; then
    echo "Suppression de l'ancienne Board.app..."
    rm -rf "$APP_PATH"
fi

# Supprimer aussi les anciennes versions PerformOS
for old_app in "$HOME/Desktop/PerformOS"*.app "$HOME/Desktop/PerformOS_Simple.app"; do
    [ -d "$old_app" ] && rm -rf "$old_app" && echo "Ancien lanceur supprimé: $old_app"
done

# ── Créer la structure .app ───────────────────────────────────
echo "Création de Board.app..."
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# ── Script exécutable principal ───────────────────────────────
cat > "$APP_PATH/Contents/MacOS/Board" << SCRIPT
#!/bin/bash
# Board — Lanceur macOS
BOARD_DIR="$SCRIPT_DIR"
cd "\$BOARD_DIR"
exec /bin/bash "\$BOARD_DIR/board.sh"
SCRIPT

chmod +x "$APP_PATH/Contents/MacOS/Board"

# ── Info.plist ────────────────────────────────────────────────
cat > "$APP_PATH/Contents/Info.plist" << 'PLIST'
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
    <key>CFBundleDisplayName</key>
    <string>Board</string>
    <key>CFBundleVersion</key>
    <string>4.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>4.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSUIElement</key>
    <false/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

# ── Icône ─────────────────────────────────────────────────────
# Convertir le SVG en icns si les outils macOS sont disponibles
ICON_SVG="$SCRIPT_DIR/assets/board-icon.svg"
ICON_DEST="$APP_PATH/Contents/Resources/AppIcon.icns"

if [ -f "$ICON_SVG" ]; then
    if command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
        # macOS: convertir SVG → PNG → iconset → icns
        echo "Génération de l'icône..."
        ICONSET_DIR=$(mktemp -d)/AppIcon.iconset
        mkdir -p "$ICONSET_DIR"

        # Générer les tailles requises via qlmanage ou sips
        # On utilise python pour le SVG → PNG car sips ne supporte pas SVG directement
        python3 -c "
import subprocess, os, tempfile
svg = '$ICON_SVG'
iconset = '$ICONSET_DIR'
sizes = [16, 32, 64, 128, 256, 512]
for s in sizes:
    out = os.path.join(iconset, f'icon_{s}x{s}.png')
    out2x = os.path.join(iconset, f'icon_{s//2}x{s//2}@2x.png') if s > 16 else None
    # Use qlmanage to render SVG
    tmp = os.path.join(tempfile.gettempdir(), f'board_icon_{s}.png')
    subprocess.run(['qlmanage', '-t', '-s', str(s), '-o', tempfile.gettempdir(), svg],
                   capture_output=True)
    rendered = svg + '.png'  # qlmanage adds .png
    tmp_rendered = os.path.join(tempfile.gettempdir(), os.path.basename(svg) + '.png')
    if os.path.exists(tmp_rendered):
        subprocess.run(['sips', '-z', str(s), str(s), tmp_rendered, '--out', out], capture_output=True)
        if out2x:
            subprocess.run(['cp', out, out2x], capture_output=True)
        os.remove(tmp_rendered)
" 2>/dev/null

        # Créer l'icns
        if ls "$ICONSET_DIR"/*.png >/dev/null 2>&1; then
            iconutil -c icns "$ICONSET_DIR" -o "$ICON_DEST" 2>/dev/null
            echo "Icône personnalisée créée"
        fi
        rm -rf "$(dirname "$ICONSET_DIR")"
    fi
fi

# Fallback: utiliser une icône système si pas d'icône personnalisée
if [ ! -f "$ICON_DEST" ]; then
    # Essayer plusieurs icônes système macOS
    for sys_icon in \
        "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/DashboardIcon.icns" \
        "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/ToolbarCustomizeIcon.icns" \
        "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericApplicationIcon.icns"; do
        if [ -f "$sys_icon" ]; then
            cp "$sys_icon" "$ICON_DEST"
            echo "Icône système utilisée: $(basename "$sys_icon")"
            break
        fi
    done
fi

# ── Résultat ──────────────────────────────────────────────────
echo ""
echo "Board.app créé avec succès !"
echo "  Emplacement : $APP_PATH"
echo ""
echo "Double-cliquez sur Board.app sur votre bureau pour lancer :"
echo "  - Backend FastAPI (port 8765)"
echo "  - Frontend Next.js (port 3000)"
echo "  - Navigateur ouvert automatiquement"
echo ""
echo "Note : Si macOS bloque l'app, allez dans :"
echo "  Réglages > Confidentialité & Sécurité > Ouvrir quand même"
echo ""
