"""Matter-aligned user, credential, schedule, and event actions."""

from __future__ import annotations

from datetime import date, time
import re
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    SERVICE_CREATE_GUEST_PIN,
    SERVICE_GET_ACCESS_LOG,
    SERVICE_GET_USERS,
    SERVICE_INVITE_USER,
)
from .coordinator import SmartSolityCoordinator

ATTR_DEVICE_ID = "device_id"
WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

DEVICE_SCHEMA = vol.Schema({vol.Required(ATTR_DEVICE_ID): cv.string})
INVITE_SCHEMA = DEVICE_SCHEMA.extend(
    {
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=50)),
        vol.Required("phone_number"): vol.All(cv.string, vol.Length(min=3, max=30)),
        vol.Required("role", default="member"): vol.In(("manager", "member")),
    }
)
PIN_SCHEMA = DEVICE_SCHEMA.extend(
    {
        vol.Required("pin"): vol.Match(r"^\d{4,12}$"),
        vol.Required("guest_name"): vol.All(cv.string, vol.Length(min=1, max=50)),
        vol.Required("phone_number"): vol.All(cv.string, vol.Length(min=3, max=30)),
        vol.Required("access_type", default="date_range"): vol.In(
            ("date_range", "weekly", "one_time")
        ),
        vol.Required("start_date"): vol.Match(r"^\d{4}-\d{2}-\d{2}$"),
        vol.Required("end_date"): vol.Match(r"^\d{4}-\d{2}-\d{2}$"),
        vol.Required("start_time"): vol.Match(r"^\d{2}:\d{2}$"),
        vol.Required("end_time"): vol.Match(r"^\d{2}:\d{2}$"),
        vol.Optional("weekdays", default=list(WEEKDAYS)): [vol.In(WEEKDAYS)],
    }
)
LOG_SCHEMA = DEVICE_SCHEMA.extend(
    {
        vol.Optional("limit", default=20): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        )
    }
)


def _door_lock_id(hass: HomeAssistant, ha_device_id: str) -> str:
    device = dr.async_get(hass).async_get(ha_device_id)
    if device is not None:
        for domain, identifier in device.identifiers:
            if domain == DOMAIN:
                return identifier
    raise HomeAssistantError("Selected device is not a Smart Solity door lock")


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as err:
        raise HomeAssistantError(f"Invalid date: {value}") from err


def _parse_time(value: str) -> time:
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise HomeAssistantError(f"Invalid time: {value}")
    return time.fromisoformat(value)


async def async_setup_services(
    hass: HomeAssistant, coordinator: SmartSolityCoordinator
) -> None:
    """Register account actions. Smart Solity allows only one config entry."""

    async def get_users(call: ServiceCall) -> dict[str, Any]:
        return await coordinator.client.async_get_users(
            _door_lock_id(hass, call.data[ATTR_DEVICE_ID])
        )

    async def invite_user(call: ServiceCall) -> dict[str, Any]:
        return await coordinator.client.async_invite_user(
            _door_lock_id(hass, call.data[ATTR_DEVICE_ID]),
            name=call.data["name"],
            phone_number=call.data["phone_number"],
            role=call.data["role"],
        )

    async def create_guest_pin(call: ServiceCall) -> dict[str, Any]:
        start_date = _parse_date(call.data["start_date"])
        end_date = _parse_date(call.data["end_date"])
        start_time = _parse_time(call.data["start_time"])
        end_time = _parse_time(call.data["end_time"])
        if end_date < start_date:
            raise HomeAssistantError("End date must not be before start date")
        if start_date == end_date and end_time <= start_time:
            raise HomeAssistantError("End time must be after start time")
        if call.data["access_type"] == "weekly" and not call.data["weekdays"]:
            raise HomeAssistantError("Select at least one weekday")
        return await coordinator.client.async_create_guest_pin(
            _door_lock_id(hass, call.data[ATTR_DEVICE_ID]),
            pin=call.data["pin"],
            guest_name=call.data["guest_name"],
            phone_number=call.data["phone_number"],
            access_type=call.data["access_type"],
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            weekdays=call.data["weekdays"],
        )

    async def get_access_log(call: ServiceCall) -> dict[str, Any]:
        return await coordinator.client.async_get_access_log(
            _door_lock_id(hass, call.data[ATTR_DEVICE_ID]), limit=call.data["limit"]
        )

    registrations = (
        (SERVICE_GET_USERS, get_users, DEVICE_SCHEMA, SupportsResponse.ONLY),
        (SERVICE_INVITE_USER, invite_user, INVITE_SCHEMA, SupportsResponse.OPTIONAL),
        (
            SERVICE_CREATE_GUEST_PIN,
            create_guest_pin,
            PIN_SCHEMA,
            SupportsResponse.OPTIONAL,
        ),
        (SERVICE_GET_ACCESS_LOG, get_access_log, LOG_SCHEMA, SupportsResponse.ONLY),
    )
    for name, handler, schema, response_support in registrations:
        hass.services.async_register(
            DOMAIN,
            name,
            handler,
            schema=schema,
            supports_response=response_support,
        )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove Smart Solity actions."""
    for service in (
        SERVICE_GET_USERS,
        SERVICE_INVITE_USER,
        SERVICE_CREATE_GUEST_PIN,
        SERVICE_GET_ACCESS_LOG,
    ):
        hass.services.async_remove(DOMAIN, service)
