"""Rule evaluation engine.

Determines which tasks are relevant now based on:
- planning window (season-based)
- activation conditions (event-based)
- urgency (time pressure from weather + season position)
"""

from __future__ import annotations

from datetime import date

from backend.domain.enums import MONTH_TO_SEASON, Season, Urgency, WeatherEventType
from backend.domain.models import ActivationCondition, EventState, Rule


# Events that signal immediate time pressure when they are a required trigger
_TRANSIENT_DANGER_EVENTS = {
    WeatherEventType.FROST_RISK_ACTIVE,
    WeatherEventType.HEATWAVE,
    WeatherEventType.DRY_SPELL,
    WeatherEventType.PERSISTENT_RAIN,
}

# Ordered season list for position calculations
_SEASON_ORDER = list(Season)


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


def compute_urgency(
    rule: Rule,
    event_state: EventState,
    current_season: Season | None = None,
    today: date | None = None,
) -> Urgency:
    """Compute how time-pressured a task is.

    - acute: transient danger event active, or in last planning season
    - soon: in planning window and conditions met
    - relaxed: not yet actionable
    """
    if current_season is None:
        current_season = get_current_season(today)

    in_window = is_in_planning_window(rule, current_season)
    conditions_met = are_activation_conditions_met(rule.activation, event_state)

    if not in_window or not conditions_met:
        return Urgency.RELAXED

    # Check if a transient danger event is among the required triggers
    has_transient = any(
        evt in _TRANSIENT_DANGER_EVENTS
        for evt in rule.activation.required_events
    )
    # Also urgent if a forbidden danger event is *about* to appear
    # (frost_risk_active is false now but the rule forbids it — if frost
    # is forecast soon the window may close)

    # Check if we're in the last planning season for this rule
    in_last_season = False
    if len(rule.planning_seasons) > 0:
        season_positions = [_SEASON_ORDER.index(s) for s in rule.planning_seasons]
        last_season_idx = max(season_positions)
        in_last_season = _SEASON_ORDER.index(current_season) == last_season_idx

    if has_transient or in_last_season:
        return Urgency.ACUTE

    return Urgency.SOON
