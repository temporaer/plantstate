"""Integration tests for the API with persistence."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.routes import app, get_db
from backend.infrastructure.database import Base


@pytest.fixture
def client():
    """Create a test client with an in-memory SQLite database."""
    from sqlalchemy.pool import StaticPool

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


@pytest.fixture
def sample_plant():
    fixtures_path = Path(__file__).parent.parent / "fixtures.json"
    with open(fixtures_path) as f:
        plants = json.load(f)
    return plants[0]  # Feigenbaum


class TestPlantCRUD:
    def test_create_and_list(self, client, sample_plant):
        resp = client.post("/plants", json=sample_plant)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == "Feigenbaum"
        assert len(data["rules"]) == 2

        resp = client.get("/plants")
        assert resp.status_code == 200
        plants = resp.json()
        assert len(plants) == 1
        assert plants[0]["name"] == "Feigenbaum"

    def test_get_plant(self, client, sample_plant):
        create_resp = client.post("/plants", json=sample_plant)
        plant_id = create_resp.json()["id"]

        resp = client.get(f"/plants/{plant_id}")
        assert resp.status_code == 200
        assert resp.json()["botanical_name"] == "Ficus carica"

    def test_get_plant_not_found(self, client):
        resp = client.get("/plants/nonexistent")
        assert resp.status_code == 404

    def test_delete_plant(self, client, sample_plant):
        create_resp = client.post("/plants", json=sample_plant)
        plant_id = create_resp.json()["id"]

        resp = client.delete(f"/plants/{plant_id}")
        assert resp.status_code == 200

        resp = client.get(f"/plants/{plant_id}")
        assert resp.status_code == 404

    def test_create_all_fixtures(self, client):
        fixtures_path = Path(__file__).parent.parent / "fixtures.json"
        with open(fixtures_path) as f:
            plants = json.load(f)

        for plant_data in plants:
            resp = client.post("/plants", json=plant_data)
            assert resp.status_code == 200, f"Failed for {plant_data['name']}: {resp.text}"

        resp = client.get("/plants")
        assert len(resp.json()) == 7


class TestTaskActions:
    def test_complete_task(self, client, sample_plant):
        create_resp = client.post("/plants", json=sample_plant)
        assert create_resp.status_code == 200

        # Use weather that triggers relevant-now for early_spring rules
        weather = {
            "history": [
                {"date": f"2026-03-{25+i:02d}", "temp_min": 5.0, "temp_max": 15.0, "precipitation_mm": 0.0}
                for i in range(7)
            ],
            "forecast": [
                {"date": f"2026-04-{1+i:02d}", "temp_min": 8.0, "temp_max": 22.0, "precipitation_mm": 0.0}
                for i in range(5)
            ],
        }
        resp = client.post("/dashboard/relevant-now", json=weather)
        assert resp.status_code == 200

    def test_skip_task_not_found(self, client):
        resp = client.post("/tasks/nonexistent/skip")
        assert resp.status_code == 404


class TestRelevantNow:
    def test_relevant_now_empty_db(self, client):
        weather = {
            "history": [],
            "forecast": [
                {"date": f"2026-04-0{i+1}", "temp_min": 5.0, "temp_max": 15.0, "precipitation_mm": 0.0}
                for i in range(5)
            ],
        }
        resp = client.post("/dashboard/relevant-now", json=weather)
        assert resp.status_code == 200
        assert resp.json() == []
