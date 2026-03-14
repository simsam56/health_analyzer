"""
Tests for deduplication logic
"""

import sqlite3
import tempfile
from pathlib import Path

from main import deduplicate_activities


def test_deduplicate_activities():
    """Test activity deduplication"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_f:
        db_path = Path(db_f.name)

    try:
        # Create test database with duplicate activities
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE activities (
                id INTEGER PRIMARY KEY,
                source TEXT,
                type TEXT,
                started_at TEXT,
                duration_s INTEGER,
                canonical_key TEXT UNIQUE
            )
        """)

        # Insert duplicate activities (same type, date, duration)
        conn.execute("""
            INSERT INTO activities (source, type, started_at, duration_s, canonical_key)
            VALUES
            ('strava_fit', 'Running', '2024-01-01T10:00:00', 3600, 'key1'),
            ('garmin_connect', 'Running', '2024-01-01T10:00:00', 3600, 'key1'),
            ('apple_health', 'Running', '2024-01-01T10:00:00', 3600, 'key1')
        """)
        conn.commit()

        before_count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        assert before_count == 3

        conn.close()

        # Run deduplication
        removed = deduplicate_activities(db_path)

        # Verify deduplication kept the best source (strava > garmin > apple)
        conn = sqlite3.connect(str(db_path))
        after_count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        remaining = conn.execute("SELECT source FROM activities").fetchall()

        assert after_count == 1  # Only one activity remains
        assert remaining[0][0] == "strava_fit"  # Best source kept
        assert removed == 2  # Two duplicates removed

        conn.close()

    finally:
        db_path.unlink(missing_ok=True)
