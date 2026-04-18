"""Rule evaluation engine.

Determines which tasks are relevant now based on:
- planning window (season-based)
- activation conditions (event-based)
"""

from __future__ import annotations

from datetime import date

from backend.domain.enums import MONTH_TO_SEASON, Season
from backend.domain.models import ActivationCondition, EventState, Rule


def get_current_season(today: date | None = None) -> Season:
    """Get the current meteorological season from the date."""
    if today is None:
        today = date.today()
    return MONTH_TO_SEASON[today.month]


def is_in_planning_window(rule: Rule, current_season: Season) -> bool:
    """Check if the current season falls within the rule's planning seasons."""
    return current_season in rule.planning_seasons


def are_activation_conditions_met(
    activation: ActivationCondition, event_state: EventState
) -> bool:
    """Check if all activation conditions are satisfied.

    All required_events must be active.
    No forbidden_events may be active.
    """
    if not all(
        event_state.is_active(event)
        for event in activation.required_events
    ):
        return False
    return all(
        not event_state.is_active(event)
        for event in activation.forbidden_events
    )


def is_relevant_now(
    rule: Rule,
    event_state: EventState,
    current_season: Season | None = None,
    today: date | None = None,
) -> bool:
    """Determine if a rule's task is relevant right now.

    relevant_now = in_planning_window AND activation_conditions_met
    """
    if current_season is None:
        current_season = get_current_season(today)
    return is_in_planning_window(rule, current_season) and are_activation_conditions_met(
        rule.activation, event_state
    )
