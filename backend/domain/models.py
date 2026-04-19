"""Domain models for the plant lifecycle system.

All models are Pydantic strict models. Lifecycle logic is rule-based,
not date-based. All timing derives from weather events + seasons.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.enums import Priority, Season, TaskStatus, TaskType, WeatherEventType

# --- Explanation models (required for LLM contract) ---


class RuleExplanation(BaseModel):
    """Beginner-friendly explanation of why/how a rule works."""

    model_config = ConfigDict(strict=True)

    summary: str = Field(..., min_length=1, max_length=500)
    why: str = Field(..., min_length=1, max_length=500)
    how: str = Field(..., min_length=1, max_length=500)


class EventExplanation(BaseModel):
    """Beginner-friendly explanation of a weather event."""

    model_config = ConfigDict(strict=True)

    why: str = Field(..., min_length=1, max_length=500)
    how: str = Field(..., min_length=1, max_length=500)


# --- Weather models ---


class DailyWeather(BaseModel):
    """A single day's weather data (observed or forecast)."""

    model_config = ConfigDict(strict=True)

    date: date
    temp_min: float
    temp_max: float
    precipitation_mm: float


class WeatherData(BaseModel):
    """Combined weather data for event computation."""

    model_config = ConfigDict(strict=True)

    history: list[DailyWeather] = Field(default_factory=list)
    forecast: list[DailyWeather] = Field(default_factory=list)


# --- Event state ---


class EventState(BaseModel):
    """Current state of all computed weather events."""

    model_config = ConfigDict(strict=True)

    frost_risk_active: bool = False
    frost_risk_passed: bool = False
    sustained_mild_nights: bool = False
    warm_spell: bool = False
    heatwave: bool = False
    dry_spell: bool = False
    persistent_rain: bool = False
    computed_at: datetime | None = None

    def is_active(self, event: WeatherEventType) -> bool:
        """Check if a specific weather event is currently active."""
        return bool(getattr(self, event.value))


# --- Activation condition ---


class ActivationCondition(BaseModel):
    """Conditions that must be met for a task to become active."""

    model_config = ConfigDict(strict=True)

    required_events: list[WeatherEventType] = Field(default_factory=list)
    forbidden_events: list[WeatherEventType] = Field(default_factory=list)
    event_explanations: dict[WeatherEventType, EventExplanation] = Field(default_factory=dict)


# --- Rule ---


class Rule(BaseModel):
    """A lifecycle rule that determines when a task should be performed.

    Planning is season-based, activation is event-based.
    """

    model_config = ConfigDict(strict=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    planning_seasons: list[Season]
    activation: ActivationCondition
    recurrence_years: int = 1
    priority: Priority = Priority.NORMAL
    explanation: RuleExplanation


# --- Plant ---


class Plant(BaseModel):
    """A plant with its lifecycle rules."""

    model_config = ConfigDict(strict=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    botanical_name: str | None = None
    description: str = ""
    water_needs: str = ""
    fertilizer_needs: str = ""
    image_url: str | None = None
    language: str = "en"
    active: bool = True
    rules: list[Rule] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- Task ---


class Task(BaseModel):
    """A concrete task instance generated from a rule."""

    model_config = ConfigDict(strict=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plant_id: str
    rule_id: str
    task_type: TaskType
    status: TaskStatus = TaskStatus.PLANNED
    year: int
    activated_at: datetime | None = None
    completed_at: datetime | None = None
    snoozed_until: date | None = None


# --- Calendar projection ---


class CalendarProjection(BaseModel):
    """A task projected onto a calendar for HA sync."""

    model_config = ConfigDict(strict=True)

    task_id: str
    plant_name: str
    task_type: TaskType
    summary: str
    description: str
    start_date: date
    end_date: date
