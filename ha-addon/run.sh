#!/usr/bin/env bash
set -euo pipefail

echo "[plant-state] Starting add-on..."

# Read options from /data/options.json
if [ -f /data/options.json ]; then
    export HA_WEATHER_ENTITY=$(python3 -c "import json; print(json.load(open('/data/options.json')).get('weather_entity', 'weather.home'))")
    export HA_CALENDAR_ENTITY=$(python3 -c "import json; print(json.load(open('/data/options.json')).get('calendar_entity', 'calendar.garden'))")
    echo "[plant-state] weather=$HA_WEATHER_ENTITY calendar=$HA_CALENDAR_ENTITY"
fi

# Database in persistent /data/ directory
export DATABASE_URL="sqlite:////data/plant_state.db"

FIRST_RUN=false
if [ ! -f /data/plant_state.db ]; then
    FIRST_RUN=true
fi

# Start uvicorn in background
python3 -m uvicorn backend.api.routes:app \
    --host 0.0.0.0 \
    --port 8099 \
    --log-level info &
SERVER_PID=$!

# On first run, seed the database once the server is ready
if [ "$FIRST_RUN" = true ]; then
    echo "[plant-state] First run — waiting for server..."
    for i in $(seq 1 30); do
        if curl -sf http://localhost:8099/plants > /dev/null 2>&1; then
            echo "[plant-state] Server ready — seeding database..."
            python3 -m backend.seed http://localhost:8099 || echo "[plant-state] Seed failed (non-fatal)"
            break
        fi
        sleep 1
    done
fi

# Wait for server process (keeps container alive)
wait $SERVER_PID
