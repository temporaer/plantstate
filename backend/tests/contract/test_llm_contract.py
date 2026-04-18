"""Contract tests for LLM output validation."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.application.llm_contract import (
    LLMPlantOutput,
    llm_output_to_plant,
    validate_llm_output,
)
from backend.domain.enums import TaskType, WeatherEventType


@pytest.fixture
def all_fixtures():
    path = Path(__file__).parent.parent / "fixtures.json"
    with open(path) as f:
        return json.load(f)


class TestLLMContract:
    def test_all_fixtures_validate(self, all_fixtures):
        for plant_data in all_fixtures:
            result = validate_llm_output(plant_data)
            assert isinstance(result, LLMPlantOutput)
            assert len(result.rules) >= 1

    def test_all_fixtures_have_explanations(self, all_fixtures):
        for plant_data in all_fixtures:
            result = validate_llm_output(plant_data)
            for rule in result.rules:
                assert rule.explanation.summary
                assert rule.explanation.why
                assert rule.explanation.how

    def test_all_referenced_events_have_explanations(self, all_fixtures):
        for plant_data in all_fixtures:
            result = validate_llm_output(plant_data)
            for rule in result.rules:
                all_events = set(rule.required_events) | set(rule.forbidden_events)
                for event in all_events:
                    assert event.value in rule.event_explanations, (
                        f"Missing explanation for {event.value} in "
                        f"{plant_data['name']}/{rule.task_type}"
                    )

    def test_only_allowed_task_types(self, all_fixtures):
        allowed = {t.value for t in TaskType}
        for plant_data in all_fixtures:
            result = validate_llm_output(plant_data)
            for rule in result.rules:
                assert rule.task_type.value in allowed

    def test_only_allowed_events(self, all_fixtures):
        allowed = {e.value for e in WeatherEventType}
        for plant_data in all_fixtures:
            result = validate_llm_output(plant_data)
            for rule in result.rules:
                for event in rule.required_events:
                    assert event.value in allowed
                for event in rule.forbidden_events:
                    assert event.value in allowed

    def test_converts_to_domain_plant(self, all_fixtures):
        for plant_data in all_fixtures:
            result = validate_llm_output(plant_data)
            plant = llm_output_to_plant(result)
            assert plant.name == plant_data["name"]
            assert len(plant.rules) == len(plant_data["rules"])

    def test_rejects_invalid_task_type(self):
        bad = {
            "name": "Test",
            "language": "en",
            "rules": [{
                "task_type": "water",  # not allowed
                "planning_seasons": ["spring"],
                "explanation": {"summary": "x", "why": "x", "how": "x"},
            }],
        }
        with pytest.raises(ValidationError):
            validate_llm_output(bad)

    def test_rejects_invalid_event(self):
        bad = {
            "name": "Test",
            "language": "en",
            "rules": [{
                "task_type": "sow",
                "planning_seasons": ["spring"],
                "required_events": ["full_moon"],  # not allowed
                "explanation": {"summary": "x", "why": "x", "how": "x"},
            }],
        }
        with pytest.raises(ValidationError):
            validate_llm_output(bad)

    def test_rejects_invalid_language(self):
        bad = {
            "name": "Test",
            "language": "fr",  # only de/en allowed
            "rules": [{
                "task_type": "sow",
                "planning_seasons": ["spring"],
                "explanation": {"summary": "x", "why": "x", "how": "x"},
            }],
        }
        with pytest.raises(ValidationError):
            validate_llm_output(bad)
