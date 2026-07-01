"""Binary sensor entities for HA Idleon."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import IdleonRuntimeData
from .coordinator import IdleonDataUpdateCoordinator
from .models import IdleonCharacter
from .sensor import _character_device_info, _select_detail_attributes, _slugify


@dataclass(frozen=True, kw_only=True)
class IdleonCharacterBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description for a character binary sensor."""

    value_fn: Callable[[IdleonCharacter], bool]
    detail_keys: tuple[str, ...] = ()


CHARACTER_BINARY_SENSOR_DESCRIPTIONS = (
    IdleonCharacterBinarySensorEntityDescription(
        key="character_inventory_full",
        translation_key="character_inventory_full",
        value_fn=lambda character: character.inventory_full,
        detail_keys=(
            "inventory_slots_total",
            "inventory_slots_usable",
            "inventory_slots_used",
            "inventory_slots_free",
            "inventory_sample",
            "inventory_bag_count",
            "inventory_bags",
            "max_carry_capacity",
        ),
    ),
    IdleonCharacterBinarySensorEntityDescription(
        key="character_needs_attention",
        translation_key="character_needs_attention",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda character: character.needs_attention,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[IdleonRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Idleon binary sensors for a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        IdleonCharacterBinarySensor(entry, coordinator, character, description)
        for character in coordinator.data.characters
        for description in CHARACTER_BINARY_SENSOR_DESCRIPTIONS
    )


class IdleonCharacterBinarySensor(
    CoordinatorEntity[IdleonDataUpdateCoordinator],
    BinarySensorEntity,
):
    """Character-level Idleon binary sensor."""

    entity_description: IdleonCharacterBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry[IdleonRuntimeData],
        coordinator: IdleonDataUpdateCoordinator,
        character: IdleonCharacter,
        description: IdleonCharacterBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        character = self._character
        if character is None:
            return None
        return self.entity_description.value_fn(character)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return details relevant to this character binary sensor."""
        if not self.entity_description.detail_keys:
            return None
        character = self._character
        if character is None or not character.details:
            return None
        attributes = _select_detail_attributes(
            character.details,
            self.entity_description.detail_keys,
        )
        return attributes or None

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
