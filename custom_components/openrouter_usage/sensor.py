"""Sensor platform for the OpenRouter Usage integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenRouterUsageCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create OpenRouter credit sensors."""
    coordinator: OpenRouterUsageCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        OpenRouterCreditSensor(coordinator, entry, "guthaben"),
        OpenRouterCreditSensor(coordinator, entry, "verbrauch_gesamt"),
        OpenRouterCreditSensor(coordinator, entry, "verbrauch_1h"),
        OpenRouterCreditSensor(coordinator, entry, "verbrauch_2h"),
        OpenRouterCreditSensor(coordinator, entry, "verbrauch_24h"),
    ]
    if coordinator.data.get("key"):
        entities.append(OpenRouterCreditSensor(coordinator, entry, "key_verbrauch_monat"))
    async_add_entities(entities)


class OpenRouterCreditSensor(CoordinatorEntity[OpenRouterUsageCoordinator], SensorEntity):
    """A single OpenRouter credit metric."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"

    def __init__(
        self,
        coordinator: OpenRouterUsageCoordinator,
        entry: ConfigEntry,
        kind: str,
    ) -> None:
        super().__init__(coordinator)
        self._kind = kind
        self._attr_unique_id = f"{entry.entry_id}-{kind}"
        self._attr_suggested_object_id = f"openrouter_{kind}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "translation_key": "account",
            "manufacturer": "OpenRouter",
            "configuration_url": "https://openrouter.ai/settings/credits",
        }
        if kind == "guthaben":
            self._attr_translation_key = "guthaben"
            self._attr_icon = "mdi:wallet"
        elif kind == "verbrauch_gesamt":
            self._attr_translation_key = "verbrauch_gesamt"
            self._attr_icon = "mdi:chart-line"
        elif kind == "key_verbrauch_monat":
            self._attr_translation_key = "key_verbrauch_monat"
            self._attr_icon = "mdi:key-alert"
        else:
            self._attr_translation_key = kind
            self._attr_icon = "mdi:chart-timeline-variant"
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        credits = data.get("credits") or {}
        key = data.get("key") or {}
        if self._kind == "guthaben":
            try:
                return round(float(credits["total_credits"]) - float(credits["total_usage"]), 4)
            except (KeyError, TypeError, ValueError):
                return None
        if self._kind == "verbrauch_gesamt":
            try:
                return round(float(credits["total_usage"]), 4)
            except (KeyError, TypeError, ValueError):
                return None
        if self._kind == "verbrauch_1h":
            return self.coordinator.usage_delta(timedelta(hours=1))
        if self._kind == "verbrauch_2h":
            return self.coordinator.usage_delta(timedelta(hours=2))
        if self._kind == "verbrauch_24h":
            return self.coordinator.usage_delta(timedelta(hours=24))
        try:
            return round(float(key["usage_monthly"]), 4)
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        key = data.get("key") or {}
        if self._kind != "guthaben":
            return {}
        return {
            "key_label": key.get("label"),
            "key_limit": key.get("limit"),
            "is_free_tier": key.get("is_free_tier"),
        }
