"""Polling coordinator for the SmartThings Soundbar integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartThingsAuthError, SmartThingsError, SmartThingsSoundbarApi, SoundbarState
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type SoundbarConfigEntry = ConfigEntry[SoundbarCoordinator]


class SoundbarCoordinator(DataUpdateCoordinator[SoundbarState]):
    """Poll one soundbar through the SmartThings cloud."""

    config_entry: SoundbarConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SoundbarConfigEntry,
        api: SmartThingsSoundbarApi,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self.device: dict[str, Any] = {}

    async def _async_setup(self) -> None:
        """Fetch static device details once, before the first poll."""
        try:
            self.device = await self.api.async_get_device()
        except SmartThingsAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SmartThingsError as err:
            raise UpdateFailed(f"Could not load device details: {err}") from err

    async def _async_update_data(self) -> SoundbarState:
        """Fetch the latest state."""
        try:
            return await self.api.async_get_state()
        except SmartThingsAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SmartThingsError as err:
            raise UpdateFailed(str(err)) from err
