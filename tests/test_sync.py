#!/usr/bin/env python3
"""Tests de synchronisation Planning <-> Apple Calendar.

Usage:
    # Avec le serveur déjà lancé :
    python3 tests/test_sync.py

    # Avec un port/token personnalisé :
    PERFORMOS_PORT=8765 PERFORMOS_API_TOKEN=montoken python3 tests/test_sync.py
"""

import json
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

BASE_URL = f"http://127.0.0.1:{os.environ.get('PERFORMOS_PORT', '8765')}"
API_BASE = f"{BASE_URL}/api/planner"

# Token: env var > extraction depuis dashboard.html > fallback
TOKEN = os.environ.get("PERFORMOS_API_TOKEN", "")
if not TOKEN:
    try:
        import re

        html = Path("reports/dashboard.html").read_text(encoding="utf-8")
        m = re.search(r'const\s+API_TOKEN\s*=\s*"([^"]+)"', html)
        if m:
            TOKEN = m.group(1)
    except Exception:
        pass
if not TOKEN:
    TOKEN = "performos"


def api(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    data = json.dumps(body or {}).encode() if body is not None else b"{}"
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-PerformOS-Token", TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return {"status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": json.loads(e.read())}
    except Exception as e:
        return {"status": 0, "body": {"error": str(e)}}


def test_server_alive():
    """Test 0: le serveur répond."""
    r = api("GET", "/events?start=2026-01-01&end=2026-12-31")
    assert r["status"] == 200, f"Server not responding: {r}"
    assert r["body"].get("ok"), f"Server returned error: {r['body']}"
    print(f"  OK — {len(r['body'].get('events', []))} events")


def test_create_task():
    """Test 1: créer une tâche via POST /tasks."""
    payload = {
        "title": "Test Sync Task",
        "category": "sport",
        "scheduled": True,
        "start_at": "2026-03-10T08:00:00",
        "end_at": "2026-03-10T09:00:00",
        "sync_apple": False,  # ne pas pousser vers Apple pour ce test
    }
    r = api("POST", "/tasks", payload)
    assert r["status"] == 201, f"Create task failed: {r}"
    assert r["body"].get("ok"), f"Create not ok: {r['body']}"
    task_id = r["body"].get("created", {}).get("task_id") or r["body"].get("created", {}).get("id")
    assert task_id, f"No task id returned: {r['body'].get('created', {})}"
    print(f"  OK — task #{task_id} created")
    return task_id


def test_push_to_apple():
    """Test 2: push local → Apple Calendar."""
    r = api("POST", "/calendar/push")
    assert r["status"] == 200, f"Push failed: {r}"
    body = r["body"]
    print(
        f"  Push result: ok={body.get('ok')}, "
        f"total={body.get('result', {}).get('total', '?')}, "
        f"synced={body.get('result', {}).get('synced', '?')}, "
        f"failed={body.get('result', {}).get('failed', '?')}"
    )
    if body.get("result", {}).get("error"):
        print(f"  ⚠ Error: {body['result']['error']}")
    return body


def test_pull_from_apple():
    """Test 3: pull Apple Calendar → SQLite."""
    r = api("POST", "/calendar/sync")
    assert r["status"] == 200, f"Sync failed: {r}"
    body = r["body"]
    assert body.get("ok"), f"Sync not ok: {body}"
    event_count = len(body.get("events", []))
    sync_info = body.get("sync", {})
    print(f"  OK — {event_count} events, synced={sync_info.get('events_synced', '?')}")
    return body


def test_db_state():
    """Test 4: vérifier l'état de la DB."""
    db = Path("athlete.db")
    if not db.exists():
        print("  SKIP — athlete.db not found")
        return

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row

    tasks = conn.execute(
        "SELECT id, title, source, calendar_uid, start_at "
        "FROM planner_tasks ORDER BY id DESC LIMIT 5"
    ).fetchall()
    print(f"  Recent tasks ({len(tasks)}):")
    for t in tasks:
        uid = t["calendar_uid"] or "-"
        print(f"    #{t['id']} {t['title'][:30]:30s} src={t['source'] or '-':15s} uid={uid[:20]}")

    cal_events = conn.execute(
        "SELECT id, title, start_at FROM calendar_events ORDER BY id DESC LIMIT 5"
    ).fetchall()
    print(f"  Recent calendar_events ({len(cal_events)}):")
    for e in cal_events:
        print(f"    #{e['id']} {e['title'][:30]:30s} start={e['start_at']}")

    conn.close()


def test_cleanup(task_id: int):
    """Test 5: supprimer la tâche de test."""
    r = api("DELETE", f"/tasks/{task_id}")
    assert r["status"] == 200, f"Delete failed: {r}"
    print(f"  OK — task #{task_id} deleted")


def main():
    print(f"\n{'=' * 60}")
    print(f"PerformOS Sync Tests — {BASE_URL}")
    print(f"Token: {TOKEN[:8]}...")
    print(f"{'=' * 60}\n")

    passed = 0
    failed = 0
    tests = [
        ("Server alive", test_server_alive, False),
        ("Create task", test_create_task, False),
        ("Push → Apple", test_push_to_apple, False),
        ("Pull ← Apple", test_pull_from_apple, False),
        ("DB state", test_db_state, False),
    ]

    task_id = None
    for name, fn, _skip in tests:
        print(f"[TEST] {name}")
        try:
            result = fn()
            if name == "Create task":
                task_id = result
            passed += 1
            print()
        except AssertionError as e:
            print(f"  FAIL: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}\n")
            failed += 1

    # Cleanup
    if task_id:
        print("[CLEANUP] Delete test task")
        try:
            test_cleanup(task_id)
        except Exception as e:
            print(f"  Cleanup error: {e}")
        print()

    print(f"{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
