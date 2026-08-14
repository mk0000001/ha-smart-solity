"""Base entity for Smart Solity."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartSolityCoordinator
from .models import SmartSolityDevice


class SmartSolityEntity(CoordinatorEntity[SmartSolityCoordinator]):
    """Base class shared by Smart Solity entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartSolityCoordinator, device_id: str) -> None:
        super().__init__(coordinator, context=device_id)
        self.device_id = device_id

    @property
    def device(self) -> SmartSolityDevice:
        return self.coordinator.data[self.device_id]

    @property
    def available(self) -> bool:
        return super().available and self.device_id in self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        device = self.device
        return DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            manufacturer=device.manufacturer,
            model=device.model,
            sw_version=device.firmware or None,
            name=device.name,
        )
