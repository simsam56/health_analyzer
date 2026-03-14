"""
Tests for Apple Health parsing pipeline
"""

import sqlite3
import tempfile
from pathlib import Path

from pipeline.parse_apple_health import run as parse_apple_health


def test_parse_apple_health_basic():
    """Test basic Apple Health XML parsing"""
    # Create a minimal test XML
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
             startDate="2024-01-01T10:00:00Z"
             endDate="2024-01-01T11:00:00Z"
             duration="3600.0"
             totalDistance="10000"
             totalEnergyBurned="500">
        <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning">
            <sum unit="km">10.0</sum>
        </WorkoutStatistics>
    </Workout>
</HealthData>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(xml_content)
        xml_path = Path(f.name)

    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_f:
            db_path = Path(db_f.name)

        # Run parsing
        result = parse_apple_health(xml_path=xml_path, db_path=db_path)

        # Verify results
        assert "workouts_inserted" in result
        assert result["workouts_inserted"] >= 1

        # Check database
        conn = sqlite3.connect(str(db_path))
        workouts = conn.execute("SELECT * FROM activities WHERE source='apple_health'").fetchall()
        assert len(workouts) >= 1

        workout = workouts[0]
        assert workout[2] == "apple_health"  # source
        assert "Running" in workout[3]  # type

        conn.close()

    finally:
        xml_path.unlink(missing_ok=True)
        db_path.unlink(missing_ok=True)


def test_parse_apple_health_empty():
    """Test parsing empty Apple Health XML"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(xml_content)
        xml_path = Path(f.name)

    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_f:
            db_path = Path(db_f.name)

        result = parse_apple_health(xml_path=xml_path, db_path=db_path)
        assert result["workouts_inserted"] == 0

    finally:
        xml_path.unlink(missing_ok=True)
        db_path.unlink(missing_ok=True)
