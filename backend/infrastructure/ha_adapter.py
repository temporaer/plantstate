"""Home Assistant adapter layer.

Handles all communication with Home Assistant:
- Weather data fetch (forecast + history via DWD)
- Calendar sync

NO domain logic here — only data mapping.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import suppress
from datetime import date, timedelta

import httpx

from backend.domain.models import DailyWeather, WeatherData


class HomeAssistantAdapter:
    """Adapter for Home Assistant REST API."""

    def __init__(
        self, base_url: str, token: str,
        weather_entity: str = "weather.karlsruhe",
    ) -> None:
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
        """Fetch recent weather history from HA recorder.

        Uses full history (not minimal_response) to get temperature attributes.
        Groups by day to compute daily min/max temp and precipitation sum.
        Also tries to fetch precipitation from a dedicated DWD sensor.
        """
        end = date.today()
        start = end - timedelta(days=7)

        # Fetch weather entity history (temperature + possibly precipitation)
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

        # Group temperature and precipitation readings by day
        daily_temps: dict[date, list[float]] = defaultdict(list)
        daily_precip: dict[date, float] = defaultdict(float)
        for state in data[0]:
            attrs = state.get("attributes", {})
            dt_str = (state.get("last_changed") or "")[:10]
            if not dt_str:
                continue
            dt = date.fromisoformat(dt_str)
            temp = attrs.get("temperature")
            if temp is not None:
                daily_temps[dt].append(float(temp))
            # DWD may provide precipitation as an attribute
            precip = attrs.get("precipitation")
            if precip is not None:
                with suppress(ValueError, TypeError):
                    daily_precip[dt] = max(daily_precip[dt], float(precip))

        # Also try a dedicated precipitation sensor (DWD pattern)
        # e.g. weather.karlsruhe → sensor.karlsruhe_precipitation
        precip_entity = self._weather_entity.replace("weather.", "sensor.") + "_precipitation"
        try:
            precip_url = (
                f"{self._base_url}/api/history/period/{start.isoformat()}"
                f"?filter_entity_id={precip_entity}"
                f"&end_time={end.isoformat()}"
                f"&significant_changes_only=0"
            )
            precip_resp = await client.get(precip_url, headers=self._headers)
            precip_resp.raise_for_status()
            precip_data = precip_resp.json()
            if precip_data and precip_data[0]:
                for state in precip_data[0]:
                    dt_str = (state.get("last_changed") or "")[:10]
                    val = state.get("state")
                    if dt_str and val not in (None, "unknown", "unavailable"):
                        dt = date.fromisoformat(dt_str)
                        with suppress(ValueError, TypeError):
                            daily_precip[dt] = max(daily_precip[dt], float(val))
        except (httpx.HTTPStatusError, httpx.ConnectError):
            pass  # Sensor may not exist

        result: list[DailyWeather] = []
        for d in sorted(daily_temps.keys()):
            temps = daily_temps[d]
            result.append(
                DailyWeather(
                    date=d,
                    temp_min=min(temps),
                    temp_max=max(temps),
                    precipitation_mm=daily_precip.get(d, 0.0),
                )
            )
        return result

    async def get_calendar_events(
        self,
        calendar_entity: str,
        start: date,
        end: date,
    ) -> list[dict]:
        """Fetch existing calendar events in a date range."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/services/calendar/get_events?return_response",
                    headers=self._headers,
                    json={
                        "entity_id": calendar_entity,
                        "start_date_time": f"{start.isoformat()}T00:00:00",
                        "end_date_time": f"{end.isoformat()}T23:59:59",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                service_resp = data.get("service_response", data)
                return service_resp.get(calendar_entity, {}).get("events", [])
            except httpx.HTTPStatusError:
                # Calendar entity may not exist yet
                return []

    async def sync_to_calendar(
        self,
        calendar_entity: str,
        events: list[dict],
    ) -> int:
        """Sync task events to a HA calendar entity (idempotent).

        Checks existing events by summary to avoid duplicates.
        Returns number of newly created events.
        """
        if not events:
            return 0

        # Find date range of events to sync
        all_starts = [date.fromisoformat(e["start_date"]) for e in events]
        all_ends = [date.fromisoformat(e["end_date"]) for e in events]
        range_start = min(all_starts)
        range_end = max(all_ends)

        # Fetch existing events to avoid duplicates
        existing = await self.get_calendar_events(
            calendar_entity, range_start, range_end,
        )
        existing_summaries = {e.get("summary", "") for e in existing}

        created = 0
        async with httpx.AsyncClient(timeout=30) as client:
            for event in events:
                if event["summary"] in existing_summaries:
                    continue
                try:
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
                    created += 1
                except httpx.HTTPStatusError:
                    # Calendar entity may not exist — skip silently
                    break
        return created

    async def update_sensor(
        self,
        entity_id: str,
        state: str,
        attributes: dict,
    ) -> bool:
        """Set a sensor state via the HA API (creates it if needed)."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/states/{entity_id}",
                    headers=self._headers,
                    json={
                        "state": state,
                        "attributes": {
                            "friendly_name": attributes.get("friendly_name", entity_id),
                            "icon": attributes.get("icon", "mdi:flower"),
                            "unit_of_measurement": attributes.get("unit_of_measurement"),
                            **attributes,
                        },
                    },
                )
                resp.raise_for_status()
                return True
            except (httpx.HTTPStatusError, httpx.ConnectError):
                return False

    async def list_conversation_agents(self) -> list[dict]:
        """List available HA conversation agents via REST API."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/api/states",
                    headers=self._headers,
                )
                resp.raise_for_status()
                states = resp.json()
                agents = []
                for s in states:
                    eid = s.get("entity_id", "")
                    if eid.startswith("conversation."):
                        agents.append({
                            "agent_id": eid,
                            "name": s.get("attributes", {}).get(
                                "friendly_name", eid,
                            ),
                        })
                return agents
            except (httpx.HTTPStatusError, httpx.ConnectError):
                return []

    async def conversation_process(
        self, agent_id: str, text: str,
    ) -> str | None:
        """Send text to an HA conversation agent and return the response."""
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/conversation/process",
                    headers=self._headers,
                    json={"agent_id": agent_id, "text": text},
                )
                resp.raise_for_status()
                data = resp.json()
                speech = (
                    data.get("response", {})
                    .get("speech", {})
                    .get("plain", {})
                    .get("speech", "")
                )
                return speech or None
            except (httpx.HTTPStatusError, httpx.ConnectError):
                return None
