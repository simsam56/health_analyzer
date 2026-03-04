#!/bin/bash
# ═════════════════════════════════════════════════════════════════════════════
# run.command — Lanceur double-clic pour le Bureau macOS
# Placez ce fichier sur votre Bureau et double-cliquez pour lancer le rapport
# ═════════════════════════════════════════════════════════════════════════════

# Dossier du script (résolution du lien symbolique si nécessaire)
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" && pwd)"
HEALTH_DIR="$HOME/Documents/health_analyzer"

# Titre de la fenêtre terminal
echo -e "\033]0;⚡ Sport Dashboard — Simon Hingant\007"
clear

echo "╔═══════════════════════════════════════════════════════╗"
echo "║       ⚡  Sport Performance Dashboard                  ║"
echo "║       Simon Hingant  ·  $(date '+%d/%m/%Y')                  ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── Vérification du dossier health_analyzer ──────────────────────────────
if [[ ! -f "$HEALTH_DIR/main.py" ]]; then
    echo "❌ Dossier health_analyzer introuvable : $HEALTH_DIR"
    echo ""
    echo "   Assurez-vous que le dossier health_analyzer est dans Documents/"
    echo "   Chemin attendu : $HEALTH_DIR"
    echo ""
    echo "   Appuyez sur Entrée pour fermer..."
    read -r
    exit 1
fi

# ── Vérification du fichier .env ──────────────────────────────────────────
if [[ ! -f "$HEALTH_DIR/.env" ]]; then
    echo "⚠️  Fichier .env non configuré"
    echo ""
    echo "   Pour activer Garmin Connect :"
    echo "   1. Copiez  : cp $HEALTH_DIR/.env.example $HEALTH_DIR/.env"
    echo "   2. Éditez  : open -a TextEdit $HEALTH_DIR/.env"
    echo "   3. Relancez ce script"
    echo ""
    echo "   → Génération sans données Garmin live (Apple Health + Strava uniquement)"
    echo ""
fi

# ── Lancement du pipeline ─────────────────────────────────────────────────
echo "🔄 Démarrage du pipeline…"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

bash "$HEALTH_DIR/sync_and_generate.sh"

EXIT_CODE=$?
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ Terminé avec succès !"
    echo ""
    echo "   📊 Dashboard : ~/Documents/health_analyzer/reports/"
    echo "   ☁️  iCloud    : Fichiers iCloud > SportApp > dashboard.html"
    echo ""
    echo "   → Fermeture automatique dans 5 secondes..."
    sleep 5
else
    echo "❌ Une erreur s'est produite (code $EXIT_CODE)"
    echo "   Consultez les logs dans : ~/Documents/health_analyzer/logs/"
    echo ""
    echo "   Appuyez sur Entrée pour fermer..."
    read -r
fi

exit $EXIT_CODE
