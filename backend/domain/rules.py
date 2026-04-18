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

    - acute: transient danger event active (frost, heatwave, …),
             OR last planning season is ending (2nd month of the season)
    - soon: in planning window and conditions met
    - relaxed: not yet actionable

    Low-priority tasks are capped at "soon" — they're never acute.
    """
    if today is None:
        today = date.today()
    if current_season is None:
        current_season = get_current_season(today)

    in_window = is_in_planning_window(rule, current_season)
    conditions_met = are_activation_conditions_met(rule.activation, event_state)

    if not in_window or not conditions_met:
        return Urgency.RELAXED

    # Low-priority tasks are never acute
    from backend.domain.enums import Priority
    if rule.priority == Priority.LOW:
        return Urgency.SOON

    # Check if a transient danger event is among the required triggers
    has_transient = any(
        evt in _TRANSIENT_DANGER_EVENTS
        for evt in rule.activation.required_events
    )
    if has_transient:
        return Urgency.ACUTE

    # Check if the planning window is about to close:
    # we're in the last planning season AND in the 2nd month of that season
    if len(rule.planning_seasons) > 0:
        season_positions = [_SEASON_ORDER.index(s) for s in rule.planning_seasons]
        last_season_idx = max(season_positions)
        if _SEASON_ORDER.index(current_season) == last_season_idx:
            # Seasons span 1-2 months. For 1-month seasons we're always
            # at the end. For 2-month seasons, acute only in the 2nd month.
            months_in_season = [
                m for m, s in MONTH_TO_SEASON.items() if s == current_season
            ]
            if len(months_in_season) <= 1 or today.month == max(months_in_season):
                return Urgency.ACUTE

    return Urgency.SOON
