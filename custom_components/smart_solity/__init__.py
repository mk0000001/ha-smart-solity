"""The unofficial Smart Solity cloud integration."""

from __future__ import annotations

from collections.abc import Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartSolityClient
from .const import (
    CONF_MEMBER_NAME,
    CONF_PHONE_TOKEN,
    CONF_TOKEN,
    CONF_TOKEN_PASSWORD,
    PLATFORMS,
)
from .coordinator import SmartSolityCoordinator
from .services import async_setup_services, async_unload_services

type SmartSolityConfigEntry = ConfigEntry[SmartSolityCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SmartSolityConfigEntry) -> bool:
    data: Mapping[str, str] = entry.data

    async def _store_tokens(token: str, token_password: str) -> None:
        if (
            entry.data.get(CONF_TOKEN) == token
            and entry.data.get(CONF_TOKEN_PASSWORD) == token_password
        ):
            return
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_TOKEN: token,
                CONF_TOKEN_PASSWORD: token_password,
            },
        )

    client = SmartSolityClient(
        async_get_clientsession(hass),
        token=data[CONF_TOKEN],
        token_password=data[CONF_TOKEN_PASSWORD],
        phone_token=data[CONF_PHONE_TOKEN],
        email=data.get(CONF_EMAIL, ""),
        member_name=data.get(CONF_MEMBER_NAME, ""),
        token_callback=_store_tokens,
    )
    coordinator = SmartSolityCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_services(hass, coordinator)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartSolityConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        async_unload_services(hass)
    return unloaded
