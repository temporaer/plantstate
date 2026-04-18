"""Unit tests for weather event computation."""

from datetime import date

from backend.domain.events import (
    compute_all_events,
    compute_dry_spell,
    compute_frost_risk_active,
    compute_frost_risk_passed,
    compute_heatwave,
    compute_persistent_rain,
    compute_sustained_mild_nights,
    compute_warm_spell,
)
from backend.domain.models import DailyWeather, WeatherData


def _day(d: str, temp_min: float, temp_max: float, rain: float = 0.0) -> DailyWeather:
    return DailyWeather(
        date=date.fromisoformat(d),
        temp_min=temp_min,
        temp_max=temp_max,
        precipitation_mm=rain,
    )


# --- frost_risk_active ---


class TestFrostRiskActive:
    def test_frost_when_below_threshold(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-04-01", 3.0, 12.0),
                _day("2026-04-02", 1.0, 10.0),
                _day("2026-04-03", -1.0, 8.0),
                _day("2026-04-04", 2.0, 11.0),
                _day("2026-04-05", 4.0, 14.0),
            ]
        )
        assert compute_frost_risk_active(data) is True

    def test_no_frost_when_all_above(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-04-01", 5.0, 15.0),
                _day("2026-04-02", 4.0, 14.0),
                _day("2026-04-03", 6.0, 16.0),
                _day("2026-04-04", 3.0, 12.0),
                _day("2026-04-05", 2.0, 11.0),
            ]
        )
        assert compute_frost_risk_active(data) is False

    def test_frost_at_exactly_1_degree(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-04-01", 5.0, 15.0),
                _day("2026-04-02", 1.0, 14.0),
                _day("2026-04-03", 6.0, 16.0),
                _day("2026-04-04", 3.0, 12.0),
                _day("2026-04-05", 2.0, 11.0),
            ]
        )
        assert compute_frost_risk_active(data) is True

    def test_empty_forecast(self) -> None:
        data = WeatherData(forecast=[])
        assert compute_frost_risk_active(data) is False


# --- frost_risk_passed ---


class TestFrostRiskPassed:
    def test_passed_when_all_above(self) -> None:
        data = WeatherData(
            history=[
                _day("2026-03-25", 3.0, 12.0),
                _day("2026-03-26", 4.0, 13.0),
                _day("2026-03-27", 2.0, 11.0),
                _day("2026-03-28", 5.0, 14.0),
                _day("2026-03-29", 3.0, 12.0),
                _day("2026-03-30", 4.0, 13.0),
                _day("2026-03-31", 2.0, 11.0),
            ],
            forecast=[
                _day("2026-04-01", 5.0, 15.0),
                _day("2026-04-02", 4.0, 14.0),
                _day("2026-04-03", 6.0, 16.0),
                _day("2026-04-04", 3.0, 12.0),
                _day("2026-04-05", 2.0, 11.0),
            ],
        )
        assert compute_frost_risk_passed(data) is True

    def test_not_passed_when_history_cold(self) -> None:
        data = WeatherData(
            history=[
                _day("2026-03-25", -1.0, 8.0),
                _day("2026-03-26", 4.0, 13.0),
                _day("2026-03-27", 2.0, 11.0),
                _day("2026-03-28", 5.0, 14.0),
                _day("2026-03-29", 3.0, 12.0),
                _day("2026-03-30", 4.0, 13.0),
                _day("2026-03-31", 2.0, 11.0),
            ],
            forecast=[
                _day("2026-04-01", 5.0, 15.0),
                _day("2026-04-02", 4.0, 14.0),
                _day("2026-04-03", 6.0, 16.0),
                _day("2026-04-04", 3.0, 12.0),
                _day("2026-04-05", 2.0, 11.0),
            ],
        )
        assert compute_frost_risk_passed(data) is False

    def test_not_passed_when_forecast_cold(self) -> None:
        data = WeatherData(
            history=[
                _day("2026-03-25", 3.0, 12.0),
                _day("2026-03-26", 4.0, 13.0),
                _day("2026-03-27", 2.0, 11.0),
                _day("2026-03-28", 5.0, 14.0),
                _day("2026-03-29", 3.0, 12.0),
                _day("2026-03-30", 4.0, 13.0),
                _day("2026-03-31", 2.0, 11.0),
            ],
            forecast=[
                _day("2026-04-01", 0.0, 8.0),
                _day("2026-04-02", 4.0, 14.0),
                _day("2026-04-03", 6.0, 16.0),
                _day("2026-04-04", 3.0, 12.0),
                _day("2026-04-05", 2.0, 11.0),
            ],
        )
        assert compute_frost_risk_passed(data) is False

    def test_insufficient_history(self) -> None:
        data = WeatherData(
            history=[_day("2026-03-31", 5.0, 15.0)],
            forecast=[
                _day("2026-04-01", 5.0, 15.0),
                _day("2026-04-02", 4.0, 14.0),
                _day("2026-04-03", 6.0, 16.0),
                _day("2026-04-04", 3.0, 12.0),
                _day("2026-04-05", 2.0, 11.0),
            ],
        )
        assert compute_frost_risk_passed(data) is False


# --- sustained_mild_nights ---


class TestSustainedMildNights:
    def test_mild_when_4_of_5(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-05-01", 9.0, 20.0),
                _day("2026-05-02", 8.0, 19.0),
                _day("2026-05-03", 10.0, 22.0),
                _day("2026-05-04", 5.0, 15.0),  # not mild
                _day("2026-05-05", 9.0, 21.0),
            ]
        )
        assert compute_sustained_mild_nights(data) is True

    def test_not_mild_when_only_3(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-05-01", 9.0, 20.0),
                _day("2026-05-02", 8.0, 19.0),
                _day("2026-05-03", 10.0, 22.0),
                _day("2026-05-04", 5.0, 15.0),
                _day("2026-05-05", 4.0, 14.0),
            ]
        )
        assert compute_sustained_mild_nights(data) is False

    def test_exactly_at_threshold(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-05-01", 8.0, 20.0),
                _day("2026-05-02", 8.0, 19.0),
                _day("2026-05-03", 8.0, 22.0),
                _day("2026-05-04", 8.0, 15.0),
                _day("2026-05-05", 7.0, 14.0),
            ]
        )
        assert compute_sustained_mild_nights(data) is True


# --- warm_spell ---


class TestWarmSpell:
    def test_warm_when_3_of_5(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-06-01", 12.0, 22.0),
                _day("2026-06-02", 10.0, 18.0),
                _day("2026-06-03", 14.0, 25.0),
                _day("2026-06-04", 11.0, 20.0),
                _day("2026-06-05", 8.0, 15.0),
            ]
        )
        assert compute_warm_spell(data) is True

    def test_not_warm_when_only_2(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-06-01", 12.0, 22.0),
                _day("2026-06-02", 10.0, 18.0),
                _day("2026-06-03", 14.0, 25.0),
                _day("2026-06-04", 11.0, 17.0),
                _day("2026-06-05", 8.0, 15.0),
            ]
        )
        assert compute_warm_spell(data) is False


# --- heatwave ---


class TestHeatwave:
    def test_heatwave_3_consecutive(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-07-01", 20.0, 32.0),
                _day("2026-07-02", 21.0, 33.0),
                _day("2026-07-03", 19.0, 31.0),
                _day("2026-07-04", 15.0, 25.0),
                _day("2026-07-05", 16.0, 26.0),
            ]
        )
        assert compute_heatwave(data) is True

    def test_no_heatwave_broken_streak(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-07-01", 20.0, 32.0),
                _day("2026-07-02", 21.0, 33.0),
                _day("2026-07-03", 15.0, 25.0),
                _day("2026-07-04", 19.0, 31.0),
                _day("2026-07-05", 20.0, 32.0),
            ]
        )
        assert compute_heatwave(data) is False

    def test_heatwave_at_end(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-07-01", 15.0, 25.0),
                _day("2026-07-02", 16.0, 26.0),
                _day("2026-07-03", 20.0, 30.0),
                _day("2026-07-04", 21.0, 31.0),
                _day("2026-07-05", 19.0, 32.0),
            ]
        )
        assert compute_heatwave(data) is True


# --- dry_spell ---


class TestDrySpell:
    def test_dry_3_consecutive(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-06-01", 15.0, 25.0, 0.0),
                _day("2026-06-02", 16.0, 26.0, 0.5),
                _day("2026-06-03", 17.0, 27.0, 0.0),
                _day("2026-06-04", 18.0, 28.0, 5.0),
                _day("2026-06-05", 19.0, 29.0, 0.0),
            ]
        )
        assert compute_dry_spell(data) is True

    def test_no_dry_spell(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-06-01", 15.0, 25.0, 0.0),
                _day("2026-06-02", 16.0, 26.0, 0.5),
                _day("2026-06-03", 17.0, 27.0, 2.0),
                _day("2026-06-04", 18.0, 28.0, 0.0),
                _day("2026-06-05", 19.0, 29.0, 0.0),
            ]
        )
        assert compute_dry_spell(data) is False


# --- persistent_rain ---


class TestPersistentRain:
    def test_rain_3_consecutive(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-06-01", 10.0, 15.0, 6.0),
                _day("2026-06-02", 11.0, 14.0, 8.0),
                _day("2026-06-03", 10.0, 13.0, 5.0),
                _day("2026-06-04", 12.0, 18.0, 0.0),
                _day("2026-06-05", 13.0, 20.0, 0.0),
            ]
        )
        assert compute_persistent_rain(data) is True

    def test_no_persistent_rain(self) -> None:
        data = WeatherData(
            forecast=[
                _day("2026-06-01", 10.0, 15.0, 6.0),
                _day("2026-06-02", 11.0, 14.0, 8.0),
                _day("2026-06-03", 10.0, 13.0, 2.0),
                _day("2026-06-04", 12.0, 18.0, 7.0),
                _day("2026-06-05", 13.0, 20.0, 6.0),
            ]
        )
        assert compute_persistent_rain(data) is False


# --- compute_all_events ---


class TestComputeAllEvents:
    def test_returns_event_state(self) -> None:
        data = WeatherData(
            history=[
                _day("2026-03-25", 5.0, 15.0),
                _day("2026-03-26", 6.0, 16.0),
                _day("2026-03-27", 5.0, 14.0),
                _day("2026-03-28", 7.0, 17.0),
                _day("2026-03-29", 5.0, 15.0),
                _day("2026-03-30", 6.0, 16.0),
                _day("2026-03-31", 5.0, 14.0),
            ],
            forecast=[
                _day("2026-04-01", 8.0, 22.0, 0.0),
                _day("2026-04-02", 9.0, 21.0, 0.0),
                _day("2026-04-03", 10.0, 23.0, 0.0),
                _day("2026-04-04", 8.0, 20.0, 0.0),
                _day("2026-04-05", 9.0, 22.0, 0.0),
            ],
        )
        state = compute_all_events(data)

        assert state.frost_risk_active is False
        assert state.frost_risk_passed is True
        assert state.sustained_mild_nights is True
        assert state.warm_spell is True
        assert state.heatwave is False
        assert state.dry_spell is True
        assert state.persistent_rain is False
        assert state.computed_at is not None
