"""Sensor entities for Smart Solity."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SmartSolityCoordinator
from .entity import SmartSolityEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[SmartSolityCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    def _add_new_devices() -> None:
        new_ids = set(coordinator.data) - known
        if new_ids:
            known.update(new_ids)
            async_add_entities(
                SmartSolityBatterySensor(coordinator, device_id)
                for device_id in new_ids
            )

    _add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_devices))


class SmartSolityBatterySensor(SmartSolityEntity, SensorEntity):
    """Door-lock battery level."""

    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SmartSolityCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_battery"

    @property
    def native_value(self) -> int | None:
        return self.device.battery
