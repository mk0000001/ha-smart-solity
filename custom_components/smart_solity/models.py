"""Data models for Smart Solity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _text(value: Any) -> str:
    return "" if value is None else str(value)


@dataclass(frozen=True, slots=True)
class SmartSolityDevice:
    """A door lock returned by the Smart Solity cloud."""

    device_id: str
    name: str
    status: str
    battery: int | None
    manufacturer: str
    model: str
    firmware: str
    gateway_status: str
    wifi_enabled: bool
    gateway_enabled: bool
    functions: dict[str, Any] = field(compare=False, hash=False, repr=False)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SmartSolityDevice:
        """Create a device from an API object."""
        raw_battery = value.get("battery")
        try:
            battery = int(raw_battery) if raw_battery not in (None, "") else None
        except (TypeError, ValueError):
            battery = None

        device_id = _text(value.get("myDeviceId"))
        if not device_id:
            raise ValueError("Smart Solity device response has no myDeviceId")

        functions = value.get("myDeviceFunctions")
        return cls(
            device_id=device_id,
            name=_text(value.get("myDeviceNickName")) or "Smart Solity",
            status=_text(value.get("lockerStatus")),
            battery=battery,
            manufacturer=_text(value.get("myDeviceMakerName")) or "Solity",
            model=_text(value.get("myDeviceModelName")) or "Door lock",
            firmware=_text(value.get("myDeviceFirmwareVersion")),
            gateway_status=_text(value.get("gatewayConnStatus")),
            wifi_enabled=_text(value.get("myDeviceWifiYn")).upper() == "Y",
            gateway_enabled=_text(value.get("myDeviceGatewayYn")).upper() == "Y",
            functions=functions if isinstance(functions, dict) else {},
        )
