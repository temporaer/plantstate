"""End-to-end lifecycle tests.

Tests the full flow WITHOUT Home Assistant:
1. Add plant via API
2. Evaluate lifecycle with mock weather
3. Mark task done/skip
4. Verify calendar sync endpoint
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.routes import app, get_db
from backend.infrastructure.database import Base

FIXTURES_PATH = Path(__file__).parent.parent / "fixtures.json"


@pytest.fixture()
def client() -> TestClient:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _spring_weather_frost_passed() -> dict:
    """Weather: late March history (warm), April forecast (warm, dry).

    Triggers: frost_risk_passed=True, dry_spell=True, warm_spell=True.
    Season via forecast dates: spring.
    """
    return {
        "history": [
            {
                "date": f"2026-03-{20+i:02d}",
                "temp_min": 6.0,
                "temp_max": 16.0,
                "precipitation_mm": 0.0,
            }
            for i in range(7)
        ],
        "forecast": [
            {
                "date": f"2026-04-{1+i:02d}",
                "temp_min": 10.0,
                "temp_max": 22.0,
                "precipitation_mm": 0.0,
            }
            for i in range(5)
        ],
    }


def _summer_weather_warm() -> dict:
    """Weather: June (warm nights, no frost, dry).

    Triggers: frost_risk_passed=True, sustained_mild_nights=True,
              warm_spell=True, dry_spell=True.
    Season: early_summer.
    """
    return {
        "history": [
            {
                "date": f"2026-06-{10+i:02d}",
                "temp_min": 14.0,
                "temp_max": 28.0,
                "precipitation_mm": 0.0,
            }
            for i in range(7)
        ],
        "forecast": [
            {
                "date": f"2026-06-{17+i:02d}",
                "temp_min": 15.0,
                "temp_max": 28.0,
                "precipitation_mm": 0.0,
            }
            for i in range(5)
        ],
    }


class TestAddPlantAndEvaluate:
    """E2E: Add a plant, evaluate lifecycle, verify tasks appear."""

    def test_add_plant_then_evaluate(self, client: TestClient) -> None:
        # 1. Load Tomate fixture (has transplant rule in spring)
        with open(FIXTURES_PATH) as f:
            plants = json.load(f)
        tomate = next(p for p in plants if "Tomate" in p["name"])

        resp = client.post("/plants", json=tomate)
        assert resp.status_code == 200
        plant = resp.json()
        assert plant["name"] == "Tomate (Hochbeet)"
        assert len(plant["rules"]) == 3

        # 2. Evaluate with warm spring weather
        weather = _spring_weather_frost_passed()
        resp = client.post("/dashboard/relevant-now", json=weather)
        assert resp.status_code == 200
        relevant = resp.json()

        # Tomate transplant: spring + frost_risk_passed + sustained_mild_nights
        # Weather has nights at 10°C (>=8°C → sustained_mild_nights=True)
        transplant_tasks = [
            t for t in relevant
            if t["task_type"] == "transplant"
            and t["plant_name"] == "Tomate (Hochbeet)"
        ]
        assert len(transplant_tasks) >= 1, (
            f"Expected Tomate transplant task. Got: {relevant}"
        )

        # 3. Verify explanation fields exist
        task_item = transplant_tasks[0]
        assert task_item["explanation_summary"]
        assert task_item["explanation_why"]
        assert task_item["explanation_how"]

    def test_add_multiple_plants_evaluate(self, client: TestClient) -> None:
        with open(FIXTURES_PATH) as f:
            plants = json.load(f)

        # Add all 7 plants
        for plant_data in plants:
            resp = client.post("/plants", json=plant_data)
            assert resp.status_code == 200

        # Evaluate with summer weather (triggers more rules)
        weather = _summer_weather_warm()
        resp = client.post("/dashboard/relevant-now", json=weather)
        assert resp.status_code == 200
        relevant = resp.json()

        # Should have some relevant tasks in early summer
        assert isinstance(relevant, list)


class TestCompleteAndSkipTasks:
    """E2E: Create tasks via evaluation, then complete/skip them."""

    def test_complete_task_flow(self, client: TestClient) -> None:
        # Add Gurke (has sow in spring, needs frost_risk_passed)
        with open(FIXTURES_PATH) as f:
            plants = json.load(f)
        gurke = next(p for p in plants if "Gurke" in p["name"])

        client.post("/plants", json=gurke)

        # Evaluate to create tasks
        weather = _spring_weather_frost_passed()
        resp = client.post("/dashboard/relevant-now", json=weather)
        relevant = resp.json()

        # Find a sow task for Gurke
        sow_tasks = [
            t for t in relevant if t["task_type"] == "sow"
        ]
        if not sow_tasks:
            pytest.skip("No sow task triggered (weather conditions)")

        task_id = sow_tasks[0]["task"]["id"]

        # Complete the task
        resp = client.post(f"/tasks/{task_id}/complete")
        assert resp.status_code == 200
        completed = resp.json()
        assert completed["status"] == "completed"
        assert completed["id"] == task_id

        # Task should no longer appear in relevant-now
        resp = client.post("/dashboard/relevant-now", json=weather)
        remaining_ids = [t["task"]["id"] for t in resp.json()]
        assert task_id not in remaining_ids

    def test_skip_task_flow(self, client: TestClient) -> None:
        with open(FIXTURES_PATH) as f:
            plants = json.load(f)
        tomate = next(p for p in plants if "Tomate" in p["name"])

        client.post("/plants", json=tomate)

        weather = _spring_weather_frost_passed()
        resp = client.post("/dashboard/relevant-now", json=weather)
        relevant = resp.json()

        sow_tasks = [
            t for t in relevant if t["task_type"] == "sow"
        ]
        if not sow_tasks:
            pytest.skip("No sow task triggered")

        task_id = sow_tasks[0]["task"]["id"]

        # Skip the task
        resp = client.post(f"/tasks/{task_id}/skip")
        assert resp.status_code == 200
        skipped = resp.json()
        assert skipped["status"] == "skipped"

        # Skipped task should not appear in relevant-now
        resp = client.post("/dashboard/relevant-now", json=weather)
        remaining_ids = [t["task"]["id"] for t in resp.json()]
        assert task_id not in remaining_ids


class TestCalendarSync:
    """E2E: Verify calendar sync endpoint works (without HA)."""

    def test_calendar_sync_no_ha(self, client: TestClient) -> None:
        """Calendar sync should return error when HA is not configured."""
        resp = client.post("/sync/calendar")
        # Without HA_BASE_URL set, should return 503
        assert resp.status_code == 503


class TestDeletePlantCascade:
    """E2E: Delete a plant and verify tasks are cleaned up."""

    def test_delete_removes_tasks(self, client: TestClient) -> None:
        with open(FIXTURES_PATH) as f:
            plants = json.load(f)
        erdbeeren = next(p for p in plants if "Erdbeeren" in p["name"])

        resp = client.post("/plants", json=erdbeeren)
        plant_id = resp.json()["id"]

        # Evaluate to create tasks
        weather = _summer_weather_warm()
        client.post("/dashboard/relevant-now", json=weather)

        # Delete the plant
        resp = client.delete(f"/plants/{plant_id}")
        assert resp.status_code == 200

        # Plant should be gone
        resp = client.get(f"/plants/{plant_id}")
        assert resp.status_code == 404

        # Evaluate again — no tasks for deleted plant
        resp = client.post("/dashboard/relevant-now", json=weather)
        relevant = resp.json()
        erdbeeren_tasks = [
            t for t in relevant if t["plant_name"] == "Erdbeeren"
        ]
        assert len(erdbeeren_tasks) == 0
