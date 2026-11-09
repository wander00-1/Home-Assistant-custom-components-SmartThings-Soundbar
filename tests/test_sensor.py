"""Sensor and diagnostics tests."""

from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.smartthings_soundbar.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import DEVICE_ID, TOKEN


async def _setup(hass, config_entry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_diagnostic_sensors(hass: HomeAssistant, mock_api, config_entry) -> None:
    """Each sensor reports its value and is a diagnostic entity."""
    await _setup(hass, config_entry)
    registry = er.async_get(hass)

    expected = {
        "sensor.lounge_soundbar_input_source": "wifi",
        "sensor.lounge_soundbar_playback_status": "playing",
        "sensor.lounge_soundbar_volume_level": "15",
        "sensor.lounge_soundbar_now_playing": "Some Song",
    }
    for entity_id, value in expected.items():
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert state.state == value
        assert registry.async_get(entity_id).entity_category is EntityCategory.DIAGNOSTIC

    attrs = hass.states.get("sensor.lounge_soundbar_input_source").attributes
    assert attrs["supported_sources"] == ["wifi", "bluetooth", "HDMI1"]
    assert (
        registry.async_get("sensor.lounge_soundbar_volume_level").unique_id
        == f"{DEVICE_ID}_volume"
    )


async def test_diagnostics(hass: HomeAssistant, mock_api, config_entry) -> None:
    """Diagnostics include the raw payload and never the token."""
    await _setup(hass, config_entry)
    diag = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diag["entry"]["data"]["api_key"] == "**REDACTED**"
    assert TOKEN not in str(diag)
    assert diag["auth_method"] == "personal_access_token"
    assert diag["last_update_success"] is True
    assert diag["state"]["source"] == "wifi"
    assert "raw" not in diag["state"]
    assert diag["raw_states"]["main"]["volume"]["value"] == 15
    assert diag["device"]["ocf"]["modelNumber"] == "HW-Q990B"
