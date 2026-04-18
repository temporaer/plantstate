"""Tests for sensor serialization used by the Lovelace card.

The card (plant-state-card.js) reads t.task_id, t.plant_id, t.plant_name,
t.task_type, t.urgency, t.priority, t.explanation_summary from sensor
attributes. These tests ensure the serialization matches those expectations.
"""

import json

from backend.api.routes import SENSOR_TASK_KEYS, serialize_relevant_task
from backend.application.services import RelevantTask
from backend.domain.enums import (
    Priority,
    Season,
    TaskStatus,
    TaskType,
    Urgency,
    WeatherEventType,
)
from backend.domain.models import (
    ActivationCondition,
    EventState,
    Plant,
    Rule,
    RuleExplanation,
    Task,
)


def _make_relevant_task(
    urgency: Urgency = Urgency.SOON,
    task_type: TaskType = TaskType.SOW,
    priority: Priority = Priority.NORMAL,
) -> RelevantTask:
    """Build a minimal RelevantTask for testing."""
    rule = Rule(
        id="rule-1",
        task_type=task_type,
        planning_seasons=[Season.SPRING],
        activation=ActivationCondition(
            required_events=[WeatherEventType.FROST_RISK_PASSED],
        ),
        priority=priority,
        explanation=RuleExplanation(
            summary="Sow after last frost",
            why="Frost kills seedlings",
            how="Direct sow into prepared bed",
        ),
    )
    plant = Plant(
        id="plant-1",
        name="Tomate",
        rules=[rule],
    )
    task = Task(
        id="task-1",
        plant_id=plant.id,
        rule_id=rule.id,
        task_type=task_type,
        status=TaskStatus.ACTIVE,
        year=2026,
    )
    event_state = EventState(frost_risk_passed=True)
    return RelevantTask(
        task=task,
        plant=plant,
        rule=rule,
        event_state=event_state,
        urgency=urgency,
    )


def test_serialize_has_all_card_keys():
    """Serialized dict must contain every key the Lovelace card reads."""
    result = serialize_relevant_task(_make_relevant_task())
    assert set(result.keys()) == SENSOR_TASK_KEYS


def test_serialize_values_are_strings():
    """All values must be JSON-serializable strings (no enum objects)."""
    result = serialize_relevant_task(_make_relevant_task())
    dumped = json.dumps(result)
    restored = json.loads(dumped)
    assert restored == result


def test_serialize_plant_name():
    rt = _make_relevant_task()
    assert serialize_relevant_task(rt)["plant_name"] == "Tomate"


def test_serialize_urgency_is_string_value():
    for urg in Urgency:
        rt = _make_relevant_task(urgency=urg)
        result = serialize_relevant_task(rt)
        assert result["urgency"] == urg.value
        assert isinstance(result["urgency"], str)


def test_serialize_task_type_is_string_value():
    rt = _make_relevant_task(task_type=TaskType.HARVEST)
    assert serialize_relevant_task(rt)["task_type"] == "harvest"


def test_serialize_priority_is_string_value():
    rt = _make_relevant_task(priority=Priority.HIGH)
    assert serialize_relevant_task(rt)["priority"] == "high"


def test_serialize_explanation_summary():
    rt = _make_relevant_task()
    assert serialize_relevant_task(rt)["explanation_summary"] == "Sow after last frost"


def test_serialize_ids():
    rt = _make_relevant_task()
    result = serialize_relevant_task(rt)
    assert result["task_id"] == "task-1"
    assert result["plant_id"] == "plant-1"
