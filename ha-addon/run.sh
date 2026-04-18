#!/usr/bin/env bash
set -euo pipefail

echo "[plant-state] Starting add-on..."

# Auto-deploy Lovelace card JS to HA's www directory
mkdir -p /config/www
cp /app/ha-addon/plant-state-card.js /config/www/plant-state-card.js
echo "[plant-state] Lovelace card JS updated in /config/www/"

# Auto-update Lovelace resource cache buster via HA API
CARD_HASH=$(md5sum /config/www/plant-state-card.js | cut -c1-8)
CARD_URL="/local/plant-state-card.js?v=${CARD_HASH}"
if [ -n "${SUPERVISOR_TOKEN:-}" ]; then
    echo "[plant-state] Updating Lovelace resource to ${CARD_URL}"
    # List existing resources
    RESOURCES=$(curl -sf -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
        http://supervisor/core/api/lovelace/resources 2>/dev/null || echo "[]")
    # Find our resource ID
    RES_ID=$(echo "$RESOURCES" | python3 -c "
import sys, json
for r in json.load(sys.stdin):
    if 'plant-state-card' in r.get('url', ''):
        print(r['id']); break
" 2>/dev/null || true)
    if [ -n "$RES_ID" ]; then
        # Update existing resource
        curl -sf -X PATCH \
            -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"url\": \"${CARD_URL}\"}" \
            "http://supervisor/core/api/lovelace/resources/${RES_ID}" > /dev/null 2>&1 \
            && echo "[plant-state] Resource ${RES_ID} updated" \
            || echo "[plant-state] Failed to update resource (non-fatal)"
    else
        # Create new resource
        curl -sf -X POST \
            -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"url\": \"${CARD_URL}\", \"res_type\": \"module\"}" \
            "http://supervisor/core/api/lovelace/resources" > /dev/null 2>&1 \
            && echo "[plant-state] Resource created" \
            || echo "[plant-state] Failed to create resource (non-fatal)"
    fi
else
    echo "[plant-state] No SUPERVISOR_TOKEN — skipping resource update"
fi

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
