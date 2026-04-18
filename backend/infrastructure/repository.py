"""Repository pattern for domain persistence.

Converts between domain models and database rows.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.domain.enums import Priority, Season, TaskStatus, TaskType, WeatherEventType
from backend.domain.models import (
    ActivationCondition,
    EventExplanation,
    Plant,
    Rule,
    RuleExplanation,
    Task,
)
from backend.infrastructure.database import PlantRow, RuleRow, TaskRow


class PlantRepository:
    """Repository for Plant aggregate persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, plant: Plant) -> Plant:
        """Save a plant with all its rules."""
        now = datetime.now()
        row = PlantRow(
            id=plant.id,
            name=plant.name,
            botanical_name=plant.botanical_name,
            description=plant.description,
            image_url=plant.image_url,
            language=plant.language,
            active=plant.active,
            created_at=plant.created_at or now,
            updated_at=now,
        )
        for rule in plant.rules:
            rule_row = RuleRow(
                id=rule.id,
                plant_id=plant.id,
                task_type=rule.task_type.value,
                planning_seasons=[s.value for s in rule.planning_seasons],
                activation=rule.activation.model_dump(mode="json"),
                recurrence_years=rule.recurrence_years,
                priority=rule.priority.value,
                explanation=rule.explanation.model_dump(),
            )
            row.rules.append(rule_row)

        self._session.merge(row)
        self._session.flush()
        plant.created_at = row.created_at
        plant.updated_at = row.updated_at
        return plant

    def get(self, plant_id: str) -> Plant | None:
        """Get a plant by ID with all rules loaded."""
        stmt = (
            select(PlantRow)
            .options(selectinload(PlantRow.rules))
            .where(PlantRow.id == plant_id)
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def list_all(self) -> list[Plant]:
        """List all plants with rules."""
        stmt = select(PlantRow).options(selectinload(PlantRow.rules))
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def delete(self, plant_id: str) -> bool:
        """Delete a plant and cascade."""
        row = self._session.get(PlantRow, plant_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def set_active(self, plant_id: str, active: bool) -> Plant | None:
        """Enable or disable a plant."""
        row = self._session.get(PlantRow, plant_id)
        if row is None:
            return None
        row.active = active
        self._session.flush()
        # Reload with rules
        return self.get(plant_id)

    @staticmethod
    def _to_domain(row: PlantRow) -> Plant:
        rules = []
        for r in row.rules:
            activation_data = r.activation
            event_explanations = {}
            for k, v in activation_data.get("event_explanations", {}).items():
                event_explanations[WeatherEventType(k)] = EventExplanation(**v)

            activation = ActivationCondition(
                required_events=[
                    WeatherEventType(e)
                    for e in activation_data.get("required_events", [])
                ],
                forbidden_events=[
                    WeatherEventType(e)
                    for e in activation_data.get("forbidden_events", [])
                ],
                event_explanations=event_explanations,
            )
            rules.append(
                Rule(
                    id=r.id,
                    task_type=TaskType(r.task_type),
                    planning_seasons=[Season(s) for s in r.planning_seasons],
                    activation=activation,
                    recurrence_years=r.recurrence_years,
                    priority=Priority(r.priority) if r.priority else Priority.NORMAL,
                    explanation=RuleExplanation(**r.explanation),
                )
            )

        return Plant(
            id=row.id,
            name=row.name,
            botanical_name=row.botanical_name,
            description=row.description,
            image_url=row.image_url,
            language=row.language,
            active=getattr(row, "active", True),
            rules=rules,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class TaskRepository:
    """Repository for Task persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, task: Task) -> Task:
        row = TaskRow(
            id=task.id,
            plant_id=task.plant_id,
            rule_id=task.rule_id,
            task_type=task.task_type.value,
            status=task.status.value,
            year=task.year,
            activated_at=task.activated_at,
            completed_at=task.completed_at,
            snoozed_until=task.snoozed_until,
        )
        self._session.merge(row)
        self._session.flush()
        return task

    def get(self, task_id: str) -> Task | None:
        row = self._session.get(TaskRow, task_id)
        if row is None:
            return None
        return self._to_domain(row)

    def list_by_plant(self, plant_id: str) -> list[Task]:
        stmt = select(TaskRow).where(TaskRow.plant_id == plant_id)
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def list_active(self) -> list[Task]:
        stmt = select(TaskRow).where(TaskRow.status.in_(["planned", "active"]))
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def update_status(self, task_id: str, status: TaskStatus) -> Task | None:
        row = self._session.get(TaskRow, task_id)
        if row is None:
            return None
        row.status = status.value
        if status == TaskStatus.COMPLETED:
            row.completed_at = datetime.now()
        elif status == TaskStatus.ACTIVE:
            row.activated_at = datetime.now()
        self._session.flush()
        return self._to_domain(row)

    def snooze(self, task_id: str, until: date) -> Task | None:
        row = self._session.get(TaskRow, task_id)
        if row is None:
            return None
        row.snoozed_until = until
        self._session.flush()
        return self._to_domain(row)

    @staticmethod
    def _to_domain(row: TaskRow) -> Task:
        return Task(
            id=row.id,
            plant_id=row.plant_id,
            rule_id=row.rule_id,
            task_type=TaskType(row.task_type),
            status=TaskStatus(row.status),
            year=row.year,
            activated_at=row.activated_at,
            completed_at=row.completed_at,
            snoozed_until=row.snoozed_until,
        )
