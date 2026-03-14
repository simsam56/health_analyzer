#!/usr/bin/env python3
"""Diagnose synchronization issues between PerformOS and Apple Calendar."""

import sqlite3

conn = sqlite3.connect("athlete.db")
cursor = conn.cursor()

print("\n🔍 DIAGNOSTIC DE SYNCHRONISATION")
print("=" * 70)

# Check planner_tasks
try:
    cursor.execute("SELECT COUNT(*) FROM planner_tasks WHERE scheduled=1")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM planner_tasks WHERE scheduled=1 AND source='apple_calendar'"
    )
    apple = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM planner_tasks WHERE scheduled=1 AND source='local'")
    local = cursor.fetchone()[0]

    print(f"\n📋 PLANNER TASKS (scheduling): {total} total")
    print(f"   - Apple Calendar source: {apple}")
    print(f"   - Local source: {local}")

    if local > 0:
        print(f"\n⚠️  {local} events are LOCAL but NOT synced to Apple!")
        cursor.execute(
            "SELECT id, title, scheduled_start FROM planner_tasks WHERE scheduled=1 AND source='local' LIMIT 3"
        )
        print("   Sample local events:")
        for _task_id, title, start in cursor.fetchall():
            print(f"     - {title} @ {start}")

except Exception as e:
    print(f"❌ Error checking planner_tasks: {e}")

# Check calendar_events (what's actually in Apple Calendar)
try:
    cursor.execute("SELECT COUNT(*) FROM calendar_events")
    apple_count = cursor.fetchone()[0]
    cursor.execute("SELECT title, start_at FROM calendar_events LIMIT 5")

    print("\n📱 APPLE CALENDAR (synced from iPhone):")
    print(f"   - Total events: {apple_count}")
    print("   - Recent events:")
    for title, start_at in cursor.fetchall():
        print(f"     - {title} @ {start_at}")

except Exception as e:
    print(f"❌ Error checking calendar_events: {e}")

print("\n💡 DIAGNOSIS:")
print("   If LOCAL events > 0 and APPLE CALENDAR has few events,")
print("   then local events are NOT being pushed to Apple Calendar!")

conn.close()
