"""Application service layer.

Orchestrates domain logic and persistence. No business logic here —
delegates to domain functions and repositories.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from backend.domain.enums import Season, TaskStatus
from backend.domain.events import compute_all_events
from backend.domain.models import EventState, Plant, Rule, Task, WeatherData
from backend.domain.rules import (
    are_activation_conditions_met,
    get_current_season,
    is_in_planning_window,
    is_relevant_now,
)
from backend.infrastructure.repository import PlantRepository, TaskRepository


class PlantService:
    """Service for plant lifecycle management."""

    def __init__(self, db_session: Session) -> None:
        self._plants = PlantRepository(db_session)
        self._tasks = TaskRepository(db_session)
        self._session = db_session

    def add_plant(self, plant: Plant) -> Plant:
        """Persist a new plant and generate initial tasks."""
        now = datetime.now()
        plant.created_at = now
        plant.updated_at = now
        saved = self._plants.save(plant)

        # Generate planned tasks for current year
        year = date.today().year
        for rule in saved.rules:
            task = Task(
                plant_id=saved.id,
                rule_id=rule.id,
                task_type=rule.task_type,
                status=TaskStatus.PLANNED,
                year=year,
            )
            self._tasks.save(task)

        self._session.commit()
        return saved

    def get_plant(self, plant_id: str) -> Plant | None:
        return self._plants.get(plant_id)

    def list_plants(self) -> list[Plant]:
        return self._plants.list_all()

    def delete_plant(self, plant_id: str) -> bool:
        result = self._plants.delete(plant_id)
        if result:
            self._session.commit()
        return result

    def complete_task(self, task_id: str) -> Task | None:
        task = self._tasks.update_status(task_id, TaskStatus.COMPLETED)
        if task:
            self._session.commit()
        return task

    def skip_task(self, task_id: str) -> Task | None:
        task = self._tasks.update_status(task_id, TaskStatus.SKIPPED)
        if task:
            self._session.commit()
        return task

    def get_relevant_now(self, weather_data: WeatherData) -> list[RelevantTask]:
        """Get all tasks that are relevant right now."""
        event_state = compute_all_events(weather_data)
        current_season = get_current_season()
        plants = self._plants.list_all()
        active_tasks = self._tasks.list_active()

        # Build lookup: rule_id -> tasks
        task_by_rule: dict[str, list[Task]] = {}
        for t in active_tasks:
            task_by_rule.setdefault(t.rule_id, []).append(t)

        results: list[RelevantTask] = []
        for plant in plants:
            for rule in plant.rules:
                if is_relevant_now(rule, event_state, current_season):
                    tasks = task_by_rule.get(rule.id, [])
                    for task in tasks:
                        results.append(
                            RelevantTask(
                                task=task,
                                plant=plant,
                                rule=rule,
                                event_state=event_state,
                            )
                        )
        return results

    def get_outlook(
        self, weather_data: WeatherData,
    ) -> list[OutlookItem]:
        """Get all tasks for the year with season and readiness info."""
        event_state = compute_all_events(weather_data)
        current_season = get_current_season()
        plants = self._plants.list_all()
        active_tasks = self._tasks.list_active()

        task_by_rule: dict[str, list[Task]] = {}
        for t in active_tasks:
            task_by_rule.setdefault(t.rule_id, []).append(t)

        # Season ordering for sorting
        season_order = list(Season)

        results: list[OutlookItem] = []
        for plant in plants:
            for rule in plant.rules:
                tasks = task_by_rule.get(rule.id, [])
                in_window = is_in_planning_window(rule, current_season)
                conditions_met = are_activation_conditions_met(
                    rule.activation, event_state,
                )

                # Determine what's blocking activation
                blocking: list[str] = []
                if not in_window:
                    blocking.append("season")
                if not conditions_met:
                    for evt in rule.activation.required_events:
                        if not event_state.is_active(evt):
                            blocking.append(f"waiting:{evt.value}")
                    for evt in rule.activation.forbidden_events:
                        if event_state.is_active(evt):
                            blocking.append(f"blocked:{evt.value}")

                # Pick earliest planning season for sort order
                earliest_season_idx = min(
                    (season_order.index(s) for s in rule.planning_seasons),
                    default=0,
                )

                for task in tasks:
                    results.append(
                        OutlookItem(
                            task=task,
                            plant=plant,
                            rule=rule,
                            in_planning_window=in_window,
                            conditions_met=conditions_met,
                            blocking=blocking,
                            season_sort=earliest_season_idx,
                        )
                    )

        results.sort(key=lambda x: x.season_sort)
        return results


class RelevantTask:
    """A task that is currently relevant, with its context."""

    def __init__(
        self,
        task: Task,
        plant: Plant,
        rule: Rule,
        event_state: EventState,
    ) -> None:
        self.task = task
        self.plant = plant
        self.rule = rule
        self.event_state = event_state


class OutlookItem:
    """A task in the yearly outlook, with readiness info."""

    def __init__(
        self,
        task: Task,
        plant: Plant,
        rule: Rule,
        in_planning_window: bool,
        conditions_met: bool,
        blocking: list[str],
        season_sort: int,
    ) -> None:
        self.task = task
        self.plant = plant
        self.rule = rule
        self.in_planning_window = in_planning_window
        self.conditions_met = conditions_met
        self.blocking = blocking
        self.season_sort = season_sort
