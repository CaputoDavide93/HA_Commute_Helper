"""Binary sensor platform for Commute Briefing integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_TRAFFIC_DELAY_THRESHOLD,
    CONF_BUS_GAP_THRESHOLD,
    DEFAULT_TRAFFIC_DELAY_THRESHOLD,
    DEFAULT_BUS_GAP_THRESHOLD,
)
from .coordinator import CommuteBriefingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Commute Briefing binary sensors."""
    coordinator: CommuteBriefingCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        CommuteDayBinarySensor(coordinator, entry),
        CanCallApiAutoBinarySensor(coordinator, entry),
        CanCallApiManualBinarySensor(coordinator, entry),
        CommutePotentialIssueBinarySensor(coordinator, entry),
    ]

    async_add_entities(entities)


class CommuteBriefingBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for Commute Briefing binary sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
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


class CommuteDayBinarySensor(CommuteBriefingBinarySensorBase):
    """Binary sensor for commute day detection."""

    _attr_name = "Commute Day"
    _attr_icon = "mdi:office-building"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_commute_day"

    @property
    def is_on(self) -> bool:
        """Return true if today is a commute day."""
        data = self.coordinator.data or {}
        return data.get("is_commute_day", False)


class CanCallApiAutoBinarySensor(CommuteBriefingBinarySensorBase):
    """Binary sensor for automatic API call availability."""

    _attr_name = "Can Call API (Auto)"
    _attr_icon = "mdi:api"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_can_call_api_auto"

    @property
    def is_on(self) -> bool:
        """Return true if automatic API calls are allowed."""
        return self.coordinator.can_call_api_auto()


class CanCallApiManualBinarySensor(CommuteBriefingBinarySensorBase):
    """Binary sensor for manual API call availability."""

    _attr_name = "Can Call API (Manual)"
    _attr_icon = "mdi:hand-pointing-up"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_can_call_api_manual"

    @property
    def is_on(self) -> bool:
        """Return true if manual API calls are allowed."""
        return self.coordinator.can_call_api_manual()


class CommutePotentialIssueBinarySensor(CommuteBriefingBinarySensorBase):
    """Binary sensor for potential commute issues."""

    _attr_name = "Potential Issue"
    _attr_icon = "mdi:alert"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_potential_issue"

    @property
    def is_on(self) -> bool:
        """Return true if there's a potential commute issue."""
        data = self.coordinator.data or {}
        config = self.coordinator.config

        traffic_delay = data.get("traffic_delay", 0)
        delay_threshold = config.get(
            CONF_TRAFFIC_DELAY_THRESHOLD, DEFAULT_TRAFFIC_DELAY_THRESHOLD
        )

        next_bus = data.get("next_bus")
        bus_mins = next_bus.get("due_mins", 999) if next_bus else 999
        bus_threshold = config.get(CONF_BUS_GAP_THRESHOLD, DEFAULT_BUS_GAP_THRESHOLD)

        return (
            traffic_delay >= delay_threshold
            or bus_mins >= bus_threshold
            or bus_mins == 999
        )
