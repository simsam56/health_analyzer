#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# install_schedule.sh
# Configure l'exécution automatique du rapport chaque dimanche à 20h00.
# À exécuter UNE SEULE FOIS dans le Terminal :
#   chmod +x ~/Documents/health_analyzer/install_schedule.sh
#   ~/Documents/health_analyzer/install_schedule.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_LABEL="com.simonhingant.healthreport"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$SCRIPT_DIR/logs"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║    🏋️  Health Report — Installation automatisation       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Vérifie que Python3 est disponible
if ! /usr/bin/python3 --version &>/dev/null; then
    echo "❌ python3 introuvable dans /usr/bin/python3"
    echo "   Installe Python 3 depuis https://python.org"
    exit 1
fi

# Vérifie que pandas et numpy sont installés
echo "🔍 Vérification des dépendances Python…"
/usr/bin/python3 -c "import pandas, numpy" 2>/dev/null || {
    echo "📦 Installation de pandas et numpy…"
    /usr/bin/python3 -m pip install pandas numpy --quiet
}
echo "   ✅ pandas, numpy OK"

# Rend les scripts exécutables
chmod +x "$SCRIPT_DIR/run_health_report.sh"
chmod +x "$SCRIPT_DIR/health_analyzer.py"

# Crée les dossiers nécessaires
mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$SCRIPT_DIR/reports"

# ── Génère le plist launchd ──────────────────────────────────────────────────
echo "📝 Création du job launchd (chaque dimanche à 20h00)…"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${SCRIPT_DIR}/run_health_report.sh</string>
    </array>

    <!-- Chaque dimanche à 20h00 -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>20</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/launchd_stderr.log</string>

    <!-- Lance même si le Mac était éteint à l'heure prévue -->
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

echo "   ✅ Plist créé : $PLIST_PATH"

# ── Charge le job ────────────────────────────────────────────────────────────
echo "⚙️  Chargement du job launchd…"

# Décharge l'ancien job s'il existe
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Charge le nouveau job
launchctl load "$PLIST_PATH"

echo "   ✅ Job chargé"

# ── Résumé ───────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅  Installation terminée !                             ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  📅  Le rapport se générera automatiquement              ║"
echo "║      chaque DIMANCHE à 20h00                             ║"
echo "║                                                          ║"
echo "║  📂  Rapports : $SCRIPT_DIR/reports/"
echo "║  📋  Logs     : $LOG_DIR/"
echo "║                                                          ║"
echo "║  ▶️   Pour lancer MAINTENANT :                           ║"
echo "║      bash $SCRIPT_DIR/run_health_report.sh"
echo "║                                                          ║"
echo "║  🗑️   Pour désinstaller :                                ║"
echo "║      launchctl unload $PLIST_PATH"
echo "║      rm $PLIST_PATH"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Propose de lancer maintenant
read -p "▶️  Veux-tu générer le rapport maintenant ? (o/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo "Lancement…"
    bash "$SCRIPT_DIR/run_health_report.sh"
fi
