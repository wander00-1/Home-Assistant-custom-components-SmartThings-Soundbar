"""Media player entity for SmartThings soundbars."""

from __future__ import annotations

from collections.abc import Awaitable

import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA as MEDIA_PLAYER_PLATFORM_SCHEMA,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_API_KEY, CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SmartThingsAuthError, SmartThingsError
from .const import (
    CONF_MAX_VOLUME,
    CONTROLLABLE_SOURCES,
    DEFAULT_MAX_VOLUME,
    DEFAULT_NAME,
    DOMAIN,
)
from .coordinator import SoundbarConfigEntry, SoundbarCoordinator

PARALLEL_UPDATES = 1

SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
)

# Legacy YAML schema, kept only so existing configs can be imported.
PLATFORM_SCHEMA = MEDIA_PLAYER_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_MAX_VOLUME, default=DEFAULT_MAX_VOLUME): cv.positive_int,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Import a YAML-configured soundbar into a config entry."""
    if CONF_DEVICE_ID not in config:
        async_create_issue(
            hass,
            DOMAIN,
            "yaml_missing_device_id",
            is_fixable=False,
            severity=IssueSeverity.ERROR,
            translation_key="yaml_missing_device_id",
        )
        return

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={
            CONF_API_KEY: config[CONF_API_KEY],
            CONF_DEVICE_ID: config[CONF_DEVICE_ID],
            CONF_NAME: config[CONF_NAME],
            CONF_MAX_VOLUME: config[CONF_MAX_VOLUME],
        },
    )
    if (
        result["type"] is FlowResultType.CREATE_ENTRY
        or result.get("reason") == "already_configured"
    ):
        async_create_issue(
            hass,
            HOMEASSISTANT_DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": "SmartThings Soundbar",
            },
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoundbarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the soundbar media player from a config entry."""
    async_add_entities([SmartThingsSoundbarMediaPlayer(entry.runtime_data)])


class SmartThingsSoundbarMediaPlayer(
    CoordinatorEntity[SoundbarCoordinator], MediaPlayerEntity
):
    """A SmartThings-connected soundbar."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = SUPPORTED_FEATURES

    def __init__(self, coordinator: SoundbarCoordinator) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        device_id = coordinator.api.device_id
        # Matches the unique_id used by the YAML platform, so imported
        # entities keep their entity_id and history.
        self._attr_unique_id = f"SmartThings_Soundbar_{device_id}"

        device = coordinator.device
        ocf = device.get("ocf") or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=coordinator.config_entry.title,
            manufacturer=ocf.get("manufacturerName")
            or device.get("manufacturerName"),
            model=ocf.get("modelNumber") or device.get("deviceTypeName"),
            sw_version=ocf.get("firmwareVersion"),
        )

    @property
    def _max_volume(self) -> int:
        return int(
            self.coordinator.config_entry.options.get(
                CONF_MAX_VOLUME, DEFAULT_MAX_VOLUME
            )
        )

    @property
    def available(self) -> bool:
        """SmartThings omits the switch value when the device is unreachable."""
        return super().available and self.coordinator.data.switch is not None

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the current state."""
        data = self.coordinator.data
        if data.switch != "on":
            return MediaPlayerState.OFF
        if (data.source or "").lower() in CONTROLLABLE_SOURCES:
            if data.playback_status == "playing":
                return MediaPlayerState.PLAYING
            if data.playback_status == "paused":
                return MediaPlayerState.PAUSED
        return MediaPlayerState.ON

    @property
    def volume_level(self) -> float | None:
        """Return volume scaled so max_volume maps to 1.0."""
        volume = self.coordinator.data.volume
        if volume is None:
            return None
        return min(volume / self._max_volume, 1.0)

    @property
    def is_volume_muted(self) -> bool:
        """Return True if muted."""
        return self.coordinator.data.muted

    @property
    def source(self) -> str | None:
        """Return the current input source."""
        return self.coordinator.data.source

    @property
    def source_list(self) -> list[str]:
        """Return the available input sources."""
        return self.coordinator.data.source_list

    @property
    def media_title(self) -> str | None:
        """Return the track description while something is playing."""
        if self.state in (MediaPlayerState.PLAYING, MediaPlayerState.PAUSED):
            return self.coordinator.data.track_description
        return None

    async def _send(self, request: Awaitable[None]) -> None:
        """Run a command, surface failures to the caller, then refresh."""
        try:
            await request
        except SmartThingsAuthError as err:
            self.coordinator.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(f"SmartThings rejected the token: {err}") from err
        except SmartThingsError as err:
            raise HomeAssistantError(f"SmartThings command failed: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the soundbar on."""
        await self._send(self.coordinator.api.async_command("switch", "on"))

    async def async_turn_off(self) -> None:
        """Turn the soundbar off."""
        await self._send(self.coordinator.api.async_command("switch", "off"))

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume, where 1.0 maps to max_volume."""
        level = round(volume * self._max_volume)
        await self._send(
            self.coordinator.api.async_command("audioVolume", "setVolume", [level])
        )

    async def async_volume_up(self) -> None:
        """Step volume up."""
        await self._send(self.coordinator.api.async_command("audioVolume", "volumeUp"))

    async def async_volume_down(self) -> None:
        """Step volume down."""
        await self._send(
            self.coordinator.api.async_command("audioVolume", "volumeDown")
        )

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute."""
        await self._send(
            self.coordinator.api.async_command(
                "audioMute", "mute" if mute else "unmute"
            )
        )

    async def async_select_source(self, source: str) -> None:
        """Select an input source."""
        await self._send(
            self.coordinator.api.async_command(
                "mediaInputSource", "setInputSource", [source]
            )
        )

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select a sound mode through Samsung's OCF execute endpoint."""
        await self._send(
            self.coordinator.api.async_command(
                "execute",
                "execute",
                [
                    "/sec/networkaudio/soundmode",
                    {"x.com.samsung.networkaudio.soundmode": sound_mode},
                ],
            )
        )

    async def async_media_play(self) -> None:
        """Resume playback."""
        await self._send(self.coordinator.api.async_command("mediaPlayback", "play"))

    async def async_media_pause(self) -> None:
        """Pause playback."""
        await self._send(self.coordinator.api.async_command("mediaPlayback", "pause"))
