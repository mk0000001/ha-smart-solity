"""Lock entities for Smart Solity."""

from __future__ import annotations

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import STATUS_LOCKED, STATUS_UNLOCKED
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
            async_add_entities(SmartSolityLock(coordinator, device_id) for device_id in new_ids)

    _add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_devices))


class SmartSolityLock(SmartSolityEntity, LockEntity):
    """A Smart Solity door lock."""

    _attr_name = None

    def __init__(self, coordinator: SmartSolityCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_lock"

    @property
    def is_locked(self) -> bool | None:
        if self.device.status == STATUS_LOCKED:
            return True
        if self.device.status == STATUS_UNLOCKED:
            return False
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | bool]:
        device = self.device
        functions = device.functions
        return {
            "gateway_status": device.gateway_status,
            "wifi_enabled": device.wifi_enabled,
            "gateway_enabled": device.gateway_enabled,
            "supports_pin": bool(functions.get("cmdSetPassword")),
            "supports_one_time_pin": bool(functions.get("cmdSetOnePass")),
            "supports_visitor_pin": bool(functions.get("cmdSetVisitorPass")),
            "supports_card": bool(functions.get("cmdSetCard")),
            "supports_fingerprint": bool(functions.get("cmdSetFingerPrint")),
            "supports_face": bool(functions.get("cmdSetFacePrint")),
            "supports_dual_auth": bool(functions.get("cmdDualAuth")),
        }

    async def async_lock(self, **kwargs: object) -> None:
        await self.coordinator.async_control(self.device_id, lock=True)

    async def async_unlock(self, **kwargs: object) -> None:
        await self.coordinator.async_control(self.device_id, lock=False)
