#!/bin/bash
# backup_local.sh — Snapshot local complet PerformOS
# Usage:
#   bash backup_local.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TS="$(date '+%Y%m%d_%H%M%S')"
BACKUP_ROOT="$SCRIPT_DIR/backups"
OUT_DIR="$BACKUP_ROOT/$TS"
mkdir -p "$OUT_DIR"

echo "╔════════════════════════════════════════════════════════╗"
echo "║  PerformOS · Backup local snapshot                    ║"
echo "╚════════════════════════════════════════════════════════╝"
echo "📁 Dossier: $OUT_DIR"

# 1) Snapshot code (dernier commit)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git rev-parse HEAD > "$OUT_DIR/git_head.txt" || true
  git status --short > "$OUT_DIR/git_status.txt" || true
  git diff > "$OUT_DIR/git_diff.patch" || true
  git diff --staged > "$OUT_DIR/git_diff_staged.patch" || true
  git ls-files -o --exclude-standard > "$OUT_DIR/git_untracked.txt" || true
  git archive --format=tar.gz -o "$OUT_DIR/source_head.tar.gz" HEAD
  echo "✅ Snapshot Git créé"
else
  echo "⚠️  Repo Git non détecté: snapshot code ignoré"
fi

# 2) Snapshot base SQLite (cohérent)
if [ -f "$SCRIPT_DIR/athlete.db" ]; then
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$SCRIPT_DIR/athlete.db" ".backup '$OUT_DIR/athlete.db'"
  else
    cp "$SCRIPT_DIR/athlete.db" "$OUT_DIR/athlete.db"
  fi
  [ -f "$SCRIPT_DIR/athlete.db-wal" ] && cp "$SCRIPT_DIR/athlete.db-wal" "$OUT_DIR/athlete.db-wal" || true
  [ -f "$SCRIPT_DIR/athlete.db-shm" ] && cp "$SCRIPT_DIR/athlete.db-shm" "$OUT_DIR/athlete.db-shm" || true
  echo "✅ Base SQLite sauvegardée"
else
  echo "ℹ️  athlete.db absente: étape DB ignorée"
fi

# 3) Snapshot dashboard récent
LATEST_DASH="$(ls -1t "$SCRIPT_DIR"/reports/dashboard_*.html 2>/dev/null | head -n 1 || true)"
if [ -n "${LATEST_DASH:-}" ] && [ -f "$LATEST_DASH" ]; then
  cp "$LATEST_DASH" "$OUT_DIR/"
  echo "✅ Dashboard copié: $(basename "$LATEST_DASH")"
else
  echo "ℹ️  Aucun dashboard daté trouvé dans reports/"
fi

# 4) Métadonnées opérationnelles
{
  echo "timestamp=$TS"
  echo "hostname=$(hostname)"
  echo "cwd=$SCRIPT_DIR"
  echo "python=$(command -v python3 || true)"
  python3 --version 2>/dev/null | sed 's/^/python_version=/'
} > "$OUT_DIR/metadata.txt"

echo
echo "✅ Backup local terminé"
echo "   - code: $OUT_DIR/source_head.tar.gz"
echo "   - db  : $OUT_DIR/athlete.db"
echo "   - meta: $OUT_DIR/metadata.txt"
