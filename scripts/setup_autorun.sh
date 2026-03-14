#!/bin/bash
# setup_autorun.sh — PerformOS v3 · Installation automatique complète
# Lance ce script une seule fois dans ton Terminal pour tout configurer.
#
# Il va :
#   1. Installer les dépendances Python
#   2. Initialiser la base de données (si besoin)
#   3. Lancer la sync Garmin COMPLÈTE (toutes tes données depuis 2017)
#   4. Régénérer le dashboard
#   5. Installer la sync automatique quotidienne à 06h30

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  PerformOS v3 · Setup automatique complet                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Python & dépendances ──────────────────────────────────────
echo "📦 Installation des dépendances Python..."
pip3 install --quiet garminconnect python-dotenv fitparse pyobjc-framework-EventKit 2>&1 | tail -3
echo "   ✅ garminconnect + python-dotenv + fitparse + EventKit OK"
echo ""

# ── 2. Vérifier .env ─────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "❌ Fichier .env manquant. Lance d'abord :"
    echo "   cp .env.example .env && open -e .env"
    exit 1
fi

EMAIL=$(grep "GARMIN_EMAIL" .env | cut -d= -f2)
if [[ "$EMAIL" == *"exemple"* ]] || [[ -z "$EMAIL" ]]; then
    echo "❌ Le fichier .env n'est pas configuré avec tes vrais credentials."
    echo "   Ouvre .env et renseigne ton email et mot de passe Garmin."
    exit 1
fi
echo "✅ Credentials chargés pour : $EMAIL"
echo ""

# ── 3. Init DB si besoin ─────────────────────────────────────────
if [ ! -f "athlete.db" ]; then
    echo "🗄️  Initialisation base de données..."
    python3 main.py --skip-parse --weeks-muscle 6 2>/dev/null || true
    echo ""
fi

# ── 4. Sync Garmin COMPLÈTE (depuis 2017) ────────────────────────
echo "⌚ Sync Garmin Connect COMPLÈTE (depuis 2017)..."
echo "   (peut prendre 10-20 min selon la quantité de données)"
echo "   Les logs s'affichent en temps réel :"
echo ""
python3 garmin_sync_full.py --full
echo ""

# ── 5. Régénérer le dashboard ────────────────────────────────────
echo "🎨 Génération dashboard avec toutes les données..."
python3 main.py --skip-parse --weeks-muscle 6
echo ""

# ── 6. Installer sync quotidienne ────────────────────────────────
echo "⏰ Installation de la sync automatique quotidienne (06h30)..."
python3 garmin_sync_full.py --install
echo ""

# ── 7. Ouvrir le dashboard ───────────────────────────────────────
DASHBOARD=$(ls -t reports/dashboard_*.html 2>/dev/null | head -1)
if [ -n "$DASHBOARD" ]; then
    open -a Safari "$SCRIPT_DIR/$DASHBOARD"
    echo "🌐 Dashboard ouvert dans Safari : $DASHBOARD"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ Setup terminé !                                      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  La sync Garmin tourne maintenant chaque matin à 06h30  ║"
echo "║  Pour forcer une sync maintenant :                       ║"
echo "║    launchctl start com.performos.garmin-sync             ║"
echo "║  Pour voir les logs :                                    ║"
echo "║    tail -f garmin_sync.log                               ║"
echo "╚══════════════════════════════════════════════════════════╝"
