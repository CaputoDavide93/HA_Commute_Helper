"""Button platform for Commute Briefing integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CommuteBriefingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Commute Briefing buttons."""
    coordinator: CommuteBriefingCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        RefreshCommuteButton(coordinator, entry),
        SendNotificationButton(coordinator, entry),
        ResetCountersButton(coordinator, entry),
    ]

    async_add_entities(entities)


class CommuteBriefingButtonBase(CoordinatorEntity, ButtonEntity):
    """Base class for Commute Briefing buttons."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Commute Briefing",
            manufacturer="Custom",
            model="Commute Briefing",
            sw_version="1.0.0",
        )


class RefreshCommuteButton(CommuteBriefingButtonBase):
    """Button to manually refresh commute data."""

    _attr_name = "Refresh Commute"
    _attr_icon = "mdi:refresh"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_refresh_commute"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_manual_refresh()


class SendNotificationButton(CommuteBriefingButtonBase):
    """Button to send a commute notification."""

    _attr_name = "Send Notification"
    _attr_icon = "mdi:message-badge"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_send_notification"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_send_notification()


class ResetCountersButton(CommuteBriefingButtonBase):
    """Button to reset daily API counters."""

    _attr_name = "Reset API Counters"
    _attr_icon = "mdi:counter"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_reset_counters"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_reset_daily_counters()
