"""Home Assistant adapter layer.

Handles all communication with Home Assistant:
- Weather data fetch (forecast + history via DWD)
- Calendar sync

NO domain logic here — only data mapping.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

import httpx

from backend.domain.models import DailyWeather, WeatherData


class HomeAssistantAdapter:
    """Adapter for Home Assistant REST API."""

    def __init__(self, base_url: str, token: str, weather_entity: str = "weather.karlsruhe") -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._weather_entity = weather_entity
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def fetch_weather_data(self) -> WeatherData:
        """Fetch forecast and recent history from HA."""
        async with httpx.AsyncClient(timeout=30) as client:
            forecast = await self._fetch_forecast(client)
            history = await self._fetch_history(client)
        return WeatherData(forecast=forecast, history=history)

    async def _fetch_forecast(self, client: httpx.AsyncClient) -> list[DailyWeather]:
        """Fetch daily forecast via weather.get_forecasts service.

        DWD returns: temperature (high), templow (low), precipitation (mm).
        Requires ?return_response query parameter.
        """
        url = f"{self._base_url}/api/services/weather/get_forecasts?return_response"
        resp = await client.post(
            url,
            headers=self._headers,
            json={
                "entity_id": self._weather_entity,
                "type": "daily",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        # Response shape: {service_response: {entity_id: {forecast: [...]}}}
        service_resp = data.get("service_response", data)
        forecasts_raw = service_resp.get(self._weather_entity, {}).get("forecast", [])

        result: list[DailyWeather] = []
        for entry in forecasts_raw[:7]:
            dt = entry.get("datetime", "")[:10]
            result.append(
                DailyWeather(
                    date=date.fromisoformat(dt),
                    temp_min=float(entry.get("templow", entry.get("temperature", 0))),
                    temp_max=float(entry.get("temperature", 0)),
                    precipitation_mm=float(entry.get("precipitation", 0)),
                )
            )
        return result

    async def _fetch_history(self, client: httpx.AsyncClient) -> list[DailyWeather]:
        """Fetch recent temperature history from HA recorder.

        Uses full history (not minimal_response) to get temperature attributes.
        Groups by day to compute daily min/max temp.
        """
        end = date.today()
        start = end - timedelta(days=7)
        url = (
            f"{self._base_url}/api/history/period/{start.isoformat()}"
            f"?filter_entity_id={self._weather_entity}"
            f"&end_time={end.isoformat()}"
            f"&significant_changes_only=0"
        )
        resp = await client.get(url, headers=self._headers)
        resp.raise_for_status()
        data = resp.json()

        if not data or not data[0]:
            return []

        # Group temperature readings by day
        daily_temps: dict[date, list[float]] = defaultdict(list)
        for state in data[0]:
            attrs = state.get("attributes", {})
            dt_str = (state.get("last_changed") or "")[:10]
            if not dt_str:
                continue
            dt = date.fromisoformat(dt_str)
            temp = attrs.get("temperature")
            if temp is not None:
                daily_temps[dt].append(float(temp))

        # DWD doesn't provide historical precipitation in weather state,
        # so we use 0.0 — forecast is the primary precipitation source
        result: list[DailyWeather] = []
        for d in sorted(daily_temps.keys()):
            temps = daily_temps[d]
            result.append(
                DailyWeather(
                    date=d,
                    temp_min=min(temps),
                    temp_max=max(temps),
                    precipitation_mm=0.0,
                )
            )
        return result

    async def sync_to_calendar(
        self,
        calendar_entity: str,
        events: list[dict],
    ) -> None:
        """Sync task events to a HA calendar entity."""
        async with httpx.AsyncClient(timeout=30) as client:
            for event in events:
                await client.post(
                    f"{self._base_url}/api/services/calendar/create_event",
                    headers=self._headers,
                    json={
                        "entity_id": calendar_entity,
                        "summary": event["summary"],
                        "description": event.get("description", ""),
                        "start_date": event["start_date"],
                        "end_date": event["end_date"],
                    },
                )
