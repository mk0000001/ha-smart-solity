"""Update coordinator for Smart Solity."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartSolityAuthError, SmartSolityClient, SmartSolityError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import SmartSolityDevice

_LOGGER = logging.getLogger(__name__)


class SmartSolityCoordinator(DataUpdateCoordinator[dict[str, SmartSolityDevice]]):
    """Coordinate a single account-wide cloud poll."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: SmartSolityClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            always_update=False,
        )
        self.client = client

    async def _async_setup(self) -> None:
        try:
            await self.client.async_refresh_tokens()
        except SmartSolityAuthError as err:
            raise ConfigEntryAuthFailed from err
        except SmartSolityError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_update_data(self) -> dict[str, SmartSolityDevice]:
        try:
            return await self.client.async_get_devices()
        except SmartSolityAuthError as err:
            raise ConfigEntryAuthFailed from err
        except SmartSolityError as err:
            raise UpdateFailed(str(err)) from err

    async def async_control(self, device_id: str, *, lock: bool) -> None:
        """Connect, issue a command, then ask the cloud for fresh state."""
        try:
            await self.client.async_connect_gateway(device_id)
            if lock:
                await self.client.async_lock(device_id)
            else:
                await self.client.async_unlock(device_id)
            await asyncio.sleep(1)
            await self.client.async_request_status(device_id)
            await asyncio.sleep(1)
        except SmartSolityAuthError as err:
            raise ConfigEntryAuthFailed from err
        except SmartSolityError as err:
            raise HomeAssistantError(str(err)) from err
        await self.async_request_refresh()
