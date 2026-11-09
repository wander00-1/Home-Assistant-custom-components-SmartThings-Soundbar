"""Base entity for the SmartThings Soundbar integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SoundbarCoordinator


class SoundbarEntity(CoordinatorEntity[SoundbarCoordinator]):
    """Shared device info and availability for soundbar entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SoundbarCoordinator) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        device_id = coordinator.api.device_id
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
    def available(self) -> bool:
        """SmartThings omits the switch value when the device is unreachable."""
        return super().available and self.coordinator.data.switch is not None
