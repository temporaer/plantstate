"""Seed script: load fixture plants into the database via the API."""

import json
import sys
from pathlib import Path

import httpx

API_BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
FIXTURES = Path(__file__).parent / "tests" / "fixtures.json"


def main() -> None:
    with open(FIXTURES) as f:
        plants = json.load(f)

    with httpx.Client(base_url=API_BASE, timeout=30) as client:
        # Delete existing plants first (idempotent re-seed)
        existing = client.get("/plants").json()
        for p in existing:
            client.delete(f"/plants/{p['id']}")
        if existing:
            print(f"  🗑️  Deleted {len(existing)} existing plants")

        for plant_data in plants:
            resp = client.post("/plants", json=plant_data)
            if resp.status_code == 200:
                name = resp.json()["name"]
                rules = len(resp.json()["rules"])
                print(f"  ✅ {name} ({rules} rules)")
            else:
                print(f"  ❌ {plant_data['name']}: {resp.status_code} {resp.text}")

    print(f"\nSeeded {len(plants)} plants to {API_BASE}")


if __name__ == "__main__":
    main()
