#!/bin/bash
# Bord — Tests rapides de synchronisation via curl
# Usage: bash tests/test_sync.sh [PORT] [TOKEN]

PORT="${1:-8765}"
TOKEN="${2:-$(grep -oP 'const\s+API_TOKEN\s*=\s*"\K[^"]+' reports/dashboard.html 2>/dev/null || echo bord)}"
BASE="http://127.0.0.1:${PORT}/api/planner"

echo "============================================"
echo "Bord Sync Tests (curl)"
echo "Base: ${BASE}"
echo "Token: ${TOKEN:0:8}..."
echo "============================================"
echo

# --- Test 1: GET /events ---
echo "[TEST] GET /events"
curl -s -w "\nHTTP %{http_code}\n" \
  -H "X-Bord-Token: ${TOKEN}" \
  "${BASE}/events?start=2026-01-01&end=2026-12-31" | tail -1
echo

# --- Test 2: POST /tasks (créer tâche test) ---
echo "[TEST] POST /tasks — créer tâche"
TASK_RESP=$(curl -s \
  -H "Content-Type: application/json" \
  -H "X-Bord-Token: ${TOKEN}" \
  -X POST \
  -d '{"title":"curl-test-sync","category":"sport","scheduled":true,"start_at":"2026-03-10T08:00:00","end_at":"2026-03-10T09:00:00","sync_apple":false}' \
  "${BASE}/tasks")
echo "${TASK_RESP}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  ok={d.get(\"ok\")} id={d.get(\"created\",{}).get(\"id\")}')" 2>/dev/null || echo "  ${TASK_RESP}"
TASK_ID=$(echo "${TASK_RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('created',{}).get('id',''))" 2>/dev/null)
echo

# --- Test 3: POST /calendar/push ---
echo "[TEST] POST /calendar/push"
curl -s \
  -H "Content-Type: application/json" \
  -H "X-Bord-Token: ${TOKEN}" \
  -X POST -d '{}' \
  "${BASE}/calendar/push" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); print(f'  ok={d.get(\"ok\")} total={r.get(\"total\")} synced={r.get(\"synced\")} failed={r.get(\"failed\")}')" 2>/dev/null
echo

# --- Test 4: POST /calendar/sync ---
echo "[TEST] POST /calendar/sync"
curl -s \
  -H "Content-Type: application/json" \
  -H "X-Bord-Token: ${TOKEN}" \
  -X POST -d '{}' \
  "${BASE}/calendar/sync" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('sync',{}); print(f'  ok={d.get(\"ok\")} events={len(d.get(\"events\",[]))} events_synced={s.get(\"events_synced\",\"?\")}')" 2>/dev/null
echo

# --- Test 5: DB state ---
echo "[TEST] DB state"
sqlite3 athlete.db "SELECT id, title, source, calendar_uid FROM planner_tasks ORDER BY id DESC LIMIT 3;" 2>/dev/null || echo "  DB not accessible"
sqlite3 athlete.db "SELECT id, title, start_at FROM calendar_events ORDER BY id DESC LIMIT 3;" 2>/dev/null || echo "  calendar_events not accessible"
echo

# --- Cleanup ---
if [ -n "${TASK_ID}" ]; then
  echo "[CLEANUP] DELETE /tasks/${TASK_ID}"
  curl -s \
    -H "X-Bord-Token: ${TOKEN}" \
    -X DELETE \
    "${BASE}/tasks/${TASK_ID}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  ok={d.get(\"ok\")}')" 2>/dev/null
  echo
fi

echo "============================================"
echo "Done."
echo "============================================"
