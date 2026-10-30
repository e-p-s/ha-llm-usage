"""Data update coordinator for the OpenRouter Usage integration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CREDITS_URL, DEFAULT_SCAN_INTERVAL, DOMAIN, KEY_URL

_LOGGER = logging.getLogger(__name__)

HISTORY_RETENTION = timedelta(hours=48)


class OpenRouterUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll OpenRouter credits/key endpoints and keep a rolling usage history."""

    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._api_key = api_key
        self._store = Store(hass, 1, f"{DOMAIN}.samples", private=True)
        # samples: [epoch_seconds, total_usage_usd]
        self.samples: list[list[float]] = []

    async def async_load_history(self) -> None:
        try:
            raw = await self._store.async_load()
        except Exception:  # version mismatch / broken file -> start fresh
            _LOGGER.debug("Discarding incompatible OpenRouter sample history", exc_info=True)
            return
        if not isinstance(raw, list):
            return
        cutoff = datetime.now(timezone.utc).timestamp() - HISTORY_RETENTION.total_seconds()
        self.samples = [
            s
            for s in raw
            if isinstance(s, list)
            and len(s) == 2
            and isinstance(s[0], (int, float))
            and s[0] >= cutoff
        ]

    async def async_store_history(self) -> None:
        cutoff = datetime.now(timezone.utc).timestamp() - HISTORY_RETENTION.total_seconds()
        self.samples = [s for s in self.samples if s[0] >= cutoff]
        await self._store.async_save(self.samples)

    def usage_delta(self, window: timedelta) -> float | None:
        """USD consumed within a rolling window (positive increments only)."""
        if not self.samples:
            return None
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - window.total_seconds()
        series = [s for s in self.samples if s[0] >= cutoff]
        previous = [s for s in self.samples if s[0] < cutoff]
        if previous:
            series = [previous[-1]] + series
        if len(series) < 2:
            return 0.0
        delta = 0.0
        for prev, cur in zip(series, series[1:]):
            inc = float(cur[1]) - float(prev[1])
            if inc > 0:
                delta += inc
        return round(delta, 4)

    async def _get_json(self, session, url: str) -> Any:
        async with session.get(
            url, headers={"Authorization": f"Bearer {self._api_key}"}, timeout=30
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        try:
            credits_payload = await self._get_json(session, CREDITS_URL)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"OpenRouter credits request failed: {err}") from err

        credits_data = (
            credits_payload.get("data")
            if isinstance(credits_payload, dict)
            else None
        )
        if not isinstance(credits_data, dict):
            raise UpdateFailed("OpenRouter credits returned unexpected payload")

        key_data: dict[str, Any] | None = None
        try:
            key_payload = await self._get_json(session, KEY_URL)
            if isinstance(key_payload, dict) and isinstance(
                key_payload.get("data"), dict
            ):
                key_data = key_payload["data"]
        except (aiohttp.ClientError, TimeoutError, ValueError):
            _LOGGER.debug("OpenRouter key endpoint unavailable", exc_info=True)

        total_usage = credits_data.get("total_usage")
        if isinstance(total_usage, (int, float)):
            self.samples.append(
                [datetime.now(timezone.utc).timestamp(), float(total_usage)]
            )
            await self.async_store_history()

        return {"credits": credits_data, "key": key_data}
