#!/bin/bash
# smoke_check.sh — Vérification rapide anti-régression cockpit
#
# Ce script valide:
# 1) compilation Python des modules critiques
# 2) génération d'un dashboard local
# 3) syntaxe JS du script embarqué (Node.js --check)
#
# Usage:
#   bash smoke_check.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OUT_HTML="$SCRIPT_DIR/reports/dashboard_smoke.html"
TMP_JS="/tmp/performos_dashboard_smoke.js"

echo "🔎 Smoke check PerformOS..."

python3 -m py_compile \
  main.py \
  cockpit_server.py \
  dashboard/generator.py \
  integrations/apple_calendar.py \
  analytics/planner.py

python3 main.py --skip-parse --no-calendar --output "$OUT_HTML" >/tmp/performos_smoke_run.log 2>&1

python3 - <<'PY'
from pathlib import Path

html_path = Path("/Users/simonhingant/Documents/health_analyzer/reports/dashboard_smoke.html")
js_path = Path("/tmp/performos_dashboard_smoke.js")
html = html_path.read_text(encoding="utf-8")
start = html.find("<script>")
end = html.rfind("</script>")
if start == -1 or end == -1 or end <= start:
    raise SystemExit("Script block introuvable dans dashboard_smoke.html")
js_path.write_text(html[start + 8:end], encoding="utf-8")
print("dashboard_smoke_js_len=", len(js_path.read_text(encoding="utf-8")))
PY

if ! command -v node >/dev/null 2>&1; then
  echo "❌ Node.js introuvable. Installe Node pour activer le check JS."
  exit 1
fi

node --check "$TMP_JS"

echo "✅ Smoke check OK"
