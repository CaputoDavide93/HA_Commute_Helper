"""Sensor platform for Commute Briefing integration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SOURCE_NONE
from .coordinator import CommuteBriefingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Commute Briefing sensors."""
    coordinator: CommuteBriefingCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        NextBusMinutesSensor(coordinator, entry),
        NextBusTimeSensor(coordinator, entry),
        NextBusRouteSensor(coordinator, entry),
        NextBusStatusSensor(coordinator, entry),
        TrafficMinutesSensor(coordinator, entry),
        TrafficDelaySensor(coordinator, entry),
        BusDataSourceSensor(coordinator, entry),
        ApiCallsTodaySensor(coordinator, entry),
        AutoApiCallsTodaySensor(coordinator, entry),
        LastCheckTimeSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class CommuteBriefingSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Commute Briefing sensors."""

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


class NextBusMinutesSensor(CommuteBriefingSensorBase):
    """Sensor for next bus minutes."""

    _attr_name = "Next Bus Minutes"
    _attr_icon = "mdi:bus-clock"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_bus_minutes"

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        data = self.coordinator.data or {}
        next_bus = data.get("next_bus")
        if next_bus:
            return next_bus.get("due_mins")
        return None


class NextBusTimeSensor(CommuteBriefingSensorBase):
    """Sensor for next bus time."""

    _attr_name = "Next Bus Time"
    _attr_icon = "mdi:clock"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_bus_time"

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        data = self.coordinator.data or {}
        next_bus = data.get("next_bus")
        if next_bus:
            return next_bus.get("expected") or next_bus.get("aimed")
        return None


class NextBusRouteSensor(CommuteBriefingSensorBase):
    """Sensor for next bus route."""

    _attr_name = "Next Bus Route"
    _attr_icon = "mdi:bus"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_bus_route"

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        data = self.coordinator.data or {}
        next_bus = data.get("next_bus")
        if next_bus:
            return next_bus.get("route")
        return None


class NextBusStatusSensor(CommuteBriefingSensorBase):
    """Sensor for next bus status."""

    _attr_name = "Next Bus Status"
    _attr_icon = "mdi:information"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_bus_status"

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        data = self.coordinator.data or {}
        next_bus = data.get("next_bus")
        if next_bus:
            return next_bus.get("status")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        data = self.coordinator.data or {}
        next_bus = data.get("next_bus")
        if next_bus:
            return {
                "is_realtime": next_bus.get("is_realtime", False),
                "destination": next_bus.get("destination"),
            }
        return {}


class TrafficMinutesSensor(CommuteBriefingSensorBase):
    """Sensor for traffic/travel time minutes."""

    _attr_name = "Traffic Time"
    _attr_icon = "mdi:car"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_traffic_minutes"

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        data = self.coordinator.data or {}
        return data.get("waze_minutes")


class TrafficDelaySensor(CommuteBriefingSensorBase):
    """Sensor for traffic delay vs baseline."""

    _attr_name = "Traffic Delay"
    _attr_icon = "mdi:car-clock"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_traffic_delay"

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        data = self.coordinator.data or {}
        return data.get("traffic_delay")


class BusDataSourceSensor(CommuteBriefingSensorBase):
    """Sensor for bus data source."""

    _attr_name = "Bus Data Source"
    _attr_icon = "mdi:database"

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_bus_data_source"

    @property
    def native_value(self) -> str:
        """Return the state."""
        data = self.coordinator.data or {}
        return data.get("source", SOURCE_NONE)


class ApiCallsTodaySensor(CommuteBriefingSensorBase):
    """Sensor for API calls made today."""

    _attr_name = "API Calls Today"
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_api_calls_today"

    @property
    def native_value(self) -> int:
        """Return the state."""
        data = self.coordinator.data or {}
        return data.get("calls_today", 0)


class AutoApiCallsTodaySensor(CommuteBriefingSensorBase):
    """Sensor for automatic API calls made today."""

    _attr_name = "Auto API Calls Today"
    _attr_icon = "mdi:robot"
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_auto_api_calls_today"

    @property
    def native_value(self) -> int:
        """Return the state."""
        data = self.coordinator.data or {}
        return data.get("auto_calls_today", 0)


class LastCheckTimeSensor(CommuteBriefingSensorBase):
    """Sensor for last check time."""

    _attr_name = "Last Check"
    _attr_icon = "mdi:clock-check"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: CommuteBriefingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_check"

    @property
    def native_value(self) -> datetime | None:
        """Return the state."""
        data = self.coordinator.data or {}
        last_check = data.get("last_check")
        if last_check:
            return datetime.fromisoformat(last_check)
        return None
