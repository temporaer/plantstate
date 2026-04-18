# 🌱 Plant-State — Garden Lifecycle Manager

A weather-driven garden task planner that integrates with Home Assistant.

## Features

- **29 plants** with lifecycle rules (pruning, harvesting, sowing, etc.)
- **Weather-based activation** — tasks become relevant based on DWD forecast data
- **Priority & urgency** — smart sorting by importance and time pressure
- **Calendar sync** — pushes relevant tasks to a Home Assistant calendar
- **Passive UI** — dashboard, yearly outlook, contextual tips

## Architecture

```
backend/    Python (FastAPI, SQLAlchemy, Pydantic)
frontend/   TypeScript (React, Vite, MUI, TanStack Query)
```

Domain logic is independent of Home Assistant.  
HA is only used as a weather data source and calendar sync target.

## Deployment (Proxmox / any Docker host)

### 1. Clone and configure

```bash
git clone <repo-url> plant-state
cd plant-state

# Create .env with your HA connection details
cat > .env <<EOF
HA_BASE_URL=https://your-ha-instance.local:8123
HA_TOKEN=your_long_lived_access_token
HA_WEATHER_ENTITY=weather.karlsruhe
HA_CALENDAR_ENTITY=calendar.garden
EOF
```

### 2. Start with Docker Compose

```bash
docker compose up -d --build
```

This starts:
- **Backend** on port `8000` (FastAPI + SQLite + APScheduler)
- **Frontend** on port `3000` (nginx serving React SPA, proxying `/api` to backend)

### 3. Seed the database

```bash
docker compose exec backend python -m backend.seed
```

### 4. Verify

- UI: `http://<host>:3000`
- API: `http://<host>:8000/docs`
- Health: `http://<host>:8000/dashboard/weather`

## Home Assistant Integration

### Calendar Entity

Create a local calendar in HA called `garden`:

1. **Settings → Devices & Services → Add Integration → Local Calendar**
2. Name it `garden` (entity: `calendar.garden`)

Tasks are synced automatically every 6 hours via APScheduler,  
or manually via `POST /api/sync/calendar`.

### Iframe Panel (optional)

Add the Plant-State UI as a sidebar panel in HA:

```yaml
# configuration.yaml
panel_iframe:
  plant_state:
    title: "Garten"
    icon: mdi:flower
    url: "http://<plant-state-host>:3000"
    require_admin: false
```

### Long-Lived Access Token

1. Go to your HA profile (bottom-left)
2. Scroll to **Long-Lived Access Tokens**
3. Create one and put it in `.env` as `HA_TOKEN`

## Development

### Prerequisites

- [Miniforge/Mamba](https://github.com/conda-forge/miniforge)

```bash
mamba env create -f environment.yml
conda activate plant-state
```

### Run locally (without Docker)

```bash
# Backend
uvicorn backend.api.routes:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

### Tests

```bash
python -m pytest backend/tests/ -q
```

## Background Sync

APScheduler runs inside the backend container:
- **Calendar sync**: every 6 hours — pushes relevant tasks to `calendar.garden`
- Idempotent — checks existing events before creating new ones
- Manual trigger: `POST /api/sync/calendar`
