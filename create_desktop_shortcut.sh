#!/bin/bash
# Créer un raccourci bureau pour Board

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$HOME/Desktop"

echo "Création du raccourci bureau Board..."

# Créer le script de lancement .command
cat > "$DESKTOP/Board.command" << SCRIPT
#!/bin/bash
cd "$SCRIPT_DIR"
bash board.sh
SCRIPT

chmod +x "$DESKTOP/Board.command"

# Créer un AppleScript pour une meilleure intégration
cat > "$DESKTOP/Board.scpt" << SCRIPT
tell application "Terminal"
    do script "cd \"$SCRIPT_DIR\" && bash board.sh"
    activate
end tell
SCRIPT

# Compiler l'AppleScript en application
osacompile -o "$DESKTOP/Board.app" "$DESKTOP/Board.scpt" 2>/dev/null

# Nettoyer
rm -f "$DESKTOP/Board.scpt"

echo "Raccourci créé: $DESKTOP/Board.app"
echo "Double-cliquez pour lancer Board"
