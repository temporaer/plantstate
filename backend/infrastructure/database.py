"""SQLAlchemy database models for persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PlantRow(Base):
    __tablename__ = "plants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    botanical_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    rules: Mapped[list[RuleRow]] = relationship(
        back_populates="plant", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[TaskRow]] = relationship(
        back_populates="plant", cascade="all, delete-orphan"
    )


class RuleRow(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plant_id: Mapped[str] = mapped_column(ForeignKey("plants.id"), nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    planning_seasons: Mapped[dict] = mapped_column(JSON, nullable=False)  # list[str]
    activation: Mapped[dict] = mapped_column(JSON, nullable=False)
    recurrence_years: Mapped[int] = mapped_column(default=1)
    explanation: Mapped[dict] = mapped_column(JSON, nullable=False)

    plant: Mapped[PlantRow] = relationship(back_populates="rules")


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plant_id: Mapped[str] = mapped_column(ForeignKey("plants.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    year: Mapped[int] = mapped_column(nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    plant: Mapped[PlantRow] = relationship(back_populates="tasks")
