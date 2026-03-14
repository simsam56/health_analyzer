"""
Pytest configuration for Bord tests
"""

import tempfile
from pathlib import Path

import pytest

from pipeline.schema import init_db


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_f:
        db_path = Path(db_f.name)

    # Initialize schema
    conn = init_db(db_path)
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def sample_apple_xml():
    """Sample Apple Health XML for testing"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
             startDate="2024-01-01T10:00:00Z"
             endDate="2024-01-01T11:00:00Z"
             duration="3600.0"
             totalDistance="10000"
             totalEnergyBurned="500">
    </Workout>
</HealthData>"""
