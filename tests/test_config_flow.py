"""Config flow tests."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.smartthings_soundbar.const import (
    CONF_MAX_VOLUME,
    CONF_SMARTTHINGS_ENTRY_ID,
    DOMAIN,
)

from .conftest import API, DEVICE_ID, OAUTH_TOKEN, TOKEN


async def test_user_flow(hass: HomeAssistant, mock_api) -> None:
    """Token, then device picker, creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    # No official SmartThings entry, so it goes straight to the token form.
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "token"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: f" {TOKEN} "}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device"
    options = result["data_schema"].schema[CONF_DEVICE_ID].config["options"]
    # Non-audio devices are filtered out.
    assert [o["value"] for o in options] == [DEVICE_ID]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: DEVICE_ID}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lounge Soundbar"
    assert result["data"] == {CONF_API_KEY: TOKEN, CONF_DEVICE_ID: DEVICE_ID}
    assert result["options"] == {CONF_MAX_VOLUME: 100}


async def test_user_flow_invalid_auth(hass: HomeAssistant, aioclient_mock) -> None:
    """A rejected token shows an error and lets the user retry."""
    aioclient_mock.get(f"{API}/devices", status=401)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "bad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """Adding the same device twice aborts."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TOKEN}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: DEVICE_ID}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_flow(hass: HomeAssistant, mock_api) -> None:
    """YAML import keeps the name and max volume."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_API_KEY: TOKEN,
            CONF_DEVICE_ID: DEVICE_ID,
            CONF_NAME: "Soundbar",
            CONF_MAX_VOLUME: 30,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Soundbar"
    assert result["options"] == {CONF_MAX_VOLUME: 30}


async def test_reauth_flow(hass: HomeAssistant, mock_api, config_entry) -> None:
    """Reauth replaces the token."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "token"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "token-2"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    await hass.async_block_till_done()
    assert config_entry.data[CONF_API_KEY] == "token-2"


async def test_options_flow(hass: HomeAssistant, mock_api, config_entry) -> None:
    """Options flow updates max volume."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_MAX_VOLUME: 50}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_MAX_VOLUME: 50}


def _auth_headers(aioclient_mock) -> set[str]:
    return {h["Authorization"] for _m, _u, _d, h in aioclient_mock.mock_calls}


async def test_user_flow_smartthings_login(
    hass: HomeAssistant, mock_api, smartthings_entry
) -> None:
    """With the official integration loaded, its login can be borrowed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["smartthings", "token"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "smartthings"}
    )
    # A single SmartThings entry is used without asking.
    assert result["step_id"] == "device"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: DEVICE_ID}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SMARTTHINGS_ENTRY_ID: smartthings_entry.entry_id,
        CONF_DEVICE_ID: DEVICE_ID,
    }
    assert _auth_headers(mock_api) == {f"Bearer {OAUTH_TOKEN}"}


async def test_reconfigure_to_smartthings_login(
    hass: HomeAssistant, mock_api, config_entry, smartthings_entry
) -> None:
    """Reconfigure switches a token entry to the borrowed login."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "smartthings"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert config_entry.data == {
        CONF_DEVICE_ID: DEVICE_ID,
        CONF_SMARTTHINGS_ENTRY_ID: smartthings_entry.entry_id,
    }


async def test_smartthings_login_rejected(
    hass: HomeAssistant, aioclient_mock, smartthings_entry
) -> None:
    """A rejected borrowed login shows an error on the SmartThings step."""
    aioclient_mock.get(f"{API}/devices", status=401)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "smartthings"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "smartthings"
    assert result["errors"] == {"base": "invalid_auth"}
