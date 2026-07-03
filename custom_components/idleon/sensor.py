"""Sensor entities for HA Idleon."""

from __future__ import annotations

import re
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
    detail_keys: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class IdleonCharacterSensorEntityDescription(SensorEntityDescription):
    """Description for a character sensor."""

    value_fn: Callable[[IdleonCharacter], Any]
    detail_keys: tuple[str, ...] = ()


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
        value_fn=lambda coordinator: (
            coordinator.data.source_updated_at or coordinator.last_successful_update
        ),
        entity_registry_enabled_default=False,
    ),
    IdleonAccountSensorEntityDescription(
        key="account_highest_character_level",
        translation_key="account_highest_character_level",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "highest_character_level",
            0,
        ),
        detail_keys=("highest_level_character", "class_counts"),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_total_skill_level",
        translation_key="account_total_skill_level",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "total_skill_level",
            0,
        ),
        detail_keys=("class_counts",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_total_money",
        translation_key="account_total_money",
        value_fn=lambda coordinator: _account_total_money(coordinator),
        detail_keys=("money_breakdown",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_raw_money",
        translation_key="account_raw_money",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "raw_money",
            0,
        ),
        detail_keys=("money_breakdown",),
        entity_registry_enabled_default=False,
    ),
    IdleonAccountSensorEntityDescription(
        key="account_green_stacks",
        translation_key="account_green_stacks",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "green_stack_count",
            0,
        ),
        detail_keys=("green_stack_sample",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_slab_items_obtained",
        translation_key="account_slab_items_obtained",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "slab_items_obtained",
            0,
        ),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_achievements_completed",
        translation_key="account_achievements_completed",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "achievements_completed",
            0,
        ),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_currencies",
        translation_key="account_currencies",
        value_fn=lambda coordinator: _account_detail_count(coordinator, "currencies"),
        detail_keys=("currencies",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_shrine_levels",
        translation_key="account_shrine_levels",
        value_fn=lambda coordinator: _account_detail_sum(
            coordinator,
            "shrine_levels",
        ),
        detail_keys=("shrine_levels",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_statue_levels",
        translation_key="account_statue_levels",
        value_fn=lambda coordinator: _account_detail_sum(
            coordinator,
            "statue_levels",
        ),
        detail_keys=("statue_levels",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_colosseum_scores",
        translation_key="account_colosseum_scores",
        value_fn=lambda coordinator: _account_detail_sum(
            coordinator,
            "colosseum_scores",
        ),
        detail_keys=("colosseum_scores",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_minigame_scores",
        translation_key="account_minigame_scores",
        value_fn=lambda coordinator: _account_detail_sum(
            coordinator,
            "minigame_scores",
        ),
        detail_keys=("minigame_scores",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_progress_totals",
        translation_key="account_progress_totals",
        value_fn=lambda coordinator: _account_detail_count(
            coordinator,
            "progress_totals",
        ),
        detail_keys=("progress_totals",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_pets",
        translation_key="account_pets",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "pets",
        ),
        detail_keys=("pets",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_achievements_by_world",
        translation_key="account_achievements_by_world",
        value_fn=lambda coordinator: _account_achievement_total(coordinator),
        detail_keys=("achievement_status",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_task_levels",
        translation_key="account_task_levels",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "task_levels",
        ),
        detail_keys=("task_levels",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_taskboard_merits",
        translation_key="account_taskboard_merits",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "taskboard_merits",
        ),
        detail_keys=("taskboard_merits",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_taskboard_unlocks",
        translation_key="account_taskboard_unlocks",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "taskboard_unlocks",
        ),
        detail_keys=("taskboard_unlocks",),
    ),
)

CHARACTER_SENSOR_DESCRIPTIONS = (
    IdleonCharacterSensorEntityDescription(
        key="character_level",
        translation_key="character_level",
        value_fn=lambda character: character.level,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_class",
        translation_key="character_class",
        value_fn=lambda character: character.character_class,
        detail_keys=("raw_class_id",),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_current_map",
        translation_key="character_current_map",
        value_fn=lambda character: character.current_map,
        detail_keys=("raw_map_id",),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_current_activity",
        translation_key="character_current_activity",
        value_fn=lambda character: character.current_activity,
        detail_keys=("afk_target",),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_afk_hours",
        translation_key="character_afk_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda character: character.afk_hours,
        detail_keys=("afk_seconds", "raw_afk_value"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_inventory_slots_used",
        translation_key="character_inventory_slots_used",
        value_fn=lambda character: _detail_value(
            character,
            "inventory_slots_used",
            0,
        ),
        detail_keys=(
            "inventory_slots_total",
            "inventory_slots_usable",
            "inventory_slots_free",
            "inventory_sample",
        ),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_inventory_slots_free",
        translation_key="character_inventory_slots_free",
        value_fn=lambda character: _detail_value(
            character,
            "inventory_slots_free",
            0,
        ),
        detail_keys=(
            "inventory_slots_total",
            "inventory_slots_usable",
            "inventory_slots_used",
            "inventory_sample",
        ),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_highest_skill",
        translation_key="character_highest_skill",
        value_fn=lambda character: _highest_skill_name(character),
        detail_keys=("highest_skill", "total_skill_level", "skill_levels", "stats"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_total_skill_level",
        translation_key="character_total_skill_level",
        value_fn=lambda character: _detail_value(
            character,
            "total_skill_level",
            0,
        ),
        detail_keys=("skill_levels", "highest_skill"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_money",
        translation_key="character_money",
        value_fn=lambda character: _detail_value(character, "money", 0),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_strength",
        translation_key="character_strength",
        value_fn=lambda character: _stat_value(character, "strength"),
        entity_registry_enabled_default=False,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_agility",
        translation_key="character_agility",
        value_fn=lambda character: _stat_value(character, "agility"),
        entity_registry_enabled_default=False,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_wisdom",
        translation_key="character_wisdom",
        value_fn=lambda character: _stat_value(character, "wisdom"),
        entity_registry_enabled_default=False,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_luck",
        translation_key="character_luck",
        value_fn=lambda character: _stat_value(character, "luck"),
        entity_registry_enabled_default=False,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_equipped_items",
        translation_key="character_equipped_items",
        value_fn=lambda character: _detail_value(
            character,
            "equipped_item_count",
            0,
        ),
        detail_keys=(
            "equipped_items",
            "equipped_tool_count",
            "equipped_tools",
            "equipped_food_count",
            "equipped_food",
            "attack_loadout",
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[IdleonRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Idleon sensors for a config entry."""
    coordinator = entry.runtime_data.coordinator
    added_character_ids: set[str] = set()

    def _new_character_entities() -> list[SensorEntity]:
        entities: list[SensorEntity] = []
        for character in coordinator.data.characters:
            if character.character_id in added_character_ids:
                continue
            added_character_ids.add(character.character_id)
            entities.extend(
                IdleonCharacterSensor(entry, coordinator, character, description)
                for description in CHARACTER_SENSOR_DESCRIPTIONS
            )
        return entities

    def _add_new_character_entities() -> None:
        if entities := _new_character_entities():
            async_add_entities(entities)

    entities: list[SensorEntity] = [
        IdleonAccountSensor(entry, coordinator, description)
        for description in ACCOUNT_SENSOR_DESCRIPTIONS
    ]
    entities.extend(_new_character_entities())
    async_add_entities(entities)
    entry.async_on_unload(coordinator.async_add_listener(_add_new_character_entities))


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

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return account timestamp details where useful."""
        if self.entity_description.key == "account_last_updated":
            attributes = {
                "source_updated_at": (
                    self.coordinator.data.source_updated_at.isoformat()
                    if self.coordinator.data.source_updated_at
                    else None
                ),
                "last_successful_update": (
                    self.coordinator.last_successful_update.isoformat()
                    if self.coordinator.last_successful_update
                    else None
                ),
            }
            return _remove_none_attributes(attributes)

        if not self.entity_description.detail_keys or not self.coordinator.data.details:
            return None
        attributes = {
            key: self.coordinator.data.details[key]
            for key in self.entity_description.detail_keys
            if key in self.coordinator.data.details
        }
        return attributes or None


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
        """Return details relevant to this character sensor."""
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
        name=_character_device_name(character),
        manufacturer="Legends of Idleon",
        model=character.character_class,
        via_device=(DOMAIN, _account_device_identifier(entry)),
    )


def _character_device_name(character: IdleonCharacter) -> str:
    """Return a readable character device name."""
    match = re.fullmatch(r"Character\s+(\d+)(?:\s+-\s+(.+))?", character.name)
    if match:
        character_number = match.group(1)
        character_name = match.group(2)
        if character_name:
            return f"Idleon Character {character_number} - {character_name}"
        return f"Idleon Character {character_number}"

    match = re.fullmatch(r"character_(\d+)", character.character_id)
    if match:
        character_number = int(match.group(1)) + 1
        return f"Idleon Character {character_number} - {character.name}"

    return f"Idleon Character - {character.name}"


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


def _select_detail_attributes(
    details: Mapping[str, Any],
    keys: tuple[str, ...],
) -> dict[str, Any]:
    """Return selected character detail attributes."""
    return {key: details[key] for key in keys if key in details}


def _remove_none_attributes(attributes: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return compact attributes without empty timestamp values."""
    compact_attributes = {
        key: value for key, value in attributes.items() if value is not None
    }
    return compact_attributes or None


def _detail_value(
    character: IdleonCharacter,
    key: str,
    default: Any = None,
) -> Any:
    """Return a single parsed character detail value."""
    return character.details.get(key, default)


def _account_detail_value(
    coordinator: IdleonDataUpdateCoordinator,
    key: str,
    default: Any = None,
) -> Any:
    """Return a single parsed account detail value."""
    return coordinator.data.details.get(key, default)


def _account_detail_count(
    coordinator: IdleonDataUpdateCoordinator,
    key: str,
) -> int:
    """Return the number of values in a grouped account detail."""
    value = coordinator.data.details.get(key)
    if isinstance(value, Mapping):
        return len(value)
    return 0


def _account_detail_nested_count(
    coordinator: IdleonDataUpdateCoordinator,
    key: str,
) -> int:
    """Return the number of nested values in a grouped account detail."""
    value = coordinator.data.details.get(key)
    if not isinstance(value, Mapping):
        return 0

    total = 0
    for detail_value in value.values():
        if isinstance(detail_value, Mapping):
            total += len(detail_value)
        else:
            total += 1
    return total


def _account_achievement_total(coordinator: IdleonDataUpdateCoordinator) -> int:
    """Return the total achieved achievements from grouped status details."""
    value = coordinator.data.details.get("achievement_status")
    if not isinstance(value, Mapping):
        return int(coordinator.data.details.get("achievements_completed", 0) or 0)

    total = 0
    for detail_value in value.values():
        if not isinstance(detail_value, Mapping):
            continue
        achieved = detail_value.get("achieved")
        if isinstance(achieved, int | float):
            total += int(achieved)
    return total


def _account_detail_sum(
    coordinator: IdleonDataUpdateCoordinator,
    key: str,
) -> int | float:
    """Return the numeric sum of values in a grouped account detail."""
    value = coordinator.data.details.get(key)
    if not isinstance(value, Mapping):
        return 0

    total = 0.0
    for detail_value in value.values():
        if isinstance(detail_value, int | float):
            total += detail_value
            continue
        try:
            total += float(detail_value)
        except TypeError, ValueError:
            continue
    if total.is_integer():
        return int(total)
    return round(total, 2)


def _account_total_money(coordinator: IdleonDataUpdateCoordinator) -> Any:
    """Return parsed account money using current and compatibility detail keys."""
    return coordinator.data.details.get(
        "total_money",
        coordinator.data.details.get("raw_money", 0),
    )


def _stat_value(character: IdleonCharacter, key: str) -> int:
    """Return a single parsed character stat value."""
    stats = character.details.get("stats")
    if not isinstance(stats, Mapping):
        return 0
    value = stats.get(key)
    if isinstance(value, int | float):
        return int(value)
    return 0


def _highest_skill_name(character: IdleonCharacter) -> str:
    """Return the character's highest parsed skill name."""
    highest_skill = character.details.get("highest_skill")
    if isinstance(highest_skill, Mapping):
        name = highest_skill.get("name")
        level = highest_skill.get("level")
        if name and level is not None:
            return f"{name} ({level})"
    return "Unknown"
