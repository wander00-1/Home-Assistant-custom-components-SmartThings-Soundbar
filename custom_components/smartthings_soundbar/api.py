"""Minimal async client for the SmartThings REST API, scoped to soundbars."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://api.smartthings.com/v1"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

type TokenProvider = Callable[[], Awaitable[str]]


class SmartThingsError(Exception):
    """Base error for SmartThings API failures."""


class SmartThingsAuthError(SmartThingsError):
    """The token is invalid, expired or lacks the required scopes."""


class SmartThingsConnectionError(SmartThingsError):
    """The API could not be reached or returned an unexpected response."""


@dataclass(slots=True)
class SoundbarState:
    """Snapshot of the soundbar state reported by SmartThings."""

    switch: str | None = None
    playback_status: str | None = None
    source: str | None = None
    source_list: list[str] = field(default_factory=list)
    muted: bool = False
    volume: int | None = None
    track_description: str | None = None
    # Full /states payload, kept for the diagnostics download.
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


def _value(data: dict[str, Any], attribute: str) -> Any:
    """Return main.<attribute>.value from a /states payload, or None."""
    main = data.get("main")
    if not isinstance(main, dict):
        return None
    attr = main.get(attribute)
    if not isinstance(attr, dict):
        return None
    return attr.get("value")


def _parse_sources(raw: Any) -> list[str]:
    """Parse supportedInputSources, which arrives in several shapes."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    if isinstance(raw, dict):
        raw = raw.get("value")
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return []


def parse_state(data: dict[str, Any]) -> SoundbarState:
    """Build a SoundbarState from a /devices/{id}/states payload."""
    volume_raw = _value(data, "volume")
    try:
        volume = int(volume_raw) if volume_raw is not None else None
    except (TypeError, ValueError):
        volume = None

    return SoundbarState(
        switch=_value(data, "switch"),
        playback_status=_value(data, "playbackStatus"),
        source=_value(data, "inputSource"),
        source_list=_parse_sources(_value(data, "supportedInputSources")),
        muted=_value(data, "mute") == "muted",
        volume=volume,
        track_description=_value(data, "trackDescription"),
        raw=data,
    )


class SmartThingsSoundbarApi:
    """Talk to one soundbar through the SmartThings cloud API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token_provider: TokenProvider,
        device_id: str,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._token_provider = token_provider
        self.device_id = device_id

    @staticmethod
    async def async_list_devices(
        session: aiohttp.ClientSession, token_provider: TokenProvider
    ) -> list[dict[str, Any]]:
        """Return every device visible to the token, following pagination."""
        devices: list[dict[str, Any]] = []
        url: str | None = f"{API_BASE_URL}/devices"
        while url:
            page = await _request(session, await token_provider(), "GET", url)
            devices.extend(page.get("items", []))
            next_link = (page.get("_links") or {}).get("next")
            url = next_link.get("href") if isinstance(next_link, dict) else None
        return devices

    async def async_get_device(self) -> dict[str, Any]:
        """Return the device description (label, manufacturer, model)."""
        return await _request(
            self._session,
            await self._token_provider(),
            "GET",
            f"{API_BASE_URL}/devices/{self.device_id}",
        )

    async def async_get_state(self) -> SoundbarState:
        """Ask the device to refresh, then read its current state."""
        try:
            await self.async_command("refresh", "refresh")
        except SmartThingsAuthError:
            raise
        except SmartThingsError as err:
            # An offline device rejects the refresh; the read below still works.
            _LOGGER.debug("Refresh command failed: %s", err)

        data = await _request(
            self._session,
            await self._token_provider(),
            "GET",
            f"{API_BASE_URL}/devices/{self.device_id}/states",
        )
        return parse_state(data)

    async def async_command(
        self,
        capability: str,
        command: str,
        arguments: list[Any] | None = None,
    ) -> None:
        """Send a single command to the main component."""
        cmd: dict[str, Any] = {
            "component": "main",
            "capability": capability,
            "command": command,
        }
        if arguments is not None:
            cmd["arguments"] = arguments
        await _request(
            self._session,
            await self._token_provider(),
            "POST",
            f"{API_BASE_URL}/devices/{self.device_id}/commands",
            {"commands": [cmd]},
        )


async def _request(
    session: aiohttp.ClientSession,
    token: str,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform an API request and map failures onto our exceptions."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with session.request(
            method, url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
        ) as resp:
            if resp.status in (401, 403):
                raise SmartThingsAuthError(f"HTTP {resp.status} from SmartThings")
            if resp.status >= 400:
                body = await resp.text()
                raise SmartThingsConnectionError(
                    f"HTTP {resp.status} from SmartThings: {body[:200]}"
                )
            body = await resp.text()
    except (TimeoutError, aiohttp.ClientError) as err:
        raise SmartThingsConnectionError(str(err)) from err
    if not body:
        return {}
    try:
        data = json.loads(body)
    except ValueError as err:
        raise SmartThingsConnectionError("SmartThings returned invalid JSON") from err
    return data if isinstance(data, dict) else {}
