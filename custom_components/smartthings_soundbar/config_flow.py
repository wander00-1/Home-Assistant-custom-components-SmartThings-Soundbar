"""Config flow for the SmartThings Soundbar integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY, CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import SmartThingsAuthError, SmartThingsError, SmartThingsSoundbarApi
from .auth import token_provider_for, usable_smartthings_entries
from .const import (
    CONF_MAX_VOLUME,
    CONF_SMARTTHINGS_ENTRY_ID,
    DEFAULT_MAX_VOLUME,
    DEFAULT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

TOKEN_URL = "https://account.smartthings.com/tokens"

TOKEN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)

MAX_VOLUME_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=1, max=100, step=1, mode=NumberSelectorMode.BOX)
)

AUTH_MENU = ["smartthings", "token"]


def _is_audio_device(device: dict[str, Any]) -> bool:
    """Return True if the device's main component exposes volume control."""
    for component in device.get("components", []):
        if component.get("id") != "main":
            continue
        return any(
            cap.get("id") == "audioVolume" for cap in component.get("capabilities", [])
        )
    return False


def _device_label(device: dict[str, Any]) -> str:
    return device.get("label") or device.get("name") or device["deviceId"]


class SmartThingsSoundbarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartThings Soundbar."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._auth: dict[str, Any] = {}
        self._devices: dict[str, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return SmartThingsSoundbarOptionsFlow()

    # Entry points ---------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a soundbar."""
        return await self._async_choose_auth("user")

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauth when SmartThings rejected the credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose new credentials for an existing soundbar."""
        return await self._async_choose_auth("reauth_confirm")

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Switch an existing soundbar to a different login."""
        return await self._async_choose_auth("reconfigure")

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import a legacy YAML platform entry.

        The token is not validated here: a stale one triggers reauth on setup,
        which is a better experience than silently dropping the import.
        """
        device_id = import_data[CONF_DEVICE_ID]
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=import_data.get(CONF_NAME, DEFAULT_NAME),
            data={
                CONF_API_KEY: import_data[CONF_API_KEY],
                CONF_DEVICE_ID: device_id,
            },
            options={
                CONF_MAX_VOLUME: import_data.get(CONF_MAX_VOLUME, DEFAULT_MAX_VOLUME)
            },
        )

    # Choosing where the token comes from -----------------------------------

    async def _async_choose_auth(self, step_id: str) -> ConfigFlowResult:
        """Offer the SmartThings login when available, else ask for a token."""
        if usable_smartthings_entries(self.hass):
            return self.async_show_menu(step_id=step_id, menu_options=AUTH_MENU)
        return await self.async_step_token()

    async def async_step_smartthings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Use the login of the official SmartThings integration."""
        entries = usable_smartthings_entries(self.hass)
        if not entries:
            return self.async_abort(reason="smartthings_not_loaded")

        errors: dict[str, str] = {}
        if user_input is not None or len(entries) == 1:
            entry_id = (
                user_input[CONF_SMARTTHINGS_ENTRY_ID]
                if user_input is not None
                else entries[0].entry_id
            )
            result, errors = await self._async_try_auth(
                {CONF_SMARTTHINGS_ENTRY_ID: entry_id}
            )
            if result is not None:
                return result

        return self.async_show_form(
            step_id="smartthings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SMARTTHINGS_ENTRY_ID, default=entries[0].entry_id
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=e.entry_id, label=e.title)
                                for e in entries
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_token(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Use a pasted personal access token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            result, errors = await self._async_try_auth(
                {CONF_API_KEY: user_input[CONF_API_KEY].strip()}
            )
            if result is not None:
                return result

        return self.async_show_form(
            step_id="token",
            data_schema=TOKEN_SCHEMA,
            errors=errors,
            description_placeholders={"token_url": TOKEN_URL},
        )

    def _existing_entry(self) -> ConfigEntry | None:
        """The entry being reauthenticated or reconfigured, if any."""
        if self.source == SOURCE_REAUTH:
            return self._get_reauth_entry()
        if self.source == SOURCE_RECONFIGURE:
            return self._get_reconfigure_entry()
        return None

    async def _async_try_auth(
        self, auth: dict[str, Any]
    ) -> tuple[ConfigFlowResult | None, dict[str, str]]:
        """Validate credentials, then finish or move on to picking a device."""
        provider = token_provider_for(self.hass, auth)
        session = async_get_clientsession(self.hass)
        existing = self._existing_entry()
        try:
            if existing is not None:
                await SmartThingsSoundbarApi(
                    session, provider, existing.data[CONF_DEVICE_ID]
                ).async_get_device()
                devices: list[dict[str, Any]] = []
            else:
                devices = await SmartThingsSoundbarApi.async_list_devices(
                    session, provider
                )
        except SmartThingsAuthError:
            return None, {"base": "invalid_auth"}
        except SmartThingsError:
            return None, {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error talking to SmartThings")
            return None, {"base": "unknown"}

        if existing is not None:
            # Replace data wholesale so a switch of auth method drops the old key.
            return (
                self.async_update_reload_and_abort(
                    existing,
                    data={CONF_DEVICE_ID: existing.data[CONF_DEVICE_ID], **auth},
                ),
                {},
            )

        audio = [d for d in devices if _is_audio_device(d)] or devices
        self._devices = {d["deviceId"]: _device_label(d) for d in audio if "deviceId" in d}
        if not self._devices:
            return None, {"base": "no_devices"}
        self._auth = auth
        return await self.async_step_device(), {}

    # Picking the soundbar ---------------------------------------------------

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick which soundbar to add."""
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._devices.get(device_id, DEFAULT_NAME),
                data={**self._auth, CONF_DEVICE_ID: device_id},
                options={CONF_MAX_VOLUME: DEFAULT_MAX_VOLUME},
            )

        options = [
            SelectOptionDict(value=device_id, label=label)
            for device_id, label in sorted(self._devices.items(), key=lambda i: i[1])
        ]
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                            custom_value=True,
                        )
                    )
                }
            ),
        )


class SmartThingsSoundbarOptionsFlow(OptionsFlow):
    """Handle options for a configured soundbar."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the max volume mapping."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_MAX_VOLUME: int(user_input[CONF_MAX_VOLUME])}
            )

        current = self.config_entry.options.get(CONF_MAX_VOLUME, DEFAULT_MAX_VOLUME)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_MAX_VOLUME, default=current): MAX_VOLUME_SELECTOR}
            ),
        )
