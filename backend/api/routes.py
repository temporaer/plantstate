"""FastAPI application and routes."""

from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.application.llm_contract import (
    LLM_SYSTEM_PROMPT,
    llm_output_to_plant,
    validate_llm_output,
)
from backend.application.services import OutlookItem, PlantService, RelevantTask
from backend.domain.events import compute_all_events
from backend.domain.models import DailyWeather, Plant, WeatherData
from backend.domain.rules import get_current_season
from backend.domain.tips import get_tips
from backend.infrastructure.database import Base
from backend.infrastructure.ha_adapter import HomeAssistantAdapter

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///plant_state.db")

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

# HA config from environment
# HA add-on auto-detection: Supervisor API
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
if SUPERVISOR_TOKEN:
    HA_BASE_URL = os.environ.get("HA_BASE_URL", "http://supervisor/core")
    HA_TOKEN = SUPERVISOR_TOKEN
    # Read options from /data/options.json if available
    _options_path = Path("/data/options.json")
    if _options_path.exists():
        import json
        _options = json.loads(_options_path.read_text())
        HA_WEATHER_ENTITY = _options.get("weather_entity", "weather.home")
        HA_CALENDAR_ENTITY = _options.get("calendar_entity", "calendar.garden")
    else:
        HA_WEATHER_ENTITY = os.environ.get("HA_WEATHER_ENTITY", "weather.home")
        HA_CALENDAR_ENTITY = os.environ.get("HA_CALENDAR_ENTITY", "calendar.garden")
else:
    HA_BASE_URL = os.environ.get("HA_BASE_URL", "")
    HA_TOKEN = os.environ.get("HA_TOKEN", "")
    HA_WEATHER_ENTITY = os.environ.get("HA_WEATHER_ENTITY", "weather.karlsruhe")
    HA_CALENDAR_ENTITY = os.environ.get("HA_CALENDAR_ENTITY", "calendar.garden")


def _get_ha_adapter() -> HomeAssistantAdapter | None:
    if HA_BASE_URL and HA_TOKEN:
        return HomeAssistantAdapter(HA_BASE_URL, HA_TOKEN, HA_WEATHER_ENTITY)
    return None


# Keys must match what plant-state-card.js reads: t.task_id, t.plant_id,
# t.plant_name, t.task_type, t.urgency, t.priority, t.explanation_summary
SENSOR_TASK_KEYS = {
    "task_id", "plant_id", "plant_name", "task_type",
    "priority", "urgency", "explanation_summary",
}


def serialize_relevant_task(t: RelevantTask) -> dict[str, str]:
    """Serialize a RelevantTask for the HA sensor / Lovelace card."""
    return {
        "task_id": t.task.id,
        "plant_id": t.task.plant_id,
        "plant_name": t.plant.name,
        "task_type": t.rule.task_type.value,
        "priority": t.rule.priority.value,
        "urgency": t.urgency.value,
        "explanation_summary": t.rule.explanation.summary,
    }


async def _push_sensor_update() -> None:
    """Push current relevant tasks to HA sensor (fire-and-forget)."""
    import json
    import logging
    log = logging.getLogger("plant_state.sensor")
    try:
        adapter = _get_ha_adapter()
        if adapter is None:
            return
        db = SessionLocal()
        try:
            service = PlantService(db)
            weather = await adapter.fetch_weather_data()
            tasks = service.get_relevant_now(weather)
            task_dicts = [serialize_relevant_task(t) for t in tasks]
            await adapter.update_sensor(
                "sensor.garten_tasks",
                state=str(len(task_dicts)),
                attributes={
                    "friendly_name": "Garten Aufgaben",
                    "icon": "mdi:flower-tulip",
                    "unit_of_measurement": "Aufgaben",
                    "tasks": json.dumps(task_dicts),
                },
            )
            log.info("Sensor update (task change): %d tasks", len(task_dicts))
        finally:
            db.close()
    except Exception:
        log.exception("Sensor update after task change failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(engine)

    # Idempotent migration: add 'active' column if missing
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(
            __import__("sqlalchemy").text("PRAGMA table_info(plants)")
        )]
        if "active" not in cols:
            conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE plants ADD COLUMN active BOOLEAN DEFAULT 1"
                )
            )
            conn.execute(
                __import__("sqlalchemy").text(
                    "UPDATE plants SET active = 1 WHERE active IS NULL"
                )
            )
            conn.commit()

    # Idempotent migration: add water_needs/fertilizer_needs columns
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(
            __import__("sqlalchemy").text("PRAGMA table_info(plants)")
        )]
        if "water_needs" not in cols:
            conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE plants ADD COLUMN water_needs TEXT DEFAULT ''"
                )
            )
        if "fertilizer_needs" not in cols:
            conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE plants ADD COLUMN fertilizer_needs TEXT DEFAULT ''"
                )
            )
        conn.commit()

    # Start background scheduler for periodic calendar sync
    scheduler = None
    if HA_BASE_URL and HA_TOKEN:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        async def scheduled_calendar_sync() -> None:
            """Run calendar sync every 6 hours."""
            import logging
            log = logging.getLogger("plant_state.scheduler")
            try:
                db = SessionLocal()
                try:
                    service = PlantService(db)
                    adapter = _get_ha_adapter()
                    if adapter is None:
                        return
                    weather = await adapter.fetch_weather_data()
                    events = _build_calendar_events(service, weather)
                    created = await adapter.sync_to_calendar(HA_CALENDAR_ENTITY, events)
                    log.info("Calendar sync: %d new events (of %d relevant)", created, len(events))
                finally:
                    db.close()
            except Exception:
                log.exception("Calendar sync failed")

        scheduler = AsyncIOScheduler()
        scheduler.add_job(scheduled_calendar_sync, "interval", hours=6, id="calendar_sync")
        scheduler.add_job(_push_sensor_update, "interval", minutes=15, id="sensor_update")
        scheduler.add_job(_push_sensor_update, "date", id="sensor_update_boot")
        scheduler.start()

    yield

    if scheduler is not None:
        scheduler.shutdown()


app = FastAPI(title="Plant-State", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Session:  # type: ignore[misc]
    db = SessionLocal()
    try:
        yield db  # type: ignore[misc]
    finally:
        db.close()


def get_service(db: Session = Depends(get_db)) -> PlantService:
    return PlantService(db)


# --- Request models ---


class DailyWeatherInput(BaseModel):
    date: str
    temp_min: float
    temp_max: float
    precipitation_mm: float = 0.0


class WeatherDataInput(BaseModel):
    history: list[DailyWeatherInput] = Field(default_factory=list)
    forecast: list[DailyWeatherInput] = Field(default_factory=list)

    def to_domain(self) -> WeatherData:
        from datetime import date as date_type

        return WeatherData(
            history=[
                DailyWeather(
                    date=date_type.fromisoformat(d.date),
                    temp_min=d.temp_min,
                    temp_max=d.temp_max,
                    precipitation_mm=d.precipitation_mm,
                )
                for d in self.history
            ],
            forecast=[
                DailyWeather(
                    date=date_type.fromisoformat(d.date),
                    temp_min=d.temp_min,
                    temp_max=d.temp_max,
                    precipitation_mm=d.precipitation_mm,
                )
                for d in self.forecast
            ],
        )


class InterpretRequest(BaseModel):
    user_input: str


# --- Response models ---


class PlantResponse(BaseModel):
    id: str
    name: str
    botanical_name: str | None = None
    description: str = ""
    water_needs: str = ""
    fertilizer_needs: str = ""
    image_url: str | None = None
    language: str = "en"
    active: bool = True
    rules: list[dict] = Field(default_factory=list)


class TaskResponse(BaseModel):
    id: str
    plant_id: str
    rule_id: str
    task_type: str
    status: str
    year: int
    snoozed_until: str | None = None


class RelevantNowItem(BaseModel):
    task: TaskResponse
    plant_name: str
    task_type: str
    priority: str
    urgency: str
    explanation_summary: str
    explanation_why: str
    explanation_how: str


class WeatherStatusResponse(BaseModel):
    season: str
    events: dict[str, bool]
    forecast: list[dict]
    history: list[dict]


class OutlookItemResponse(BaseModel):
    task: TaskResponse
    plant_name: str
    task_type: str
    priority: str
    planning_seasons: list[str]
    explanation_summary: str
    in_planning_window: bool
    conditions_met: bool
    blocking: list[str]
    ready: bool


class TipResponse(BaseModel):
    icon: str
    title: str
    detail: str


# --- Routes ---


@app.post("/plants/interpret")
async def interpret_plant(body: InterpretRequest) -> dict:
    """Interpret a plant description via LLM. Returns the system prompt
    and expected schema so any LLM client can generate the structured output.

    In production, this would call an LLM API. For now, returns the contract
    so the caller (or a separate LLM service) can generate the JSON.
    """
    return {
        "system_prompt": LLM_SYSTEM_PROMPT,
        "user_input": body.user_input,
        "instruction": (
            "Send the system_prompt and user_input to your LLM. "
            "Validate the response JSON via POST /plants before saving."
        ),
    }


@app.post("/plants", response_model=PlantResponse)
def create_plant(
    body: dict[str, Any], service: PlantService = Depends(get_service)
) -> PlantResponse:
    """Create a plant from JSON (same schema as LLM output)."""
    validated = validate_llm_output(body)
    plant = llm_output_to_plant(validated)
    saved = service.add_plant(plant)
    return _plant_response(saved)


@app.get("/plants", response_model=list[PlantResponse])
def list_plants(service: PlantService = Depends(get_service)) -> list[PlantResponse]:
    plants = service.list_plants()
    return [_plant_response(p) for p in plants]


@app.get("/plants/{plant_id}", response_model=PlantResponse)
def get_plant(
    plant_id: str, service: PlantService = Depends(get_service)
) -> PlantResponse:
    plant = service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    return _plant_response(plant)


@app.delete("/plants/{plant_id}")
def delete_plant(
    plant_id: str, service: PlantService = Depends(get_service)
) -> dict:
    if not service.delete_plant(plant_id):
        raise HTTPException(status_code=404, detail="Plant not found")
    return {"status": "deleted"}


class SetActiveBody(BaseModel):
    active: bool


@app.patch("/plants/{plant_id}/active", response_model=PlantResponse)
def set_plant_active(
    plant_id: str, body: SetActiveBody, service: PlantService = Depends(get_service)
) -> PlantResponse:
    plant = service.set_plant_active(plant_id, body.active)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    return _plant_response(plant)


@app.get("/ha/agents")
async def list_ha_agents() -> list[dict]:
    """List available HA conversation agents."""
    adapter = _get_ha_adapter()
    if adapter is None:
        return []
    return await adapter.list_conversation_agents()


class GenerateRequest(BaseModel):
    plant_name: str
    agent_id: str


@app.post("/plants/generate")
async def generate_plant(body: GenerateRequest) -> dict:
    """Generate plant config via HA conversation agent."""
    adapter = _get_ha_adapter()
    if adapter is None:
        raise HTTPException(status_code=503, detail="Home Assistant not connected")

    combined = f"{LLM_SYSTEM_PROMPT}\n\n---\n\nPlant: {body.plant_name}"
    raw_response = await adapter.conversation_process(body.agent_id, combined)
    if raw_response is None:
        raise HTTPException(status_code=502, detail="No response from HA agent")

    from backend.application.json_extract import extract_json
    plant_json = extract_json(raw_response)
    if plant_json is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Could not extract valid JSON from agent response",
                "raw_response": raw_response[:2000],
            },
        )

    # Validate against our schema
    try:
        validated = validate_llm_output(plant_json)
        return validated.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": f"JSON does not match plant schema: {e}",
                "raw_json": plant_json,
            },
        ) from e


@app.post("/plants/prompt")
async def get_plant_prompt(body: InterpretRequest) -> dict:
    """Get a ready-to-paste prompt for external LLMs (ChatGPT etc)."""
    combined = f"""{LLM_SYSTEM_PROMPT}

---

Generate the lifecycle JSON for this plant: {body.user_input}

Output ONLY the JSON, no additional text."""
    return {
        "system_prompt": LLM_SYSTEM_PROMPT,
        "user_input": body.user_input,
        "combined_prompt": combined,
    }


@app.post("/plants/{plant_id}/regenerate", response_model=PlantResponse)
async def regenerate_plant(
    plant_id: str,
    body: GenerateRequest,
    service: PlantService = Depends(get_service),
) -> PlantResponse:
    """Re-generate a plant's rules via LLM, preserving completed task history."""
    existing = service.get_plant(plant_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    adapter = _get_ha_adapter()
    if adapter is None:
        raise HTTPException(status_code=503, detail="Home Assistant not connected")

    combined = f"{LLM_SYSTEM_PROMPT}\n\n---\n\nPlant: {body.plant_name}"
    raw_response = await adapter.conversation_process(body.agent_id, combined)
    if raw_response is None:
        raise HTTPException(status_code=502, detail="No response from HA agent")

    from backend.application.json_extract import extract_json
    plant_json = extract_json(raw_response)
    if plant_json is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Could not extract valid JSON from agent response",
                "raw_response": raw_response[:2000],
            },
        )

    try:
        validated = validate_llm_output(plant_json)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail={"error": f"JSON does not match plant schema: {e}", "raw_json": plant_json},
        ) from e

    new_plant = llm_output_to_plant(validated)
    updated = service.regenerate_plant(plant_id, new_plant)
    if updated is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    return _plant_response(updated)


class RegenerateAllRequest(BaseModel):
    agent_id: str


class RegenerateAllResult(BaseModel):
    total: int
    succeeded: int
    failed: list[dict]


@app.post("/plants/regenerate-all", response_model=RegenerateAllResult)
async def regenerate_all_plants(
    body: RegenerateAllRequest,
    service: PlantService = Depends(get_service),
) -> RegenerateAllResult:
    """Re-generate all active plants via LLM sequentially."""
    import logging
    log = logging.getLogger("plant_state.regenerate")
    adapter = _get_ha_adapter()
    if adapter is None:
        raise HTTPException(status_code=503, detail="Home Assistant not connected")

    plants = service.list_plants()
    active_plants = [p for p in plants if p.active]
    log.info("Regenerate-all: %d active plants, agent=%s", len(active_plants), body.agent_id)
    succeeded = 0
    failed: list[dict] = []

    for plant in active_plants:
        try:
            log.info("Regenerating: %s", plant.name)
            combined = f"{LLM_SYSTEM_PROMPT}\n\n---\n\nPlant: {plant.name}"
            raw_response = await adapter.conversation_process(body.agent_id, combined)
            if raw_response is None:
                log.warning("No response for %s", plant.name)
                failed.append({"name": plant.name, "error": "No response from agent"})
                continue

            from backend.application.json_extract import extract_json
            plant_json = extract_json(raw_response)
            if plant_json is None:
                log.warning("No JSON for %s: %s", plant.name, raw_response[:200])
                failed.append({"name": plant.name, "error": "Could not extract JSON"})
                continue

            validated = validate_llm_output(plant_json)
            new_plant = llm_output_to_plant(validated)
            service.regenerate_plant(plant.id, new_plant)
            succeeded += 1
            log.info("Regenerated: %s (%d rules)", plant.name, len(new_plant.rules))
        except Exception as e:
            log.exception("Failed to regenerate %s", plant.name)
            failed.append({"name": plant.name, "error": str(e)})

    log.info("Regenerate-all done: %d/%d succeeded", succeeded, len(active_plants))
    return RegenerateAllResult(
        total=len(active_plants), succeeded=succeeded, failed=failed,
    )


@app.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: str, bg: BackgroundTasks, service: PlantService = Depends(get_service)
) -> TaskResponse:
    task = service.complete_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    bg.add_task(_push_sensor_update)
    return _task_response(task)


@app.post("/tasks/{task_id}/skip", response_model=TaskResponse)
def skip_task(
    task_id: str, bg: BackgroundTasks, service: PlantService = Depends(get_service)
) -> TaskResponse:
    task = service.skip_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    bg.add_task(_push_sensor_update)
    return _task_response(task)


@app.post("/tasks/{task_id}/snooze", response_model=TaskResponse)
def snooze_task(
    task_id: str,
    days: int = 14,
    bg: BackgroundTasks = BackgroundTasks(),
    service: PlantService = Depends(get_service),
) -> TaskResponse:
    task = service.snooze_task(task_id, days=days)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    bg.add_task(_push_sensor_update)
    return _task_response(task)


@app.post("/dashboard/relevant-now", response_model=list[RelevantNowItem])
def get_relevant_now(
    weather_input: WeatherDataInput,
    service: PlantService = Depends(get_service),
) -> list[RelevantNowItem]:
    weather_data = weather_input.to_domain()
    results = service.get_relevant_now(weather_data)
    return [_relevant_item(r) for r in results]


@app.get("/dashboard/weather", response_model=WeatherStatusResponse)
async def get_weather_status() -> WeatherStatusResponse:
    """Fetch current weather from HA and compute event state."""
    adapter = _get_ha_adapter()
    if adapter is None:
        raise HTTPException(status_code=503, detail="Home Assistant not configured")
    weather = await adapter.fetch_weather_data()
    events = compute_all_events(weather)
    season = get_current_season()
    return WeatherStatusResponse(
        season=season.value,
        events={
            "frost_risk_active": events.frost_risk_active,
            "frost_risk_passed": events.frost_risk_passed,
            "sustained_mild_nights": events.sustained_mild_nights,
            "warm_spell": events.warm_spell,
            "heatwave": events.heatwave,
            "dry_spell": events.dry_spell,
            "persistent_rain": events.persistent_rain,
        },
        forecast=[
            {
                "date": str(d.date), "temp_min": d.temp_min,
                "temp_max": d.temp_max, "precipitation_mm": d.precipitation_mm,
            }
            for d in weather.forecast
        ],
        history=[
            {
                "date": str(d.date), "temp_min": d.temp_min,
                "temp_max": d.temp_max, "precipitation_mm": d.precipitation_mm,
            }
            for d in weather.history
        ],
    )


@app.get("/dashboard/tips", response_model=list[TipResponse])
async def get_garden_tips() -> list[TipResponse]:
    """Get contextual garden tips based on current season and weather."""
    adapter = _get_ha_adapter()
    if adapter is None:
        raise HTTPException(
            status_code=503, detail="Home Assistant not configured",
        )
    weather = await adapter.fetch_weather_data()
    events = compute_all_events(weather)
    season = get_current_season()
    tips = get_tips(season, events)
    return [
        TipResponse(icon=t.icon, title=t.title, detail=t.detail)
        for t in tips
    ]


@app.get("/dashboard/relevant-now-live", response_model=list[RelevantNowItem])
async def get_relevant_now_live(
    service: PlantService = Depends(get_service),
) -> list[RelevantNowItem]:
    """Fetch weather from HA and compute relevant tasks in one call."""
    adapter = _get_ha_adapter()
    if adapter is None:
        raise HTTPException(status_code=503, detail="Home Assistant not configured")
    weather = await adapter.fetch_weather_data()
    results = service.get_relevant_now(weather)
    return [_relevant_item(r) for r in results]


def _outlook_response(item: OutlookItem) -> OutlookItemResponse:
    return OutlookItemResponse(
        task=_task_response(item.task),
        plant_name=item.plant.name,
        task_type=item.rule.task_type.value,
        priority=item.rule.priority.value,
        planning_seasons=[s.value for s in item.rule.planning_seasons],
        explanation_summary=item.rule.explanation.summary,
        in_planning_window=item.in_planning_window,
        conditions_met=item.conditions_met,
        blocking=item.blocking,
        ready=item.in_planning_window and item.conditions_met,
    )


@app.get(
    "/dashboard/outlook",
    response_model=list[OutlookItemResponse],
)
async def get_outlook(
    service: PlantService = Depends(get_service),
) -> list[OutlookItemResponse]:
    """Yearly outlook: all tasks with season and readiness info."""
    adapter = _get_ha_adapter()
    if adapter is None:
        raise HTTPException(
            status_code=503, detail="Home Assistant not configured",
        )
    weather = await adapter.fetch_weather_data()
    items = service.get_outlook(weather)
    return [_outlook_response(i) for i in items]


@app.post(
    "/dashboard/outlook",
    response_model=list[OutlookItemResponse],
)
def get_outlook_with_weather(
    weather_input: WeatherDataInput,
    service: PlantService = Depends(get_service),
) -> list[OutlookItemResponse]:
    """Outlook with explicit weather data (for testing without HA)."""
    weather_data = weather_input.to_domain()
    items = service.get_outlook(weather_data)
    return [_outlook_response(i) for i in items]


# German task type labels for calendar events
_TASK_TYPE_DE: dict[str, str] = {
    "sow": "Aussaat",
    "transplant": "Auspflanzen",
    "harvest": "Ernte",
    "prune_maintenance": "Pflegeschnitt",
    "prune_structural": "Formschnitt",
    "cut_back": "Rückschnitt",
    "deadhead": "Verblühtes entfernen",
    "thin_fruit": "Fruchtausdünnung",
    "remove_deadwood": "Totholz entfernen",
}


def _build_calendar_events(
    service: PlantService, weather: WeatherData,
) -> list[dict]:
    """Build calendar event dicts from relevant-now tasks."""
    results = service.get_relevant_now(weather)
    today = date.today()
    events = []
    for r in results:
        task_label = _TASK_TYPE_DE.get(r.rule.task_type.value, r.rule.task_type.value)
        events.append({
            "summary": f"{task_label}: {r.plant.name}",
            "description": (
                f"{r.rule.explanation.summary}\n\n"
                f"Warum: {r.rule.explanation.why}\n\n"
                f"Wie: {r.rule.explanation.how}"
            ),
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat(),
        })
    return events


@app.post("/sync/calendar")
async def sync_calendar(
    service: PlantService = Depends(get_service),
) -> dict:
    """Sync active tasks to HA calendar (idempotent)."""
    adapter = _get_ha_adapter()
    if adapter is None:
        raise HTTPException(status_code=503, detail="Home Assistant not configured")
    weather = await adapter.fetch_weather_data()
    events = _build_calendar_events(service, weather)
    created = await adapter.sync_to_calendar(HA_CALENDAR_ENTITY, events)
    return {"synced": created, "total_relevant": len(events), "calendar": HA_CALENDAR_ENTITY}


# --- Helpers ---


def _plant_response(plant: Plant) -> PlantResponse:
    return PlantResponse(
        id=plant.id,
        name=plant.name,
        botanical_name=plant.botanical_name,
        description=plant.description,
        water_needs=plant.water_needs,
        fertilizer_needs=plant.fertilizer_needs,
        image_url=plant.image_url,
        language=plant.language,
        active=plant.active,
        rules=[r.model_dump(mode="json") for r in plant.rules],
    )


def _task_response(task: Any) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        plant_id=task.plant_id,
        rule_id=task.rule_id,
        task_type=task.task_type.value,
        status=task.status.value,
        year=task.year,
        snoozed_until=str(task.snoozed_until) if task.snoozed_until else None,
    )


def _relevant_item(r: RelevantTask) -> RelevantNowItem:
    return RelevantNowItem(
        task=_task_response(r.task),
        plant_name=r.plant.name,
        task_type=r.task.task_type.value,
        priority=r.rule.priority.value,
        urgency=r.urgency.value,
        explanation_summary=r.rule.explanation.summary,
        explanation_why=r.rule.explanation.why,
        explanation_how=r.rule.explanation.how,
    )


# --- Image proxy with disk cache ---

IMAGE_CACHE_DIR = Path(os.environ.get("IMAGE_CACHE_DIR", "/tmp/plant-state-images"))
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}

# Limit concurrent outbound image fetches to avoid Wikipedia rate-limits
_image_fetch_semaphore: asyncio.Semaphore | None = None


def _get_image_semaphore() -> asyncio.Semaphore:
    global _image_fetch_semaphore  # noqa: PLW0603
    if _image_fetch_semaphore is None:
        _image_fetch_semaphore = asyncio.Semaphore(2)
    return _image_fetch_semaphore


@app.get("/images/proxy")
async def proxy_image(url: str) -> FileResponse:
    """Proxy and cache external images to avoid rate limits."""
    if not url.startswith("https://upload.wikimedia.org/"):
        raise HTTPException(status_code=400, detail="Only Wikimedia URLs allowed")

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    suffix = Path(url.split("?")[0]).suffix or ".jpg"
    cache_path = IMAGE_CACHE_DIR / f"{url_hash}{suffix}"

    if not cache_path.exists():
        async with _get_image_semaphore():
            # Re-check after acquiring semaphore (another request may have cached it)
            if not cache_path.exists():
                last_error: str = ""
                for attempt in range(3):
                    try:
                        async with httpx.AsyncClient(
                            timeout=15, follow_redirects=True,
                        ) as client:
                            resp = await client.get(
                                url, headers={
                                    "User-Agent": "Mozilla/5.0 (compatible; PlantState/1.0)",
                                },
                            )
                            if resp.status_code == 429 and attempt < 2:
                                await asyncio.sleep(2 ** attempt)
                                continue
                            resp.raise_for_status()
                            cache_path.write_bytes(resp.content)
                            break
                    except httpx.HTTPError as e:
                        last_error = str(e)
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)
                else:
                    raise HTTPException(
                        status_code=502, detail=f"Image fetch failed: {last_error}",
                    ) from None

    media_type = MIME_MAP.get(suffix.lower(), "image/jpeg")
    return FileResponse(
        cache_path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=604800"},
    )


# --- Lovelace card JS served from add-on (auto-updates with add-on) ---
_CARD_JS = Path(__file__).resolve().parent.parent.parent / "ha-addon" / "plant-state-card.js"
if not _CARD_JS.exists():
    _CARD_JS = Path("/app/ha-addon/plant-state-card.js")


@app.get("/plant-state-card.js", include_in_schema=False)
async def _serve_card_js() -> FileResponse:
    if _CARD_JS.exists():
        return FileResponse(
            _CARD_JS,
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )
    raise HTTPException(status_code=404, detail="Card JS not found")


# --- Static file serving for HA add-on mode (single process) ---
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend_dist"
if not _FRONTEND_DIR.exists():
    _FRONTEND_DIR = Path("/app/frontend_dist")

if _FRONTEND_DIR.exists():
    # SPA fallback: serve index.html for any non-API, non-file route
    _index_html = _FRONTEND_DIR / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str) -> FileResponse:
        file_path = _FRONTEND_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            suffix = file_path.suffix.lower()
            ct = {
                ".js": "application/javascript",
                ".css": "text/css",
                ".html": "text/html",
                ".json": "application/json",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".ico": "image/x-icon",
                ".woff": "font/woff",
                ".woff2": "font/woff2",
            }.get(suffix, "application/octet-stream")
            return FileResponse(file_path, media_type=ct)
        return FileResponse(_index_html, media_type="text/html")
