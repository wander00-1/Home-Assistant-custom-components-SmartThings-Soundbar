"""Media player entity tests."""

from __future__ import annotations

import pytest

from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MP_DOMAIN,
    SERVICE_SELECT_SOURCE,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    STATE_PLAYING,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.smartthings_soundbar.const import DOMAIN

from .conftest import API, DEVICE_ID, OAUTH_TOKEN, TOKEN

ENTITY_ID = "media_player.lounge_soundbar"
COMMANDS_URL = f"{API}/devices/{DEVICE_ID}/commands"


def _commands(aioclient_mock) -> list[dict]:
    """Return the non-refresh command bodies sent so far."""
    sent = []
    for method, url, data, _headers in aioclient_mock.mock_calls:
        if method == "POST" and str(url) == COMMANDS_URL:
            cmd = data["commands"][0]
            if cmd["capability"] != "refresh":
                sent.append(cmd)
    return sent


async def _setup(hass, config_entry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_state(hass: HomeAssistant, mock_api, config_entry) -> None:
    """State maps from the SmartThings payload, with max_volume scaling."""
    await _setup(hass, config_entry)
    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_PLAYING
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.5  # 15 / 30
    assert state.attributes[ATTR_MEDIA_VOLUME_MUTED] is False
    assert state.attributes[ATTR_INPUT_SOURCE] == "wifi"
    assert state.attributes[ATTR_INPUT_SOURCE_LIST] == ["wifi", "bluetooth", "HDMI1"]
    assert state.attributes[ATTR_MEDIA_TITLE] == "Some Song"

    entry = er.async_get(hass).async_get(ENTITY_ID)
    assert entry.unique_id == f"SmartThings_Soundbar_{DEVICE_ID}"


async def test_unavailable_without_switch(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    """Missing switch value means the device is unreachable."""
    aioclient_mock.get(f"{API}/devices/{DEVICE_ID}", json={"label": "x"})
    aioclient_mock.get(f"{API}/devices/{DEVICE_ID}/states", json={"main": {}})
    aioclient_mock.post(COMMANDS_URL, json={})
    await _setup(hass, config_entry)
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


async def test_commands(hass: HomeAssistant, mock_api, config_entry) -> None:
    """Services send well-formed JSON commands."""
    await _setup(hass, config_entry)

    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: 0.5},
        blocking=True,
    )
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_MUTED: True},
        blocking=True,
    )
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: "HDMI1"},
        blocking=True,
    )

    assert _commands(mock_api) == [
        {"component": "main", "capability": "audioVolume", "command": "setVolume", "arguments": [15]},
        {"component": "main", "capability": "audioMute", "command": "mute"},
        {"component": "main", "capability": "mediaInputSource", "command": "setInputSource", "arguments": ["HDMI1"]},
    ]


async def test_command_failure_raises(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """A failed command surfaces as an error to the caller."""
    await _setup(hass, config_entry)
    mock_api.clear_requests()
    mock_api.post(COMMANDS_URL, status=500)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_VOLUME_MUTE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_MUTED: True},
            blocking=True,
        )


async def test_auth_failure_starts_reauth(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    """A 401 at setup puts the entry into reauth."""
    aioclient_mock.get(f"{API}/devices/{DEVICE_ID}", status=401)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_yaml_import(hass: HomeAssistant, mock_api) -> None:
    """A YAML platform config becomes a config entry."""
    assert await async_setup_component(
        hass,
        MP_DOMAIN,
        {
            MP_DOMAIN: {
                "platform": DOMAIN,
                "name": "Soundbar",
                "api_key": TOKEN,
                "device_id": DEVICE_ID,
                "max_volume": 30,
            }
        },
    )
    await hass.async_block_till_done()
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].title == "Soundbar"
    assert hass.states.get("media_player.soundbar").state == STATE_PLAYING


async def test_borrowed_login(hass: HomeAssistant, mock_api, smartthings_entry) -> None:
    """An entry using the official login sends its token, and goes unavailable
    (not into reauth) while that integration is unloaded."""
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.const import CONF_DEVICE_ID

    from custom_components.smartthings_soundbar.const import CONF_SMARTTHINGS_ENTRY_ID

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Lounge Soundbar",
        unique_id=DEVICE_ID,
        data={CONF_DEVICE_ID: DEVICE_ID, CONF_SMARTTHINGS_ENTRY_ID: smartthings_entry.entry_id},
        options={"max_volume": 30},
    )
    await _setup(hass, entry)
    assert hass.states.get(ENTITY_ID).state == STATE_PLAYING
    assert {h["Authorization"] for *_x, h in mock_api.mock_calls} == {f"Bearer {OAUTH_TOKEN}"}

    smartthings_entry.mock_state(hass, ConfigEntryState.NOT_LOADED)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE
    assert not hass.config_entries.flow.async_progress()
