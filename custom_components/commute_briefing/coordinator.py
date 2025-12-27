"""Data coordinator for Commute Briefing integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_TRANSPORTAPI_APP_ID,
    CONF_TRANSPORTAPI_APP_KEY,
    CONF_BUS_STOP_PRIMARY,
    CONF_BUS_STOP_BACKUP,
    CONF_BUS_ROUTES,
    CONF_COMMUTE_WINDOW_START,
    CONF_COMMUTE_WINDOW_END,
    CONF_COMMUTE_BASELINE,
    CONF_TRAFFIC_DELAY_THRESHOLD,
    CONF_BUS_GAP_THRESHOLD,
    CONF_DAILY_QUOTA,
    CONF_RESERVED_FOR_MANUAL,
    CONF_MAX_AUTO_CALLS,
    CONF_NOTIFY_SERVICE,
    CONF_CALENDAR_ENTITY,
    CONF_OFFICE_KEYWORDS,
    CONF_WFH_KEYWORDS,
    CONF_WAZE_ENTITY,
    CONF_SCRAPER_URL,
    TRANSPORTAPI_BASE_URL,
    SOURCE_TRANSPORTAPI,
    SOURCE_SCRAPER,
    SOURCE_NONE,
    DEFAULT_COMMUTE_BASELINE,
    DEFAULT_TRAFFIC_DELAY_THRESHOLD,
    DEFAULT_BUS_GAP_THRESHOLD,
    DEFAULT_DAILY_QUOTA,
    DEFAULT_RESERVED_FOR_MANUAL,
    DEFAULT_MAX_AUTO_CALLS,
    DEFAULT_SCRAPER_URL,
)

_LOGGER = logging.getLogger(__name__)


class CommuteBriefingCoordinator(DataUpdateCoordinator):
    """Coordinator to manage commute briefing data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),  # Background refresh interval
        )
        self.entry = entry
        self.config = entry.data

        # Runtime state
        self._calls_today: int = 0
        self._auto_calls_today: int = 0
        self._last_reset_date: datetime | None = None
        self._last_check_time: datetime | None = None
        self._bus_data: dict[str, Any] = {}
        self._data_source: str = SOURCE_NONE

    @property
    def calls_today(self) -> int:
        """Return number of API calls made today."""
        self._check_daily_reset()
        return self._calls_today

    @property
    def auto_calls_today(self) -> int:
        """Return number of automatic API calls made today."""
        self._check_daily_reset()
        return self._auto_calls_today

    @property
    def data_source(self) -> str:
        """Return the current data source."""
        return self._data_source

    @property
    def last_check_time(self) -> datetime | None:
        """Return the last check time."""
        return self._last_check_time

    def _check_daily_reset(self) -> None:
        """Check if we need to reset daily counters."""
        now = dt_util.now()
        if self._last_reset_date is None or self._last_reset_date.date() != now.date():
            self._calls_today = 0
            self._auto_calls_today = 0
            self._last_reset_date = now
            _LOGGER.info("Daily API counters reset")

    def can_call_api_auto(self) -> bool:
        """Check if we can make an automatic API call."""
        self._check_daily_reset()
        quota = self.config.get(CONF_DAILY_QUOTA, DEFAULT_DAILY_QUOTA)
        reserved = self.config.get(CONF_RESERVED_FOR_MANUAL, DEFAULT_RESERVED_FOR_MANUAL)
        max_auto = self.config.get(CONF_MAX_AUTO_CALLS, DEFAULT_MAX_AUTO_CALLS)

        return (
            self._calls_today < (quota - reserved)
            and self._auto_calls_today < max_auto
        )

    def can_call_api_manual(self) -> bool:
        """Check if we can make a manual API call."""
        self._check_daily_reset()
        quota = self.config.get(CONF_DAILY_QUOTA, DEFAULT_DAILY_QUOTA)
        return self._calls_today < quota

    async def _fetch_transportapi(self, stop_code: str) -> dict[str, Any] | None:
        """Fetch data from TransportAPI."""
        session = async_get_clientsession(self.hass)
        url = f"{TRANSPORTAPI_BASE_URL}/{stop_code}/live.json"
        params = {
            "app_id": self.config[CONF_TRANSPORTAPI_APP_ID],
            "app_key": self.config[CONF_TRANSPORTAPI_APP_KEY],
            "group": "route",
            "nextbuses": "yes",
        }

        try:
            async with session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    self._calls_today += 1
                    return data
                else:
                    _LOGGER.warning(
                        "TransportAPI returned status %s", response.status
                    )
                    return None
        except aiohttp.ClientError as e:
            _LOGGER.error("Error fetching from TransportAPI: %s", e)
            return None

    async def _fetch_scraper(self, stop_code: str) -> dict[str, Any] | None:
        """Fetch data from the scraper microservice."""
        scraper_url = self.config.get(CONF_SCRAPER_URL, DEFAULT_SCRAPER_URL)
        if not scraper_url:
            return None

        session = async_get_clientsession(self.hass)
        url = f"{scraper_url}/lothian/stop/{stop_code}"

        try:
            async with session.get(url, timeout=60) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    _LOGGER.warning("Scraper returned status %s", response.status)
                    return None
        except aiohttp.ClientError as e:
            _LOGGER.error("Error fetching from scraper: %s", e)
            return None

    def _parse_transportapi_departures(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse TransportAPI response into standardized departures."""
        departures = []
        raw_departures = data.get("departures", {})
        allowlist = [r.strip() for r in self.config.get(CONF_BUS_ROUTES, "").split(",") if r.strip()]

        for route, deps in raw_departures.items():
            if allowlist and route not in allowlist:
                continue

            for dep in deps:
                aimed = dep.get("aimed_departure_time", "")
                expected = dep.get("expected_departure_time", aimed)
                best = dep.get("best_departure_estimate", expected or aimed)

                # Calculate minutes until departure
                due_mins = None
                if best:
                    try:
                        now = dt_util.now()
                        dep_time = datetime.strptime(best, "%H:%M")
                        dep_dt = now.replace(
                            hour=dep_time.hour,
                            minute=dep_time.minute,
                            second=0,
                            microsecond=0,
                        )
                        if dep_dt < now:
                            dep_dt += timedelta(days=1)
                        due_mins = int((dep_dt - now).total_seconds() / 60)
                    except ValueError:
                        pass

                # Determine status
                status = "Scheduled"
                if aimed and expected and aimed != expected:
                    try:
                        aimed_t = datetime.strptime(aimed, "%H:%M")
                        expected_t = datetime.strptime(expected, "%H:%M")
                        if expected_t > aimed_t:
                            status = "Late"
                        elif expected_t < aimed_t:
                            status = "Early"
                        else:
                            status = "On time"
                    except ValueError:
                        status = "On time"
                elif expected:
                    status = "On time"

                departures.append({
                    "route": route,
                    "due_mins": due_mins,
                    "aimed": aimed,
                    "expected": expected,
                    "destination": dep.get("direction", ""),
                    "status": status,
                    "is_realtime": expected is not None and expected != aimed,
                })

        # Sort by due_mins
        departures.sort(key=lambda x: x.get("due_mins") or 999)
        return departures

    def _parse_scraper_departures(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse scraper response into standardized departures."""
        departures = data.get("departures", [])
        allowlist = [r.strip() for r in self.config.get(CONF_BUS_ROUTES, "").split(",") if r.strip()]

        if allowlist:
            departures = [d for d in departures if d.get("route") in allowlist]

        # Sort by due_mins
        departures.sort(key=lambda x: x.get("due_mins") or 999)
        return departures

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the appropriate source."""
        self._check_daily_reset()
        self._last_check_time = dt_util.now()

        stop_code = self.config.get(CONF_BUS_STOP_PRIMARY)
        if not stop_code:
            return {"departures": [], "source": SOURCE_NONE}

        departures = []
        source = SOURCE_NONE

        # Try TransportAPI first if quota allows
        if self.can_call_api_auto():
            data = await self._fetch_transportapi(stop_code)
            if data and data.get("departures"):
                departures = self._parse_transportapi_departures(data)
                source = SOURCE_TRANSPORTAPI
                self._auto_calls_today += 1

        # Fall back to scraper if needed
        if not departures:
            data = await self._fetch_scraper(stop_code)
            if data and data.get("departures"):
                departures = self._parse_scraper_departures(data)
                source = SOURCE_SCRAPER

        self._bus_data = {"departures": departures, "source": source}
        self._data_source = source

        # Get Waze data
        waze_entity = self.config.get(CONF_WAZE_ENTITY)
        waze_minutes = None
        if waze_entity:
            state = self.hass.states.get(waze_entity)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    waze_minutes = float(state.state)
                except ValueError:
                    pass

        # Calculate traffic delay
        baseline = self.config.get(CONF_COMMUTE_BASELINE, DEFAULT_COMMUTE_BASELINE)
        traffic_delay = max(0, (waze_minutes or baseline) - baseline)

        # Check if it's a commute day
        is_commute_day = await self._check_commute_day()

        return {
            "departures": departures,
            "source": source,
            "next_bus": departures[0] if departures else None,
            "waze_minutes": waze_minutes,
            "traffic_delay": traffic_delay,
            "is_commute_day": is_commute_day,
            "calls_today": self._calls_today,
            "auto_calls_today": self._auto_calls_today,
            "last_check": self._last_check_time.isoformat() if self._last_check_time else None,
        }

    async def _check_commute_day(self) -> bool:
        """Check if today is a commute day based on calendar."""
        calendar_entity = self.config.get(CONF_CALENDAR_ENTITY)
        if not calendar_entity:
            return True  # Default to True if no calendar configured

        state = self.hass.states.get(calendar_entity)
        if not state or state.state != "on":
            return False

        # Check keywords
        event_title = (state.attributes.get("message") or "").lower()
        office_keywords = [k.strip().lower() for k in self.config.get(CONF_OFFICE_KEYWORDS, "").split(",") if k.strip()]
        wfh_keywords = [k.strip().lower() for k in self.config.get(CONF_WFH_KEYWORDS, "").split(",") if k.strip()]

        is_wfh = any(kw in event_title for kw in wfh_keywords)
        is_office = any(kw in event_title for kw in office_keywords)

        return is_office and not is_wfh

    async def async_manual_refresh(self) -> None:
        """Perform a manual refresh with higher quota allowance."""
        self._check_daily_reset()
        self._last_check_time = dt_util.now()

        stop_code = self.config.get(CONF_BUS_STOP_PRIMARY)
        if not stop_code:
            return

        departures = []
        source = SOURCE_NONE

        # Try TransportAPI first if quota allows (manual has higher limit)
        if self.can_call_api_manual():
            data = await self._fetch_transportapi(stop_code)
            if data and data.get("departures"):
                departures = self._parse_transportapi_departures(data)
                source = SOURCE_TRANSPORTAPI

        # Fall back to scraper if needed
        if not departures:
            data = await self._fetch_scraper(stop_code)
            if data and data.get("departures"):
                departures = self._parse_scraper_departures(data)
                source = SOURCE_SCRAPER

        self._bus_data = {"departures": departures, "source": source}
        self._data_source = source

        # Trigger coordinator update
        await self.async_refresh()

        # Send notification
        await self.async_send_notification()

    async def async_send_notification(self) -> None:
        """Send a commute briefing notification."""
        notify_service = self.config.get(CONF_NOTIFY_SERVICE)
        if not notify_service:
            _LOGGER.debug("No notification service configured")
            return

        data = self.data or {}
        waze_minutes = data.get("waze_minutes")
        traffic_delay = data.get("traffic_delay", 0)
        next_bus = data.get("next_bus")
        source = data.get("source", SOURCE_NONE)

        # Build message
        delay_sign = "+" if traffic_delay > 0 else ""

        if waze_minutes is not None:
            traffic_line = f"Traffic: {int(waze_minutes)} min ({delay_sign}{int(traffic_delay)} vs usual)"
        else:
            traffic_line = "Traffic: No data available"

        if next_bus:
            bus_line = (
                f"🚌 Bus: Route {next_bus['route']} in {next_bus['due_mins']} min"
                f"{' at ' + next_bus['aimed'] if next_bus.get('aimed') else ''}"
                f" — {next_bus['status']} ({source})"
            )
        else:
            bus_line = "🚌 Bus: No data available"

        message = f"{traffic_line}\n{bus_line}"

        # Send notification
        try:
            service_parts = notify_service.split(".", 1)
            if len(service_parts) == 2:
                await self.hass.services.async_call(
                    service_parts[0],
                    service_parts[1],
                    {
                        "title": "🚗 Commute Briefing",
                        "message": message,
                        "data": {
                            "push": {"sound": {"name": "default", "critical": 0}},
                            "actions": [
                                {
                                    "action": "COMMUTE_REFRESH",
                                    "title": "Refresh",
                                }
                            ],
                        },
                    },
                )
                _LOGGER.info("Commute notification sent")
        except Exception as e:
            _LOGGER.error("Failed to send notification: %s", e)

    async def async_reset_daily_counters(self) -> None:
        """Reset daily API counters."""
        self._calls_today = 0
        self._auto_calls_today = 0
        self._last_reset_date = dt_util.now()
        _LOGGER.info("Daily API counters manually reset")
        await self.async_refresh()
