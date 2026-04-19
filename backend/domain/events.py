"""Weather event computation engine.

All functions are pure, deterministic computations over WeatherData.
No side effects, no external dependencies.
"""

from __future__ import annotations

from datetime import datetime

from backend.domain.enums import WeatherEventType
from backend.domain.models import DailyWeather, EventState, WeatherData


def _get_forecast_days(forecast: list[DailyWeather], n: int) -> list[DailyWeather]:
    """Get the first n days from forecast."""
    return forecast[:n]


def _get_history_days(history: list[DailyWeather], n: int) -> list[DailyWeather]:
    """Get the last n days from history (most recent)."""
    return history[-n:]


def compute_frost_risk_active(data: WeatherData) -> bool:
    """frost_risk_active: min(next_5_days_min_temp) <= 1°C."""
    days = _get_forecast_days(data.forecast, 5)
    if not days:
        return False
    return min(d.temp_min for d in days) <= 1.0


def compute_frost_risk_passed(data: WeatherData) -> bool:
    """frost_risk_passed: min(last_7_days_min_temp) > 1°C AND min(next_5_days_min_temp) > 1°C."""
    history = _get_history_days(data.history, 7)
    forecast = _get_forecast_days(data.forecast, 5)
    if len(history) < 7 or len(forecast) < 5:
        return False
    history_min = min(d.temp_min for d in history)
    forecast_min = min(d.temp_min for d in forecast)
    return history_min > 1.0 and forecast_min > 1.0


def compute_sustained_mild_nights(data: WeatherData) -> bool:
    """sustained_mild_nights: >= 4 of next 5 nights >= 8°C."""
    days = _get_forecast_days(data.forecast, 5)
    if len(days) < 5:
        return False
    mild_count = sum(1 for d in days if d.temp_min >= 8.0)
    return mild_count >= 4


def compute_warm_spell(data: WeatherData) -> bool:
    """warm_spell: >= 3 of next 5 days >= 20°C."""
    days = _get_forecast_days(data.forecast, 5)
    if len(days) < 5:
        return False
    warm_count = sum(1 for d in days if d.temp_max >= 20.0)
    return warm_count >= 3


def compute_heatwave(data: WeatherData) -> bool:
    """heatwave: 3 consecutive days >= 30°C."""
    days = _get_forecast_days(data.forecast, 5)
    if len(days) < 3:
        return False
    consecutive = 0
    for d in days:
        if d.temp_max >= 30.0:
            consecutive += 1
            if consecutive >= 3:
                return True
        else:
            consecutive = 0
    return False


def compute_dry_spell(data: WeatherData) -> bool:
    """dry_spell: 5 consecutive days < 1mm rain AND last 7 days total < 5mm.

    A short rainless stretch after heavy rain isn't a real dry spell.
    We require both a streak of dry days and low overall recent precipitation.
    """
    all_days = list(data.history) + list(data.forecast)
    if len(all_days) < 5:
        return False
    # Check streak: 5 consecutive days < 1mm
    consecutive = 0
    has_streak = False
    for d in all_days:
        if d.precipitation_mm < 1.0:
            consecutive += 1
            if consecutive >= 5:
                has_streak = True
                break
        else:
            consecutive = 0
    if not has_streak:
        return False
    # Also require low total rainfall in recent history
    history = _get_history_days(data.history, 7)
    if history:
        total_rain = sum(d.precipitation_mm for d in history)
        if total_rain >= 5.0:
            return False
    return True


def compute_persistent_rain(data: WeatherData) -> bool:
    """persistent_rain: 3 consecutive days >= 5mm rain (history + forecast)."""
    all_days = list(data.history) + list(data.forecast)
    if len(all_days) < 3:
        return False
    consecutive = 0
    for d in all_days:
        if d.precipitation_mm >= 5.0:
            consecutive += 1
            if consecutive >= 3:
                return True
        else:
            consecutive = 0
    return False


# Registry of all event computation functions
EVENT_COMPUTERS: dict[WeatherEventType, type[None] | object] = {
    WeatherEventType.FROST_RISK_ACTIVE: compute_frost_risk_active,
    WeatherEventType.FROST_RISK_PASSED: compute_frost_risk_passed,
    WeatherEventType.SUSTAINED_MILD_NIGHTS: compute_sustained_mild_nights,
    WeatherEventType.WARM_SPELL: compute_warm_spell,
    WeatherEventType.HEATWAVE: compute_heatwave,
    WeatherEventType.DRY_SPELL: compute_dry_spell,
    WeatherEventType.PERSISTENT_RAIN: compute_persistent_rain,
}


def compute_all_events(data: WeatherData) -> EventState:
    """Compute all weather events from the given data."""
    return EventState(
        frost_risk_active=compute_frost_risk_active(data),
        frost_risk_passed=compute_frost_risk_passed(data),
        sustained_mild_nights=compute_sustained_mild_nights(data),
        warm_spell=compute_warm_spell(data),
        heatwave=compute_heatwave(data),
        dry_spell=compute_dry_spell(data),
        persistent_rain=compute_persistent_rain(data),
        computed_at=datetime.now(),
    )
