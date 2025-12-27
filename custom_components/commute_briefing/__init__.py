"""
Commute Briefing Integration for Home Assistant.

A free-first, multi-source commute briefing solution that combines:
- Traffic ETA via Waze Travel Time (free)
- Bus departures via TransportAPI (limited free tier)
- Emergency fallback via local scraping microservice
"""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_TRANSPORTAPI_APP_ID, CONF_TRANSPORTAPI_APP_KEY
from .coordinator import CommuteBriefingCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Commute Briefing from a config entry."""
    _LOGGER.info("Setting up Commute Briefing integration")

    # Store coordinator
    coordinator = CommuteBriefingCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass, coordinator)

    # Listen for config updates
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Commute Briefing integration")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_services(hass: HomeAssistant, coordinator: CommuteBriefingCoordinator) -> None:
    """Set up services for the integration."""

    async def handle_refresh_commute(call) -> None:
        """Handle the refresh commute service call."""
        await coordinator.async_manual_refresh()

    async def handle_send_notification(call) -> None:
        """Handle the send notification service call."""
        await coordinator.async_send_notification()

    async def handle_reset_counters(call) -> None:
        """Handle the reset counters service call."""
        await coordinator.async_reset_daily_counters()

    hass.services.async_register(DOMAIN, "refresh_commute", handle_refresh_commute)
    hass.services.async_register(DOMAIN, "send_notification", handle_send_notification)
    hass.services.async_register(DOMAIN, "reset_counters", handle_reset_counters)
