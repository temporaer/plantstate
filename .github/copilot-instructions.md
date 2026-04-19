# Copilot Instructions — Plant-State

## Project overview

Plant-State is a weather-driven garden lifecycle system that runs as a **Home Assistant add-on** (with a standalone Docker Compose mode for dev). It accepts plant configuration via LLM, evaluates lifecycle rules against DWD weather data from Home Assistant, manages tasks, syncs to an HA calendar, and exposes a passive UI.

## Architecture

```
backend/                  # Python / FastAPI
  domain/                 # Pure domain logic (models, enums, events, rules, tips)
  application/            # Service layer, LLM contract, JSON extraction
  infrastructure/         # HA adapter, SQLAlchemy repo, database models
  api/                    # FastAPI routes + lifespan (single file: routes.py)
  seed.py                 # Seed script (HTTP-based, posts to running API)
  tests/

frontend/                 # TypeScript / React + Vite
  src/
    api.ts                # API client (all backend calls)
    App.tsx               # HashRouter, MUI theme, tab navigation
    pages/                # DashboardPage, PlantListPage, PlantDetailPage
    theme.ts

ha-addon/                 # HA add-on assets
  config.yaml             # Add-on metadata (version, ingress, options schema)
  run.sh                  # Entrypoint: reads options.json, starts uvicorn, seeds on first run
  plant-state-card.js     # Custom Lovelace card

Dockerfile.addon          # Single-container multi-stage build (node → python)
docker-compose.yml        # Standalone dev mode (separate frontend/backend containers)
```

## Critical design principles

- **Domain logic is independent of Home Assistant.** HA is only a weather data source and calendar sync target.
- **No business logic in API routes or frontend.** Routes are thin wrappers around `PlantService`.
- **All lifecycle logic is deterministic and testable.** No fixed dates — all timing derives from weather events + seasons.
- **All LLM output is validated before persistence** (Pydantic strict models).

## Development environment

- **Conda env** `plant-state` at `/home/hannes/miniforge3`. Activate: `eval "$(conda shell.bash hook)" && conda activate plant-state`.
- **Proxmox deployment**: IP `192.168.1.176`, frontend port 3000, backend port 8000.
- **HA connection**: `https://haos.hsrpi.freeddns.org`, weather entity `weather.karlsruhe`, calendar `calendar.garden`.

## Build, lint, and test commands

```bash
# Backend
ruff check backend/                        # lint (must pass before commit)
python -m pytest backend/tests/ -x -q      # 87+ tests, all must pass

# Frontend
cd frontend && npm run build               # full build (tsc + vite) — MUST pass before commit

# Lovelace card JS
node -c ha-addon/plant-state-card.js       # syntax check — MUST pass before commit

# Docker (standalone dev)
docker compose up --build

# Add-on image (built by GitHub Actions, can test locally)
docker build -f Dockerfile.addon -t plant-state-addon .
```

## Version bumping (HA add-on)

**Every time you change backend or frontend code that should reach the HA add-on**, bump the version in `ha-addon/config.yaml`. HA only detects updates when this version string changes. Forget this and the user's add-on won't update.

The version in `ha-addon/config.yaml` is the **only** version that matters for the add-on. The `pyproject.toml` version is informational.

## Git workflow

- **Commit frequently** with small, focused commits.
- **Always run `ruff check backend/` and `python -m pytest backend/tests/ -x -q` before committing.**
- **Always run `node -c ha-addon/plant-state-card.js` before committing card changes.** A syntax error breaks the entire card registration in HA.
- **Always run `npm run build` in `frontend/` before committing frontend changes.** Do NOT rely on `tsc --noEmit` alone — it type-checks against locally installed packages, which may differ from what Docker installs. `npm run build` (tsc + vite) catches the same errors the Docker build will hit.
- Two GitHub accounts: `temporaer` (personal, for push) and `haschulz_microsoft` (EMU, default). Switch with `gh auth switch --user temporaer` before push, switch back after.
- GitHub Actions (`.github/workflows/addon-build.yml`) builds `Dockerfile.addon` on push to main and pushes to GHCR.

## Database

- SQLite, no Alembic yet.
- Schema created via `Base.metadata.create_all()` on startup.
- New columns added via **idempotent migration** in `lifespan()` (check `PRAGMA table_info`, then `ALTER TABLE ADD COLUMN` + backfill). See routes.py lifespan for the pattern.
- For **breaking** schema changes: `docker compose down -v` (dev) or delete `/data/plant_state.db` (add-on).

## HA add-on specifics

- **Ingress**: HA proxies requests through `/api/hassio_ingress/<token>/` → container port 8099. This is why the frontend uses `HashRouter` (not BrowserRouter) and Vite `base: "./"`.
- **Single process**: FastAPI serves both API and static frontend files (no nginx). The catch-all `/{full_path:path}` route at the end of routes.py serves `frontend_dist/`.
- **Supervisor API**: When `SUPERVISOR_TOKEN` env var exists (auto-set by HA), backend uses `http://supervisor/core` as HA URL. No manual token needed.
- **Options**: `/data/options.json` provides `weather_entity` and `calendar_entity`, configurable in HA UI.
- **GHCR**: Image at `ghcr.io/temporaer/plantstate-addon-{arch}`. Package must be public for HA to pull.

## Backend conventions

- **Pydantic strict models** in `domain/models.py` (ConfigDict strict=True).
- **Ruff rules**: `["E", "F", "I", "UP", "B", "SIM"]`, ignore `["B008"]` (FastAPI `Depends()` pattern).
- **Line length**: 99.
- Domain layer has **no imports from infrastructure or api**.
- Service layer (`application/services.py`) orchestrates domain logic and repository calls.
- Weather events are pure functions in `domain/events.py` — deterministic, testable, no I/O.
- LLM contract in `application/llm_contract.py`: system prompt, validation, conversion. LLM output must use only allowed `WeatherEventType` and `TaskType` enums.

## Frontend conventions

- **React + Vite + TypeScript + MUI + TanStack Query**.
- `HashRouter` (not BrowserRouter) for HA ingress compatibility.
- API base auto-detected: `import.meta.env.VITE_API_BASE ?? "/api"`. In add-on mode, set to `"."`.
- All API calls go through `frontend/src/api.ts`.
- German UI text (user preference), English enums.

## Adding a new plant (without breaking state)

Plants are additive — use the seed script or the UI's "Add Plant" dialog. The seed script is HTTP-based and idempotent (checks by name before inserting). Never drop/recreate the DB to add plants.

## Regenerating plants

Plants can be regenerated (re-interpreted by LLM) to pick up schema changes or improved rules.

### Via UI (requires HA conversation agent)
- **Single plant**: Plant detail page → "Neu generieren" button (picks an HA agent).
- **All plants**: Plant list page → "Alle neu generieren" button. Sequential LLM calls; can take 5-10 min for 20+ plants.

### Via API (no HA needed — direct JSON)
Use `PUT /plants/{id}/update-json` to update a single plant with pre-built JSON. Same schema as LLM output. Validates with Pydantic, then calls `regenerate_plant()` internally (preserves completed/skipped tasks, replaces rules + planned tasks).

```bash
# Example: generate JSON externally (e.g. ChatGPT, Claude), then POST
curl -X PUT "https://<ha>/api/hassio_ingress/<slug>/plants/<id>/update-json" \
  -H "Content-Type: application/json" \
  -d @plant.json
```

### Via HA conversation agent (API)
- `POST /plants/{id}/regenerate` — body: `{"plant_name": "...", "agent_id": "..."}`
- `POST /plants/regenerate-all` — body: `{"agent_id": "..."}`

### Getting the LLM prompt
Use `POST /plants/prompt` with `{"user_input": "Tomate"}` to get the full system prompt + user input, ready to paste into an external LLM. The response JSON can then be sent to `PUT /plants/{id}/update-json`.

### Regeneration preserves
- Completed and skipped tasks (history)
- Image URL (kept if new plant has none)
- Plant ID

### Regeneration replaces
- All rules
- All planned/active tasks
- Plant metadata (name, description, water_needs, fertilizer_needs, etc.)

## Allowed task types

`sow`, `transplant`, `harvest`, `prune_maintenance`, `prune_structural`, `cut_back`, `deadhead`, `thin_fruit`, `remove_deadwood`, `water`, `fertilize`

## Allowed weather events

`frost_risk_active`, `frost_risk_passed`, `sustained_mild_nights`, `warm_spell`, `heatwave`, `dry_spell`, `persistent_rain`

## Testing

Tests must run **without** Home Assistant. The test suite mocks weather data and HA responses. Contract tests validate LLM JSON schema. Keep tests fast and deterministic.
