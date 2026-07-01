"""Sensor entities for HA Idleon."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import IdleonRuntimeData
from .const import DOMAIN, NAME
from .coordinator import IdleonDataUpdateCoordinator
from .models import IdleonCharacter


@dataclass(frozen=True, kw_only=True)
class IdleonAccountSensorEntityDescription(SensorEntityDescription):
    """Description for an account sensor."""

    value_fn: Callable[[IdleonDataUpdateCoordinator], Any]


@dataclass(frozen=True, kw_only=True)
class IdleonCharacterSensorEntityDescription(SensorEntityDescription):
    """Description for a character sensor."""

    value_fn: Callable[[IdleonCharacter], Any]
    include_details: bool = False


ACCOUNT_SENSOR_DESCRIPTIONS = (
    IdleonAccountSensorEntityDescription(
        key="account_total_level",
        translation_key="account_total_level",
        value_fn=lambda coordinator: coordinator.data.total_level,
    ),
    IdleonAccountSensorEntityDescription(
        key="account_character_count",
        translation_key="account_character_count",
        value_fn=lambda coordinator: coordinator.data.character_count,
    ),
    IdleonAccountSensorEntityDescription(
        key="account_gems",
        translation_key="account_gems",
        value_fn=lambda coordinator: coordinator.data.gems,
    ),
    IdleonAccountSensorEntityDescription(
        key="account_last_updated",
        translation_key="account_last_updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: coordinator.last_successful_update,
    ),
)

CHARACTER_SENSOR_DESCRIPTIONS = (
    IdleonCharacterSensorEntityDescription(
        key="character_level",
        translation_key="character_level",
        value_fn=lambda character: character.level,
        include_details=True,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_class",
        translation_key="character_class",
        value_fn=lambda character: character.character_class,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_current_map",
        translation_key="character_current_map",
        value_fn=lambda character: character.current_map,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_current_activity",
        translation_key="character_current_activity",
        value_fn=lambda character: character.current_activity,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_afk_hours",
        translation_key="character_afk_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda character: character.afk_hours,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[IdleonRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Idleon sensors for a config entry."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [
        IdleonAccountSensor(entry, coordinator, description)
        for description in ACCOUNT_SENSOR_DESCRIPTIONS
    ]

    entities.extend(
        IdleonCharacterSensor(entry, coordinator, character, description)
        for character in coordinator.data.characters
        for description in CHARACTER_SENSOR_DESCRIPTIONS
    )
    async_add_entities(entities)


class IdleonAccountSensor(CoordinatorEntity[IdleonDataUpdateCoordinator], SensorEntity):
    """Account-level Idleon sensor."""

    entity_description: IdleonAccountSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry[IdleonRuntimeData],
        coordinator: IdleonDataUpdateCoordinator,
        description: IdleonAccountSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _account_device_info(entry)

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator)


class IdleonCharacterSensor(
    CoordinatorEntity[IdleonDataUpdateCoordinator],
    SensorEntity,
):
    """Character-level Idleon sensor."""

    entity_description: IdleonCharacterSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry[IdleonRuntimeData],
        coordinator: IdleonDataUpdateCoordinator,
        character: IdleonCharacter,
        description: IdleonCharacterSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._character_id = character.character_id
        self._attr_unique_id = (
            f"{entry.entry_id}_{_slugify(character.character_id)}_{description.key}"
        )
        self._attr_device_info = _character_device_info(entry, character)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self._character is not None

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        character = self._character
        if character is None:
            return None
        value = self.entity_description.value_fn(character)
        if isinstance(value, datetime):
            return value
        return value

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return compact detailed character attributes on the primary sensor."""
        if not self.entity_description.include_details:
            return None
        character = self._character
        if character is None or not character.details:
            return None
        return dict(character.details)

    @property
    def _character(self) -> IdleonCharacter | None:
        """Return the current character model."""
        return next(
            (
                character
                for character in self.coordinator.data.characters
                if character.character_id == self._character_id
            ),
            None,
        )


def _account_device_info(entry: ConfigEntry[IdleonRuntimeData]) -> DeviceInfo:
    """Return account device information."""
    return DeviceInfo(
        identifiers={(DOMAIN, _account_device_identifier(entry))},
        name="Legends of Idleon Account",
        manufacturer="Legends of Idleon",
        model=NAME,
    )


def _character_device_info(
    entry: ConfigEntry[IdleonRuntimeData],
    character: IdleonCharacter,
) -> DeviceInfo:
    """Return character device information."""
    return DeviceInfo(
        identifiers={(DOMAIN, _character_device_identifier(entry, character))},
        name=f"Idleon Character - {character.name}",
        manufacturer="Legends of Idleon",
        model=character.character_class,
        via_device=(DOMAIN, _account_device_identifier(entry)),
    )


def _account_device_identifier(entry: ConfigEntry[IdleonRuntimeData]) -> str:
    """Return the account device identifier."""
    return f"{entry.entry_id}_account"


def _character_device_identifier(
    entry: ConfigEntry[IdleonRuntimeData],
    character: IdleonCharacter,
) -> str:
    """Return a character device identifier."""
    return f"{entry.entry_id}_{_slugify(character.character_id)}"


def _slugify(value: str) -> str:
    """Create a stable entity-safe identifier."""
    slug = "".join(
        character.lower() if character.isalnum() else "_" for character in value
    )
    return "_".join(part for part in slug.split("_") if part)
