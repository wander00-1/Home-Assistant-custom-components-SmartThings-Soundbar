"""Diagnostic sensors for SmartThings soundbars."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import SoundbarState
from .coordinator import SoundbarConfigEntry, SoundbarCoordinator
from .entity import SoundbarEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SoundbarSensorDescription(SensorEntityDescription):
    """Describe a soundbar sensor."""

    value_fn: Callable[[SoundbarState], StateType]
    attrs_fn: Callable[[SoundbarState], dict[str, Any]] | None = None


SENSORS: tuple[SoundbarSensorDescription, ...] = (
    SoundbarSensorDescription(
        key="input_source",
        translation_key="input_source",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.source,
        attrs_fn=lambda s: {"supported_sources": s.source_list},
    ),
    SoundbarSensorDescription(
        key="playback_status",
        translation_key="playback_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.playback_status,
    ),
    SoundbarSensorDescription(
        key="volume",
        translation_key="volume",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.volume,
    ),
    SoundbarSensorDescription(
        key="now_playing",
        translation_key="now_playing",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.track_description or None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoundbarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up soundbar sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(SoundbarSensor(coordinator, desc) for desc in SENSORS)


class SoundbarSensor(SoundbarEntity, SensorEntity):
    """A single value reported by the soundbar."""

    entity_description: SoundbarSensorDescription

    def __init__(
        self, coordinator: SoundbarCoordinator, description: SoundbarSensorDescription
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.api.device_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes, if any."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
