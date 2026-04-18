"""Unit tests for rule evaluation engine."""

from datetime import date

import pytest

from backend.domain.enums import Season, TaskType, Urgency, WeatherEventType
from backend.domain.models import (
    ActivationCondition,
    EventState,
    Rule,
    RuleExplanation,
)
from backend.domain.rules import (
    are_activation_conditions_met,
    compute_urgency,
    get_current_season,
    is_in_planning_window,
    is_relevant_now,
)


def _make_rule(
    task_type: TaskType = TaskType.SOW,
    planning_seasons: list[Season] | None = None,
    required_events: list[WeatherEventType] | None = None,
    forbidden_events: list[WeatherEventType] | None = None,
) -> Rule:
    return Rule(
        task_type=task_type,
        planning_seasons=planning_seasons or [Season.SPRING],
        activation=ActivationCondition(
            required_events=required_events or [],
            forbidden_events=forbidden_events or [],
        ),
        explanation=RuleExplanation(
            summary="Test rule",
            why="For testing",
            how="By testing",
        ),
    )


def _make_event_state(**kwargs: bool) -> EventState:
    return EventState(**kwargs)


# --- get_current_season ---


class TestGetCurrentSeason:
    @pytest.mark.parametrize(
        "month,expected",
        [
            (1, Season.WINTER),
            (2, Season.EARLY_SPRING),
            (3, Season.EARLY_SPRING),
            (4, Season.SPRING),
            (5, Season.SPRING),
            (6, Season.EARLY_SUMMER),
            (7, Season.SUMMER),
            (8, Season.SUMMER),
            (9, Season.LATE_SUMMER),
            (10, Season.AUTUMN),
            (11, Season.AUTUMN),
            (12, Season.WINTER),
        ],
    )
    def test_month_to_season(self, month: int, expected: Season) -> None:
        test_date = date(2026, month, 15)
        assert get_current_season(test_date) == expected


# --- is_in_planning_window ---


class TestIsInPlanningWindow:
    def test_in_window(self) -> None:
        rule = _make_rule(planning_seasons=[Season.SPRING, Season.EARLY_SUMMER])
        assert is_in_planning_window(rule, Season.SPRING) is True

    def test_not_in_window(self) -> None:
        rule = _make_rule(planning_seasons=[Season.SPRING])
        assert is_in_planning_window(rule, Season.WINTER) is False

    def test_multiple_seasons(self) -> None:
        rule = _make_rule(
            planning_seasons=[Season.EARLY_SPRING, Season.SPRING, Season.EARLY_SUMMER]
        )
        assert is_in_planning_window(rule, Season.EARLY_SPRING) is True
        assert is_in_planning_window(rule, Season.AUTUMN) is False


# --- are_activation_conditions_met ---


class TestActivationConditions:
    def test_no_conditions(self) -> None:
        condition = ActivationCondition()
        state = _make_event_state()
        assert are_activation_conditions_met(condition, state) is True

    def test_required_met(self) -> None:
        condition = ActivationCondition(
            required_events=[WeatherEventType.FROST_RISK_PASSED]
        )
        state = _make_event_state(frost_risk_passed=True)
        assert are_activation_conditions_met(condition, state) is True

    def test_required_not_met(self) -> None:
        condition = ActivationCondition(
            required_events=[WeatherEventType.FROST_RISK_PASSED]
        )
        state = _make_event_state(frost_risk_passed=False)
        assert are_activation_conditions_met(condition, state) is False

    def test_forbidden_violated(self) -> None:
        condition = ActivationCondition(
            forbidden_events=[WeatherEventType.FROST_RISK_ACTIVE]
        )
        state = _make_event_state(frost_risk_active=True)
        assert are_activation_conditions_met(condition, state) is False

    def test_forbidden_not_violated(self) -> None:
        condition = ActivationCondition(
            forbidden_events=[WeatherEventType.FROST_RISK_ACTIVE]
        )
        state = _make_event_state(frost_risk_active=False)
        assert are_activation_conditions_met(condition, state) is True

    def test_combined_conditions(self) -> None:
        condition = ActivationCondition(
            required_events=[WeatherEventType.FROST_RISK_PASSED, WeatherEventType.WARM_SPELL],
            forbidden_events=[WeatherEventType.HEATWAVE],
        )
        state = _make_event_state(frost_risk_passed=True, warm_spell=True, heatwave=False)
        assert are_activation_conditions_met(condition, state) is True

    def test_combined_one_required_missing(self) -> None:
        condition = ActivationCondition(
            required_events=[WeatherEventType.FROST_RISK_PASSED, WeatherEventType.WARM_SPELL],
            forbidden_events=[WeatherEventType.HEATWAVE],
        )
        state = _make_event_state(frost_risk_passed=True, warm_spell=False, heatwave=False)
        assert are_activation_conditions_met(condition, state) is False


# --- is_relevant_now ---


class TestIsRelevantNow:
    def test_relevant_when_both_conditions_met(self) -> None:
        rule = _make_rule(
            planning_seasons=[Season.SPRING],
            required_events=[WeatherEventType.FROST_RISK_PASSED],
        )
        state = _make_event_state(frost_risk_passed=True)
        assert is_relevant_now(rule, state, current_season=Season.SPRING) is True

    def test_not_relevant_wrong_season(self) -> None:
        rule = _make_rule(
            planning_seasons=[Season.SPRING],
            required_events=[WeatherEventType.FROST_RISK_PASSED],
        )
        state = _make_event_state(frost_risk_passed=True)
        assert is_relevant_now(rule, state, current_season=Season.WINTER) is False

    def test_not_relevant_activation_not_met(self) -> None:
        rule = _make_rule(
            planning_seasons=[Season.SPRING],
            required_events=[WeatherEventType.FROST_RISK_PASSED],
        )
        state = _make_event_state(frost_risk_passed=False)
        assert is_relevant_now(rule, state, current_season=Season.SPRING) is False

    def test_relevant_with_date(self) -> None:
        rule = _make_rule(
            planning_seasons=[Season.SPRING],
            required_events=[WeatherEventType.SUSTAINED_MILD_NIGHTS],
        )
        state = _make_event_state(sustained_mild_nights=True)
        assert is_relevant_now(rule, state, today=date(2026, 4, 15)) is True

    def test_not_relevant_with_date(self) -> None:
        rule = _make_rule(
            planning_seasons=[Season.SPRING],
            required_events=[WeatherEventType.SUSTAINED_MILD_NIGHTS],
        )
        state = _make_event_state(sustained_mild_nights=True)
        assert is_relevant_now(rule, state, today=date(2026, 12, 15)) is False


# --- compute_urgency ---


class TestComputeUrgency:
    def test_relaxed_when_not_in_window(self) -> None:
        rule = _make_rule(planning_seasons=[Season.SPRING])
        state = _make_event_state()
        assert compute_urgency(rule, state, current_season=Season.WINTER) == Urgency.RELAXED

    def test_relaxed_when_conditions_not_met(self) -> None:
        rule = _make_rule(
            planning_seasons=[Season.SPRING],
            required_events=[WeatherEventType.FROST_RISK_PASSED],
        )
        state = _make_event_state(frost_risk_passed=False)
        assert compute_urgency(rule, state, current_season=Season.SPRING) == Urgency.RELAXED

    def test_soon_when_relevant_no_pressure(self) -> None:
        """In window + conditions met + early in planning window → soon."""
        rule = _make_rule(
            planning_seasons=[Season.SPRING, Season.EARLY_SUMMER],
            required_events=[WeatherEventType.FROST_RISK_PASSED],
        )
        state = _make_event_state(frost_risk_passed=True)
        assert compute_urgency(rule, state, current_season=Season.SPRING) == Urgency.SOON

    def test_acute_when_transient_danger_event(self) -> None:
        """Frost risk active is a transient danger → acute."""
        rule = _make_rule(
            planning_seasons=[Season.AUTUMN, Season.WINTER],
            required_events=[WeatherEventType.FROST_RISK_ACTIVE],
        )
        state = _make_event_state(frost_risk_active=True)
        assert compute_urgency(rule, state, current_season=Season.AUTUMN) == Urgency.ACUTE

    def test_acute_when_last_planning_season(self) -> None:
        """In the last planning season for a rule → acute."""
        rule = _make_rule(
            planning_seasons=[Season.SPRING, Season.EARLY_SUMMER],
            required_events=[WeatherEventType.FROST_RISK_PASSED],
        )
        state = _make_event_state(frost_risk_passed=True)
        assert compute_urgency(rule, state, current_season=Season.EARLY_SUMMER) == Urgency.ACUTE

    def test_soon_when_single_season_not_transient(self) -> None:
        """Single season with no transient events → actually acute (last = only)."""
        rule = _make_rule(
            planning_seasons=[Season.SPRING],
            required_events=[WeatherEventType.FROST_RISK_PASSED],
        )
        state = _make_event_state(frost_risk_passed=True)
        # Single season = last season, so acute
        assert compute_urgency(rule, state, current_season=Season.SPRING) == Urgency.ACUTE

    def test_acute_heatwave(self) -> None:
        """Heatwave is transient danger → acute."""
        rule = _make_rule(
            planning_seasons=[Season.SUMMER, Season.LATE_SUMMER],
            required_events=[WeatherEventType.HEATWAVE],
        )
        state = _make_event_state(heatwave=True)
        assert compute_urgency(rule, state, current_season=Season.SUMMER) == Urgency.ACUTE
