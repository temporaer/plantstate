"""Seed script: load fixture plants into the database via the API.

Usage:
  python -m backend.seed              # Add new plants only (safe, preserves state)
  python -m backend.seed --reset      # Delete all and re-seed from scratch
"""

import json
import sys
from pathlib import Path

import httpx

API_BASE = "http://localhost:8000"
FIXTURES = Path(__file__).parent / "tests" / "fixtures.json"


def main() -> None:
    reset = "--reset" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    api_base = args[0] if args else API_BASE

    with open(FIXTURES) as f:
        plants = json.load(f)

    with httpx.Client(base_url=api_base, timeout=30) as client:
        existing = client.get("/plants").json()
        existing_names = {p["name"] for p in existing}

        if reset:
            for p in existing:
                client.delete(f"/plants/{p['id']}")
            if existing:
                print(f"  🗑️  Deleted {len(existing)} existing plants")
            existing_names = set()

        added = 0
        skipped = 0
        for plant_data in plants:
            if plant_data["name"] in existing_names:
                skipped += 1
                continue
            resp = client.post("/plants", json=plant_data)
            if resp.status_code == 200:
                name = resp.json()["name"]
                rules = len(resp.json()["rules"])
                print(f"  ✅ {name} ({rules} rules)")
                added += 1
            else:
                print(f"  ❌ {plant_data['name']}: {resp.status_code} {resp.text}")

    print(f"\nDone: {added} added, {skipped} skipped (already exist)")


if __name__ == "__main__":
    main()
