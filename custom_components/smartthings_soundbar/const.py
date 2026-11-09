"""Constants for the SmartThings Soundbar integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "smartthings_soundbar"

CONF_MAX_VOLUME: Final = "max_volume"
CONF_SMARTTHINGS_ENTRY_ID: Final = "smartthings_entry_id"

SMARTTHINGS_DOMAIN: Final = "smartthings"
DEFAULT_MAX_VOLUME: Final = 100
DEFAULT_NAME: Final = "SmartThings Soundbar"

SCAN_INTERVAL: Final = timedelta(seconds=10)

# Sources on which the soundbar reports a meaningful playback status.
CONTROLLABLE_SOURCES: Final = frozenset({"bluetooth", "wifi"})
