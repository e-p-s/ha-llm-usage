"""OpenRouter Usage integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers.config_validation import empty_config_schema
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, DOMAIN
from .coordinator import OpenRouterUsageCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

type OpenRouterUsageConfigEntry = ConfigEntry[OpenRouterUsageCoordinator]


def _resolved_key(entry: ConfigEntry) -> str:
    """API key from options (UI-editable) with fallback to initial data."""
    return entry.options.get(CONF_API_KEY) or entry.data[CONF_API_KEY]


CONFIG_SCHEMA = empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration (config entries only)."""
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options (API key) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(
    hass: HomeAssistant, entry: OpenRouterUsageConfigEntry
) -> bool:
    """Set up OpenRouter Usage from a config entry."""
    coordinator = OpenRouterUsageCoordinator(hass, _resolved_key(entry))
    await coordinator.async_load_history()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: OpenRouterUsageConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: OpenRouterUsageConfigEntry, device_entry
) -> bool:
    """Allow removal of orphaned devices."""
    return True
