"""Shared fixtures for SmartThings Soundbar tests."""

from __future__ import annotations

import json

import pytest

from homeassistant.const import CONF_API_KEY, CONF_DEVICE_ID

from custom_components.smartthings_soundbar.const import CONF_MAX_VOLUME, DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

API = "https://api.smartthings.com/v1"
DEVICE_ID = "abc-123"
TOKEN = "token-1"

DEVICES = {
    "items": [
        {
            "deviceId": DEVICE_ID,
            "label": "Lounge Soundbar",
            "components": [
                {"id": "main", "capabilities": [{"id": "audioVolume"}, {"id": "switch"}]}
            ],
        },
        {
            "deviceId": "fridge-1",
            "label": "Fridge",
            "components": [{"id": "main", "capabilities": [{"id": "switch"}]}],
        },
    ],
    "_links": {},
}

DEVICE = {
    "deviceId": DEVICE_ID,
    "label": "Lounge Soundbar",
    "ocf": {
        "manufacturerName": "Samsung Electronics",
        "modelNumber": "HW-Q990B",
        "firmwareVersion": "SAT-1.0",
    },
}

STATES = {
    "main": {
        "switch": {"value": "on"},
        "playbackStatus": {"value": "playing"},
        "inputSource": {"value": "wifi"},
        "supportedInputSources": {"value": json.dumps(["wifi", "bluetooth", "HDMI1"])},
        "mute": {"value": "unmuted"},
        "volume": {"value": 15},
        "trackDescription": {"value": "Some Song"},
    }
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading the custom integration in every test."""
    return


@pytest.fixture
def mock_api(aioclient_mock):
    """Mock the SmartThings endpoints for a healthy soundbar."""
    aioclient_mock.get(f"{API}/devices", json=DEVICES)
    aioclient_mock.get(f"{API}/devices/{DEVICE_ID}", json=DEVICE)
    aioclient_mock.get(f"{API}/devices/{DEVICE_ID}/states", json=STATES)
    aioclient_mock.post(f"{API}/devices/{DEVICE_ID}/commands", json={"results": []})
    return aioclient_mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured soundbar entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Lounge Soundbar",
        unique_id=DEVICE_ID,
        data={CONF_API_KEY: TOKEN, CONF_DEVICE_ID: DEVICE_ID},
        options={CONF_MAX_VOLUME: 30},
    )


OAUTH_TOKEN = "oauth-token"


@pytest.fixture
def smartthings_entry(hass):
    """A loaded official SmartThings entry exposing a token refresher."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from homeassistant.config_entries import ConfigEntryState

    entry = MockConfigEntry(
        domain="smartthings", title="Home", state=ConfigEntryState.LOADED
    )
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(
        client=SimpleNamespace(
            refresh_token_function=AsyncMock(return_value=OAUTH_TOKEN)
        )
    )
    yield entry
    # Stop HA from trying to unload the real smartthings integration at teardown.
    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)
