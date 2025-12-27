"""Config flow for Commute Briefing integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    DEFAULT_COMMUTE_WINDOW_START,
    DEFAULT_COMMUTE_WINDOW_END,
    DEFAULT_COMMUTE_BASELINE,
    DEFAULT_TRAFFIC_DELAY_THRESHOLD,
    DEFAULT_BUS_GAP_THRESHOLD,
    DEFAULT_DAILY_QUOTA,
    DEFAULT_RESERVED_FOR_MANUAL,
    DEFAULT_MAX_AUTO_CALLS,
    DEFAULT_OFFICE_KEYWORDS,
    DEFAULT_WFH_KEYWORDS,
    DEFAULT_SCRAPER_URL,
    TRANSPORTAPI_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


async def validate_transportapi_credentials(
    hass: HomeAssistant, app_id: str, app_key: str, stop_code: str
) -> dict[str, Any]:
    """Validate TransportAPI credentials by making a test request."""
    session = async_get_clientsession(hass)
    url = f"{TRANSPORTAPI_BASE_URL}/{stop_code}/live.json"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "group": "route",
        "nextbuses": "yes",
    }

    try:
        async with session.get(url, params=params, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                if "departures" in data:
                    return {"success": True, "stop_name": data.get("stop_name", "Unknown")}
                return {"success": False, "error": "invalid_response"}
            elif response.status == 401:
                return {"success": False, "error": "invalid_auth"}
            elif response.status == 403:
                return {"success": False, "error": "quota_exceeded"}
            else:
                return {"success": False, "error": "api_error"}
    except aiohttp.ClientError:
        return {"success": False, "error": "cannot_connect"}
    except Exception as e:
        _LOGGER.error("Unexpected error validating TransportAPI: %s", e)
        return {"success": False, "error": "unknown"}


async def validate_scraper(hass: HomeAssistant, scraper_url: str) -> dict[str, Any]:
    """Validate scraper microservice is accessible."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(f"{scraper_url}/health", timeout=5) as response:
            if response.status == 200:
                return {"success": True}
            return {"success": False, "error": "scraper_error"}
    except aiohttp.ClientError:
        return {"success": False, "error": "scraper_unavailable"}
    except Exception:
        return {"success": False, "error": "scraper_unavailable"}


class CommuteBriefingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Commute Briefing."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._errors: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - TransportAPI credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the credentials
            result = await validate_transportapi_credentials(
                self.hass,
                user_input[CONF_TRANSPORTAPI_APP_ID],
                user_input[CONF_TRANSPORTAPI_APP_KEY],
                user_input[CONF_BUS_STOP_PRIMARY],
            )

            if result["success"]:
                self._data.update(user_input)
                return await self.async_step_commute_settings()
            else:
                errors["base"] = result["error"]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TRANSPORTAPI_APP_ID): str,
                    vol.Required(CONF_TRANSPORTAPI_APP_KEY): str,
                    vol.Required(CONF_BUS_STOP_PRIMARY): str,
                    vol.Optional(CONF_BUS_STOP_BACKUP, default=""): str,
                    vol.Optional(CONF_BUS_ROUTES, default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "signup_url": "https://developer.transportapi.com/signup"
            },
        )

    async def async_step_commute_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle commute time settings."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_integrations()

        return self.async_show_form(
            step_id="commute_settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_COMMUTE_WINDOW_START, default=DEFAULT_COMMUTE_WINDOW_START
                    ): str,
                    vol.Required(
                        CONF_COMMUTE_WINDOW_END, default=DEFAULT_COMMUTE_WINDOW_END
                    ): str,
                    vol.Required(
                        CONF_COMMUTE_BASELINE, default=DEFAULT_COMMUTE_BASELINE
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=180)),
                    vol.Required(
                        CONF_TRAFFIC_DELAY_THRESHOLD,
                        default=DEFAULT_TRAFFIC_DELAY_THRESHOLD,
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
                    vol.Required(
                        CONF_BUS_GAP_THRESHOLD, default=DEFAULT_BUS_GAP_THRESHOLD
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                }
            ),
        )

    async def async_step_integrations(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle integration settings (Waze, Calendar, Notifications)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate scraper if provided
            scraper_url = user_input.get(CONF_SCRAPER_URL, DEFAULT_SCRAPER_URL)
            if scraper_url:
                result = await validate_scraper(self.hass, scraper_url)
                if not result["success"]:
                    _LOGGER.warning(
                        "Scraper not available at %s - will skip validation", scraper_url
                    )
                    # Don't fail, just warn - scraper is optional fallback

            self._data.update(user_input)
            return await self.async_step_quota()

        # Get list of notify services
        notify_services = []
        for service in self.hass.services.async_services().get("notify", {}):
            notify_services.append(f"notify.{service}")

        # Get list of calendar entities
        calendar_entities = [
            entity_id
            for entity_id in self.hass.states.async_entity_ids("calendar")
        ]

        # Get list of sensor entities (for Waze)
        sensor_entities = [
            entity_id
            for entity_id in self.hass.states.async_entity_ids("sensor")
            if "waze" in entity_id.lower() or "travel" in entity_id.lower()
        ]

        return self.async_show_form(
            step_id="integrations",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_WAZE_ENTITY, default=""): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_CALENDAR_ENTITY, default=""): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="calendar")
                    ),
                    vol.Optional(CONF_NOTIFY_SERVICE, default=""): str,
                    vol.Optional(
                        CONF_OFFICE_KEYWORDS, default=DEFAULT_OFFICE_KEYWORDS
                    ): str,
                    vol.Optional(CONF_WFH_KEYWORDS, default=DEFAULT_WFH_KEYWORDS): str,
                    vol.Optional(
                        CONF_SCRAPER_URL, default=DEFAULT_SCRAPER_URL
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_quota(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle quota management settings."""
        if user_input is not None:
            self._data.update(user_input)

            # Create the config entry
            return self.async_create_entry(
                title="Commute Briefing",
                data=self._data,
            )

        return self.async_show_form(
            step_id="quota",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DAILY_QUOTA, default=DEFAULT_DAILY_QUOTA
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1000)),
                    vol.Required(
                        CONF_RESERVED_FOR_MANUAL, default=DEFAULT_RESERVED_FOR_MANUAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=30)),
                    vol.Required(
                        CONF_MAX_AUTO_CALLS, default=DEFAULT_MAX_AUTO_CALLS
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return CommuteBriefingOptionsFlow(config_entry)


class CommuteBriefingOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Commute Briefing."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values from config entry
        data = self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_BUS_STOP_PRIMARY,
                        default=data.get(CONF_BUS_STOP_PRIMARY, ""),
                    ): str,
                    vol.Optional(
                        CONF_BUS_STOP_BACKUP,
                        default=data.get(CONF_BUS_STOP_BACKUP, ""),
                    ): str,
                    vol.Optional(
                        CONF_BUS_ROUTES,
                        default=data.get(CONF_BUS_ROUTES, ""),
                    ): str,
                    vol.Optional(
                        CONF_COMMUTE_WINDOW_START,
                        default=data.get(CONF_COMMUTE_WINDOW_START, DEFAULT_COMMUTE_WINDOW_START),
                    ): str,
                    vol.Optional(
                        CONF_COMMUTE_WINDOW_END,
                        default=data.get(CONF_COMMUTE_WINDOW_END, DEFAULT_COMMUTE_WINDOW_END),
                    ): str,
                    vol.Optional(
                        CONF_COMMUTE_BASELINE,
                        default=data.get(CONF_COMMUTE_BASELINE, DEFAULT_COMMUTE_BASELINE),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=180)),
                    vol.Optional(
                        CONF_TRAFFIC_DELAY_THRESHOLD,
                        default=data.get(CONF_TRAFFIC_DELAY_THRESHOLD, DEFAULT_TRAFFIC_DELAY_THRESHOLD),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
                    vol.Optional(
                        CONF_BUS_GAP_THRESHOLD,
                        default=data.get(CONF_BUS_GAP_THRESHOLD, DEFAULT_BUS_GAP_THRESHOLD),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                    vol.Optional(
                        CONF_DAILY_QUOTA,
                        default=data.get(CONF_DAILY_QUOTA, DEFAULT_DAILY_QUOTA),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1000)),
                    vol.Optional(
                        CONF_RESERVED_FOR_MANUAL,
                        default=data.get(CONF_RESERVED_FOR_MANUAL, DEFAULT_RESERVED_FOR_MANUAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=30)),
                    vol.Optional(
                        CONF_MAX_AUTO_CALLS,
                        default=data.get(CONF_MAX_AUTO_CALLS, DEFAULT_MAX_AUTO_CALLS),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
                    vol.Optional(
                        CONF_NOTIFY_SERVICE,
                        default=data.get(CONF_NOTIFY_SERVICE, ""),
                    ): str,
                    vol.Optional(
                        CONF_OFFICE_KEYWORDS,
                        default=data.get(CONF_OFFICE_KEYWORDS, DEFAULT_OFFICE_KEYWORDS),
                    ): str,
                    vol.Optional(
                        CONF_WFH_KEYWORDS,
                        default=data.get(CONF_WFH_KEYWORDS, DEFAULT_WFH_KEYWORDS),
                    ): str,
                    vol.Optional(
                        CONF_SCRAPER_URL,
                        default=data.get(CONF_SCRAPER_URL, DEFAULT_SCRAPER_URL),
                    ): str,
                }
            ),
        )
