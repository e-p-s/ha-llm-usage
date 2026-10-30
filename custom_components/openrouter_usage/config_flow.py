"""Config flow for the OpenRouter Usage integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, CREDITS_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _key_schema(default: str = "") -> vol.Schema:
    return vol.Schema({vol.Required(CONF_API_KEY, default=default): str})


async def _validate_api_key(hass, api_key: str) -> bool:
    """Return True when the key is accepted by the OpenRouter credits endpoint."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            CREDITS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        ) as resp:
            resp.raise_for_status()
            payload = await resp.json()
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return False
    return isinstance(payload, dict) and isinstance(payload.get("data"), dict)


class OpenRouterUsageConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenRouter Usage."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OpenRouterUsageOptionsFlow:
        return OpenRouterUsageOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            if await _validate_api_key(self.hass, api_key):
                return self.async_create_entry(
                    title="OpenRouter Usage",
                    data={CONF_API_KEY: api_key},
                )
            errors["base"] = "invalid_key"
        return self.async_show_form(
            step_id="user", data_schema=_key_schema(), errors=errors
        )


class OpenRouterUsageOptionsFlow(OptionsFlow):
    """Allow editing the API key via the UI (gear icon)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }.get(CONF_API_KEY, "")
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            if await _validate_api_key(self.hass, api_key):
                return self.async_create_entry(
                    title="", data={CONF_API_KEY: api_key}
                )
            errors["base"] = "invalid_key"
        return self.async_show_form(
            step_id="init", data_schema=_key_schema(current), errors=errors
        )
