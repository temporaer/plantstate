"""FastAPI application and routes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.application.services import PlantService, RelevantTask
from backend.domain.models import Plant, WeatherData
from backend.infrastructure.database import Base

DATABASE_URL = "sqlite:///plant_state.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(engine)
    yield


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


# --- Response models ---


class PlantResponse(BaseModel):
    id: str
    name: str
    botanical_name: str | None = None
    description: str = ""
    language: str = "en"
    rules: list[dict] = Field(default_factory=list)


class TaskResponse(BaseModel):
    id: str
    plant_id: str
    rule_id: str
    task_type: str
    status: str
    year: int


class RelevantNowItem(BaseModel):
    task: TaskResponse
    plant_name: str
    task_type: str
    explanation_summary: str
    explanation_why: str
    explanation_how: str


# --- Routes ---


@app.post("/plants", response_model=PlantResponse)
def create_plant(plant: Plant, service: PlantService = Depends(get_service)) -> PlantResponse:
    saved = service.add_plant(plant)
    return _plant_response(saved)


@app.get("/plants", response_model=list[PlantResponse])
def list_plants(service: PlantService = Depends(get_service)) -> list[PlantResponse]:
    plants = service.list_plants()
    return [_plant_response(p) for p in plants]


@app.get("/plants/{plant_id}", response_model=PlantResponse)
def get_plant(plant_id: str, service: PlantService = Depends(get_service)) -> PlantResponse:
    plant = service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    return _plant_response(plant)


@app.delete("/plants/{plant_id}")
def delete_plant(plant_id: str, service: PlantService = Depends(get_service)) -> dict:
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
    return TaskResponse(
        id=task.id,
        plant_id=task.plant_id,
        rule_id=task.rule_id,
        task_type=task.task_type.value,
        status=task.status.value,
        year=task.year,
    )


@app.post("/tasks/{task_id}/skip", response_model=TaskResponse)
def skip_task(
    task_id: str, service: PlantService = Depends(get_service)
) -> TaskResponse:
    task = service.skip_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        id=task.id,
        plant_id=task.plant_id,
        rule_id=task.rule_id,
        task_type=task.task_type.value,
        status=task.status.value,
        year=task.year,
    )


@app.post("/dashboard/relevant-now", response_model=list[RelevantNowItem])
def get_relevant_now(
    weather_data: WeatherData,
    service: PlantService = Depends(get_service),
) -> list[RelevantNowItem]:
    results = service.get_relevant_now(weather_data)
    return [_relevant_item(r) for r in results]


# --- Helpers ---


def _plant_response(plant: Plant) -> PlantResponse:
    return PlantResponse(
        id=plant.id,
        name=plant.name,
        botanical_name=plant.botanical_name,
        description=plant.description,
        language=plant.language,
        rules=[r.model_dump(mode="json") for r in plant.rules],
    )


def _relevant_item(r: RelevantTask) -> RelevantNowItem:
    return RelevantNowItem(
        task=TaskResponse(
            id=r.task.id,
            plant_id=r.task.plant_id,
            rule_id=r.task.rule_id,
            task_type=r.task.task_type.value,
            status=r.task.status.value,
            year=r.task.year,
        ),
        plant_name=r.plant.name,
        task_type=r.task.task_type.value,
        explanation_summary=r.rule.explanation.summary,
        explanation_why=r.rule.explanation.why,
        explanation_how=r.rule.explanation.how,
    )
