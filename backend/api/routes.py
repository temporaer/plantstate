"""FastAPI application and routes."""

from __future__ import annotations

import hashlib
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException
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
HA_BASE_URL = os.environ.get("HA_BASE_URL", "")
HA_TOKEN = os.environ.get("HA_TOKEN", "")
HA_WEATHER_ENTITY = os.environ.get("HA_WEATHER_ENTITY", "weather.karlsruhe")
HA_CALENDAR_ENTITY = os.environ.get("HA_CALENDAR_ENTITY", "calendar.garden")


def _get_ha_adapter() -> HomeAssistantAdapter | None:
    if HA_BASE_URL and HA_TOKEN:
        return HomeAssistantAdapter(HA_BASE_URL, HA_TOKEN, HA_WEATHER_ENTITY)
    return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(engine)

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
    image_url: str | None = None
    language: str = "en"
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


@app.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: str, service: PlantService = Depends(get_service)
) -> TaskResponse:
    task = service.complete_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_response(task)


@app.post("/tasks/{task_id}/skip", response_model=TaskResponse)
def skip_task(
    task_id: str, service: PlantService = Depends(get_service)
) -> TaskResponse:
    task = service.skip_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_response(task)


@app.post("/tasks/{task_id}/snooze", response_model=TaskResponse)
def snooze_task(
    task_id: str,
    days: int = 14,
    service: PlantService = Depends(get_service),
) -> TaskResponse:
    task = service.snooze_task(task_id, days=days)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
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
        image_url=plant.image_url,
        language=plant.language,
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


@app.get("/images/proxy")
async def proxy_image(url: str) -> FileResponse:
    """Proxy and cache external images to avoid rate limits."""
    if not url.startswith("https://upload.wikimedia.org/"):
        raise HTTPException(status_code=400, detail="Only Wikimedia URLs allowed")

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    suffix = Path(url.split("?")[0]).suffix or ".jpg"
    cache_path = IMAGE_CACHE_DIR / f"{url_hash}{suffix}"

    if not cache_path.exists():
        import asyncio

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
