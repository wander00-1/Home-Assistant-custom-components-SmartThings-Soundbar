"""Where the SmartThings access token comes from.

Either a pasted personal access token, or the OAuth login held by Home
Assistant's official SmartThings integration. In the second case we ask that
integration's own refresh function for a token, so it remains the only thing
that ever refreshes the login and the two integrations cannot race on a
rotating refresh token.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .api import SmartThingsAuthError, SmartThingsConnectionError, TokenProvider
from .const import CONF_SMARTTHINGS_ENTRY_ID, SMARTTHINGS_DOMAIN


def _refresh_function(entry: ConfigEntry) -> Callable[[], Awaitable[str]] | None:
    """Return the official integration's token refresher, if reachable.

    Relies on SmartThingsData.client.refresh_token_function (HA 2025.3+).
    """
    if entry.state is not ConfigEntryState.LOADED:
        return None
    client = getattr(getattr(entry, "runtime_data", None), "client", None)
    refresh = getattr(client, "refresh_token_function", None)
    return refresh if callable(refresh) else None


def usable_smartthings_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    """Loaded official SmartThings entries whose login we can borrow."""
    return [
        entry
        for entry in hass.config_entries.async_entries(SMARTTHINGS_DOMAIN)
        if _refresh_function(entry) is not None
    ]


def static_token(token: str) -> TokenProvider:
    """Provide a fixed personal access token."""

    async def _provide() -> str:
        return token

    return _provide


def smartthings_token(hass: HomeAssistant, entry_id: str) -> TokenProvider:
    """Provide the current token from an official SmartThings entry."""

    async def _provide() -> str:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            raise SmartThingsAuthError(
                "The SmartThings integration entry this soundbar used was removed"
            )
        refresh = _refresh_function(entry)
        if refresh is None:
            raise SmartThingsConnectionError(
                "The SmartThings integration is not loaded yet"
            )
        try:
            return await refresh()
        except Exception as err:  # noqa: BLE001 - the official integration owns reauth
            raise SmartThingsConnectionError(
                f"The SmartThings integration could not provide a token: {err}"
            ) from err

    return _provide


def token_provider_for(hass: HomeAssistant, data: dict[str, Any]) -> TokenProvider:
    """Build the token provider described by config entry data."""
    if CONF_SMARTTHINGS_ENTRY_ID in data:
        return smartthings_token(hass, data[CONF_SMARTTHINGS_ENTRY_ID])
    return static_token(data[CONF_API_KEY])
