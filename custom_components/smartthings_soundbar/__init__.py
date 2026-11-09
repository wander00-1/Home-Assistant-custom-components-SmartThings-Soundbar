"""SmartThings Soundbar integration."""

from __future__ import annotations

from homeassistant.const import CONF_DEVICE_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartThingsSoundbarApi
from .auth import token_provider_for
from .coordinator import SoundbarConfigEntry, SoundbarCoordinator

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SoundbarConfigEntry) -> bool:
    """Set up a soundbar from a config entry."""
    api = SmartThingsSoundbarApi(
        async_get_clientsession(hass),
        token_provider_for(hass, dict(entry.data)),
        entry.data[CONF_DEVICE_ID],
    )
    coordinator = SoundbarCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SoundbarConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
