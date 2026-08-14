"""Config flow for Smart Solity."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartSolityAuthError, SmartSolityClient, SmartSolityError
from .const import (
    CONF_MEMBER_ID,
    CONF_MEMBER_NAME,
    CONF_PHONE_TOKEN,
    CONF_TOKEN,
    CONF_TOKEN_PASSWORD,
    DOMAIN,
)


def _schema(email: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=email): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
            ),
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


class SmartSolityConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a Smart Solity account."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            phone_token = secrets.token_hex(8)
            client = SmartSolityClient(
                async_get_clientsession(self.hass), phone_token=phone_token
            )
            try:
                await client.async_login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
                devices = await client.async_get_devices()
            except SmartSolityAuthError:
                errors["base"] = "invalid_auth"
            except SmartSolityError:
                errors["base"] = "cannot_connect"
            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    unique_id = client.member_id or user_input[CONF_EMAIL].casefold()
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=client.member_name or "Smart Solity",
                        data={
                            CONF_EMAIL: client.email,
                            CONF_PHONE_TOKEN: phone_token,
                            CONF_MEMBER_ID: client.member_id,
                            CONF_MEMBER_NAME: client.member_name,
                            CONF_TOKEN: client.token,
                            CONF_TOKEN_PASSWORD: client.token_password,
                        },
                    )
        return self.async_show_form(step_id="user", data_schema=_schema(), errors=errors)

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        entry = self._reauth_entry
        errors: dict[str, str] = {}
        email = str(entry.data.get(CONF_EMAIL, ""))
        if user_input is not None:
            client = SmartSolityClient(
                async_get_clientsession(self.hass),
                phone_token=str(entry.data[CONF_PHONE_TOKEN]),
            )
            try:
                await client.async_login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            except SmartSolityAuthError:
                errors["base"] = "invalid_auth"
            except SmartSolityError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_EMAIL: client.email,
                        CONF_MEMBER_ID: client.member_id,
                        CONF_MEMBER_NAME: client.member_name,
                        CONF_TOKEN: client.token,
                        CONF_TOKEN_PASSWORD: client.token_password,
                    },
                )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=_schema(email), errors=errors
        )
