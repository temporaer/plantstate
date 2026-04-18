"""LLM integration for plant interpretation.

Defines the strict JSON contract, validates LLM output,
and provides the interpretation service.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.domain.enums import Season, TaskType, WeatherEventType
from backend.domain.models import (
    ActivationCondition,
    EventExplanation,
    Plant,
    Rule,
    RuleExplanation,
)

# --- LLM Output Contract ---


class LLMRuleOutput(BaseModel):
    """Strict schema for a single rule from LLM."""

    task_type: TaskType
    planning_seasons: list[Season]
    required_events: list[WeatherEventType] = Field(default_factory=list)
    forbidden_events: list[WeatherEventType] = Field(default_factory=list)
    recurrence_years: int = 1
    explanation: RuleExplanation
    event_explanations: dict[str, EventExplanation] = Field(default_factory=dict)


class LLMPlantOutput(BaseModel):
    """Strict schema for the complete LLM output."""

    name: str = Field(..., min_length=1, max_length=200)
    botanical_name: str | None = None
    description: str = ""
    image_url: str | None = None
    language: str = Field(..., pattern=r"^(de|en)$")
    rules: list[LLMRuleOutput] = Field(..., min_length=1)


# --- Validation ---


def validate_llm_output(raw_json: dict) -> LLMPlantOutput:
    """Validate raw JSON against the LLM contract.

    Raises ValidationError if the output doesn't conform.
    """
    return LLMPlantOutput.model_validate(raw_json)


def llm_output_to_plant(output: LLMPlantOutput) -> Plant:
    """Convert validated LLM output to a domain Plant."""
    rules: list[Rule] = []
    for r in output.rules:
        event_explanations: dict[WeatherEventType, EventExplanation] = {}
        for event_key, explanation in r.event_explanations.items():
            event_explanations[WeatherEventType(event_key)] = explanation

        rules.append(
            Rule(
                task_type=r.task_type,
                planning_seasons=r.planning_seasons,
                activation=ActivationCondition(
                    required_events=r.required_events,
                    forbidden_events=r.forbidden_events,
                    event_explanations=event_explanations,
                ),
                recurrence_years=r.recurrence_years,
                explanation=r.explanation,
            )
        )

    return Plant(
        name=output.name,
        botanical_name=output.botanical_name,
        description=output.description,
        image_url=output.image_url,
        language=output.language,
        rules=rules,
    )


# --- System Prompt ---


LLM_SYSTEM_PROMPT = """You are a garden lifecycle expert. Given a plant name or description,
generate a structured lifecycle plan as strict JSON.

RULES:
1. Detect the language (de or en) from the input. Localize name, description, and explanations.
2. Keep ALL enum values in English (task_type, planning_seasons, events).
3. Use ONLY these task types: sow, transplant, harvest, prune_maintenance, prune_structural,
   cut_back, deadhead, thin_fruit, remove_deadwood
4. Use ONLY these weather events: frost_risk_active, frost_risk_passed, sustained_mild_nights,
   warm_spell, heatwave, dry_spell, persistent_rain
5. Use ONLY these seasons: early_spring, spring, early_summer, summer, late_summer, autumn, winter
6. NO dates, NO durations, NO external API references.
7. Each rule MUST have an explanation with summary, why, and how fields.
8. Each referenced event MUST have an event_explanation with why and how fields.
9. Explanations must be beginner-friendly, concrete, 1-3 sentences each.

Output ONLY valid JSON matching this schema:
{
  "name": "string",
  "botanical_name": "string or null",
  "description": "string",
  "language": "de" or "en",
  "rules": [
    {
      "task_type": "enum",
      "planning_seasons": ["enum", ...],
      "required_events": ["enum", ...],
      "forbidden_events": ["enum", ...],
      "recurrence_years": 1,
      "explanation": {
        "summary": "string",
        "why": "string",
        "how": "string"
      },
      "event_explanations": {
        "event_name": {
          "why": "string",
          "how": "string"
        }
      }
    }
  ]
}"""
