#!/bin/bash
set -euo pipefail

# Bord — SessionStart hook for Claude Code on the web
# Installs Python + Node.js dependencies so linters and tests work.

# Only run in remote (web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# ── Python dependencies ──────────────────────────────────────────
echo "📦 Installing Python dependencies..."
# Filter out macOS-only packages (pyobjc) when running on Linux
# Use --ignore-installed to avoid conflicts, skip packages that fail to build
grep -v "pyobjc" requirements.txt > /tmp/requirements-filtered.txt
pip install -q --ignore-installed -r /tmp/requirements-filtered.txt || {
  echo "⚠️  Some packages failed, installing individually..."
  while IFS= read -r pkg; do
    [[ -z "$pkg" || "$pkg" == \#* ]] && continue
    pip install -q "$pkg" 2>/dev/null || echo "  ⏭️  Skipped: $pkg"
  done < /tmp/requirements-filtered.txt
}

# ── Node.js dependencies (frontend) ─────────────────────────────
if [ -f frontend/package.json ]; then
  echo "📦 Installing Node.js dependencies..."
  cd frontend
  npm install --prefer-offline --no-audit --no-fund
  cd "$CLAUDE_PROJECT_DIR"
fi

# ── Set PYTHONPATH for imports ───────────────────────────────────
echo "export PYTHONPATH=\"$CLAUDE_PROJECT_DIR\"" >> "$CLAUDE_ENV_FILE"

echo "✅ Bord session ready"
