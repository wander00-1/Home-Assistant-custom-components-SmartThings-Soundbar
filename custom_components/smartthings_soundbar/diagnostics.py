"""Diagnostics download for the SmartThings Soundbar integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .coordinator import SoundbarConfigEntry

# Credentials, plus account identifiers that are pointless in a shared report.
TO_REDACT = {CONF_API_KEY, "locationId", "ownerId", "roomId", "installedAppId"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SoundbarConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    state = coordinator.data
    parsed = asdict(state) if state is not None else None
    if parsed is not None:
        parsed.pop("raw", None)

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "auth_method": "smartthings_login"
        if "smartthings_entry_id" in entry.data
        else "personal_access_token",
        "last_update_success": coordinator.last_update_success,
        "device": async_redact_data(coordinator.device, TO_REDACT),
        "state": parsed,
        "raw_states": async_redact_data(state.raw, TO_REDACT) if state else None,
    }
