"""Sensor entities for HA Idleon."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import STATIC_URL_PATH, IdleonRuntimeData
from .const import DOMAIN, NAME
from .coordinator import IdleonDataUpdateCoordinator
from .models import IdleonCharacter
from .utils.number_format import (
    idleon_money_parts,
    idleon_number_parts,
    idleon_raw_value,
)

ASSETS_PATH = Path(__file__).with_name("assets")


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


LATER_WORLD_ACCOUNT_DETAIL_KEYS = (
    "world_4_cooking",
    "world_4_breeding",
    "world_4_laboratory",
    "world_4_rift",
    "world_4_tome",
    "world_5_sailing",
    "world_5_divinity",
    "world_5_gaming",
    "world_5_hole",
    "world_5_slab",
    "world_6_farming",
    "world_6_sneaking",
    "world_6_summoning",
    "world_6_beanstalk",
    "world_6_emperor",
    "world_7_spelunking",
    "world_7_research",
    "world_7_gallery",
    "world_7_legend_talents",
    "world_7_coral_reef",
    "world_7_zenith_market",
    "world_7_clam_work",
    "world_7_advice_fish",
    "world_7_minehead",
    "world_7_glimbo",
    "world_7_sushi_station",
    "world_7_the_button",
)


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
        entity_category=EntityCategory.DIAGNOSTIC,
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
        key="account_money",
        translation_key="account_money",
        value_fn=lambda coordinator: _account_money_formatted(coordinator),
        detail_keys=("money_breakdown",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_money_raw",
        translation_key="account_money_raw",
        value_fn=lambda coordinator: _account_money_raw(coordinator),
        detail_keys=("money_breakdown",),
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
        detail_keys=("achievement_status",),
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
    IdleonAccountSensorEntityDescription(
        key="account_world_1_anvil",
        translation_key="account_world_1_anvil",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_1_anvil",
        ),
        detail_keys=("world_1_anvil",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_1_bribes",
        translation_key="account_world_1_bribes",
        value_fn=lambda coordinator: _account_detail_count(
            coordinator,
            "world_1_bribes",
        ),
        detail_keys=("world_1_bribes",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_1_stamps",
        translation_key="account_world_1_stamps",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_1_stamps",
        ),
        detail_keys=("world_1_stamps",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_summaries",
        translation_key="account_world_summaries",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_summaries",
        ),
        detail_keys=("world_summaries",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_cauldron",
        translation_key="account_world_2_cauldron",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_2_cauldron",
        ),
        detail_keys=("world_2_cauldron",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_vials",
        translation_key="account_world_2_vials",
        value_fn=lambda coordinator: _account_detail_count(
            coordinator,
            "world_2_vials",
        ),
        detail_keys=("world_2_vials",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_bubbles",
        translation_key="account_world_2_bubbles",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_2_bubbles",
        ),
        detail_keys=("world_2_bubbles",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_sigils",
        translation_key="account_world_2_sigils",
        value_fn=lambda coordinator: _account_detail_count(
            coordinator,
            "world_2_sigils",
        ),
        detail_keys=("world_2_sigils",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_vote_ballots",
        translation_key="account_world_2_vote_ballots",
        value_fn=lambda coordinator: _account_detail_count(
            coordinator,
            "world_2_vote_ballots",
        ),
        detail_keys=("world_2_vote_ballots",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_killroy",
        translation_key="account_world_2_killroy",
        value_fn=lambda coordinator: _account_world_2_killroy_rooms_available(
            coordinator
        ),
        detail_keys=("world_2_killroy",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_printer",
        translation_key="account_world_3_printer",
        value_fn=lambda coordinator: _account_detail_value_from_mapping(
            coordinator,
            "world_3_printer",
            "total_printed",
        ),
        detail_keys=("world_3_printer",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_refinery",
        translation_key="account_world_3_refinery",
        value_fn=lambda coordinator: _account_detail_value_from_mapping(
            coordinator,
            "world_3_refinery",
            "refined_salt_total",
        ),
        detail_keys=("world_3_refinery",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_atom_collider",
        translation_key="account_world_3_atom_collider",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_atom_collider",
        ),
        detail_keys=("world_3_atom_collider",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_equinox",
        translation_key="account_world_3_equinox",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_equinox",
        ),
        detail_keys=("world_3_equinox",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_buildings",
        translation_key="account_world_3_buildings",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_buildings",
        ),
        detail_keys=("world_3_buildings",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_death_note",
        translation_key="account_world_3_death_note",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_death_note",
        ),
        detail_keys=("world_3_death_note",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_worship",
        translation_key="account_world_3_worship",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_worship",
        ),
        detail_keys=("world_3_worship",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_prayers",
        translation_key="account_world_3_prayers",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_prayers",
        ),
        detail_keys=("world_3_prayers",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_traps",
        translation_key="account_world_3_traps",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_traps",
        ),
        detail_keys=("world_3_traps",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_salt_lick",
        translation_key="account_world_3_salt_lick",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_salt_lick",
        ),
        detail_keys=("world_3_salt_lick",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_construction",
        translation_key="account_world_3_construction",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_construction",
        ),
        detail_keys=("world_3_construction",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_armor_smithy",
        translation_key="account_world_3_armor_smithy",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_armor_smithy",
        ),
        detail_keys=("world_3_armor_smithy",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_hat_rack",
        translation_key="account_world_3_hat_rack",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_hat_rack",
        ),
        detail_keys=("world_3_hat_rack",),
    ),
    *(
        IdleonAccountSensorEntityDescription(
            key=f"account_{detail_key}",
            translation_key=f"account_{detail_key}",
            value_fn=lambda coordinator, detail_key=detail_key: (
                _account_detail_nested_count(coordinator, detail_key)
            ),
            detail_keys=(detail_key,),
        )
        for detail_key in LATER_WORLD_ACCOUNT_DETAIL_KEYS
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
        value_fn=lambda character: _character_money_formatted(character),
        detail_keys=("money",),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_money_raw",
        translation_key="character_money_raw",
        value_fn=lambda character: _character_money_raw(character),
        detail_keys=("money",),
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

NUMERIC_ACCOUNT_SENSOR_KEYS = frozenset(
    description.key
    for description in ACCOUNT_SENSOR_DESCRIPTIONS
    if description.key
    not in {
        "account_last_updated",
        "account_money",
        "account_money_raw",
    }
)
NUMERIC_CHARACTER_SENSOR_KEYS = frozenset(
    description.key
    for description in CHARACTER_SENSOR_DESCRIPTIONS
    if description.key
    not in {
        "character_class",
        "character_current_map",
        "character_current_activity",
        "character_highest_skill",
        "character_money",
        "character_money_raw",
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[IdleonRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Idleon sensors for a config entry."""
    coordinator = entry.runtime_data.coordinator
    added_character_sensor_ids: set[str] = set()
    added_storage_sensor_ids: set[tuple[str, str]] = set()

    def _new_character_entities() -> list[SensorEntity]:
        entities: list[SensorEntity] = []
        for character in coordinator.data.characters:
            if character.character_id not in added_character_sensor_ids:
                added_character_sensor_ids.add(character.character_id)
                entities.extend(
                    IdleonCharacterSensor(entry, coordinator, character, description)
                    for description in CHARACTER_SENSOR_DESCRIPTIONS
                )

            for storage_type in _character_storage_capacities(character):
                sensor_id = (character.character_id, storage_type)
                if sensor_id in added_storage_sensor_ids:
                    continue
                added_storage_sensor_ids.add(sensor_id)
                entities.append(
                    IdleonCharacterStorageCapacitySensor(
                        entry,
                        coordinator,
                        character,
                        storage_type,
                    )
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
        if description.key in NUMERIC_ACCOUNT_SENSOR_KEYS:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def entity_picture(self) -> str | None:
        """Return the current coin tier picture for formatted money."""
        if self.entity_description.key != "account_money":
            return None
        return _money_entity_picture(_account_money_raw(self.coordinator))

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

        if self.entity_description.key == "account_money":
            attributes = _money_attributes(_account_money_raw(self.coordinator))
            money_breakdown = _money_breakdown_attributes(self.coordinator)
            if money_breakdown:
                attributes["money_breakdown"] = money_breakdown
            return attributes

        if self.entity_description.key == "account_money_raw":
            money_breakdown = _money_breakdown_attributes(self.coordinator)
            if money_breakdown:
                return {"money_breakdown": money_breakdown}
            return None

        if not self.entity_description.detail_keys or not self.coordinator.data.details:
            return None
        attributes = {
            key: _normalize_attribute_value(self.coordinator.data.details[key])
            for key in self.entity_description.detail_keys
            if key in self.coordinator.data.details
        }
        return _normalize_attribute_value(attributes) or None


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
        if description.key in NUMERIC_CHARACTER_SENSOR_KEYS:
            self._attr_state_class = SensorStateClass.MEASUREMENT

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
    def entity_picture(self) -> str | None:
        """Return an entity picture for sensors with visual assets."""
        character = self._character
        if character is None:
            return None
        if self.entity_description.key == "character_class":
            return _class_entity_picture(character.character_class)
        if self.entity_description.key != "character_money":
            return None
        return _money_entity_picture(_character_money_raw(character))

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return details relevant to this character sensor."""
        if not self.entity_description.detail_keys:
            return None
        character = self._character
        if character is None or not character.details:
            return None
        if self.entity_description.key == "character_money":
            return _money_attributes(_character_money_raw(character))
        attributes = _select_detail_attributes(
            character.details,
            self.entity_description.detail_keys,
        )
        return _normalize_attribute_value(attributes) or None

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


class IdleonCharacterStorageCapacitySensor(
    CoordinatorEntity[IdleonDataUpdateCoordinator],
    SensorEntity,
):
    """Character storage pouch capacity sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        entry: ConfigEntry[IdleonRuntimeData],
        coordinator: IdleonDataUpdateCoordinator,
        character: IdleonCharacter,
        storage_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._character_id = character.character_id
        self._storage_type = storage_type
        self._attr_name = f"{storage_type} storage capacity"
        self._attr_unique_id = (
            f"{entry.entry_id}_{_slugify(character.character_id)}_"
            f"character_storage_capacity_{_slugify(storage_type)}"
        )
        self._attr_device_info = _character_device_info(entry, character)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self._storage_capacity is not None

    @property
    def native_value(self) -> int | None:
        """Return the current maximum storage capacity."""
        details = self._storage_capacity
        if not details:
            return None
        value = details.get("maximum_capacity")
        return value if isinstance(value, int) else None

    @property
    def entity_picture(self) -> str | None:
        """Return the largest acquired pouch picture."""
        details = self._storage_capacity
        if not details:
            return None
        asset_name = details.get("largest_pouch_asset")
        if not isinstance(asset_name, str) or not asset_name:
            return None
        if not (ASSETS_PATH / asset_name).is_file():
            return None
        return f"{STATIC_URL_PATH}/{asset_name}"

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return capacity and pouch metadata."""
        details = self._storage_capacity
        if not details:
            return None
        return _normalize_attribute_value(details) or None

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

    @property
    def _storage_capacity(self) -> Mapping[str, Any] | None:
        """Return the current storage capacity details."""
        character = self._character
        if character is None:
            return None
        storage_capacities = _character_storage_capacities(character)
        details = storage_capacities.get(self._storage_type)
        return details if isinstance(details, Mapping) else None


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


def _character_storage_capacities(
    character: IdleonCharacter,
) -> Mapping[str, Any]:
    """Return parsed storage capacity details for a character."""
    value = character.details.get("storage_capacities")
    return value if isinstance(value, Mapping) else {}


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


def _account_detail_value_from_mapping(
    coordinator: IdleonDataUpdateCoordinator,
    detail_key: str,
    value_key: str,
    default: Any = 0,
) -> Any:
    """Return a single value from a grouped account detail."""
    value = coordinator.data.details.get(detail_key)
    if not isinstance(value, Mapping):
        return default
    return value.get(value_key, default)


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


def _account_money_formatted(coordinator: IdleonDataUpdateCoordinator) -> str:
    """Return account money with Idleon-style number suffixes."""
    return idleon_number_parts(_account_money_raw(coordinator)).formatted


def _account_money_raw(coordinator: IdleonDataUpdateCoordinator) -> str:
    """Return exact account money as a raw copper string."""
    value = coordinator.data.details.get("raw_money")
    if value is None:
        value = coordinator.data.details.get("total_money", 0)
    return idleon_raw_value(value)


def _character_money_formatted(character: IdleonCharacter) -> str:
    """Return character money with Idleon-style number suffixes."""
    return idleon_number_parts(_character_money_raw(character)).formatted


def _character_money_raw(character: IdleonCharacter) -> str:
    """Return exact character money as a raw copper string."""
    return idleon_raw_value(character.details.get("money", 0))


def _money_attributes(raw_value: str) -> dict[str, str]:
    """Return standard formatted money attributes."""
    formatted_money = idleon_money_parts(raw_value)
    formatted_number = idleon_number_parts(raw_value)
    return {
        "raw_value": formatted_money.raw_value,
        "coin_tier_formatted": formatted_money.formatted,
        "coin_tier": formatted_money.coin_tier,
        "coin_tier_value": formatted_money.coin_tier_value,
        "formatted_number": formatted_number.formatted,
        "number_suffix": formatted_number.suffix,
        "number_mantissa": formatted_number.mantissa,
    }


def _money_entity_picture(raw_value: str) -> str:
    """Return the image URL for the current money coin tier."""
    formatted_money = idleon_money_parts(raw_value)
    coin_slug = formatted_money.coin_tier.lower().replace(" ", "_")
    return f"{STATIC_URL_PATH}/coins/{coin_slug}.png"


def _class_entity_picture(character_class: str) -> str | None:
    """Return the image URL for a character class icon."""
    class_slug = _slugify(character_class)
    if not class_slug:
        return None
    class_icons = sorted((ASSETS_PATH / "classes").glob(f"*/{class_slug}_icon.png"))
    if not class_icons:
        return None
    class_icon = class_icons[0]
    return f"{STATIC_URL_PATH}/{class_icon.relative_to(ASSETS_PATH).as_posix()}"


def _money_breakdown_attributes(
    coordinator: IdleonDataUpdateCoordinator,
) -> dict[str, str] | None:
    """Return money breakdown values as exact raw-value strings."""
    money_breakdown = coordinator.data.details.get("money_breakdown")
    if not isinstance(money_breakdown, Mapping):
        return None
    return {str(key): idleon_raw_value(value) for key, value in money_breakdown.items()}


def _account_world_2_killroy_rooms_available(
    coordinator: IdleonDataUpdateCoordinator,
) -> int:
    """Return parsed Killroy room count for the World 2 Killroy sensor state."""
    value = coordinator.data.details.get("world_2_killroy")
    if not isinstance(value, Mapping):
        return 0
    rooms_available = value.get("rooms_available")
    if isinstance(rooms_available, int | float):
        return int(rooms_available)
    return 0


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


def _normalize_attribute_value(value: Any) -> Any:
    """Return Home Assistant friendly attributes with integral floats compacted."""
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    if isinstance(value, Mapping):
        return {key: _normalize_attribute_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_attribute_value(item) for item in value]
    return value
