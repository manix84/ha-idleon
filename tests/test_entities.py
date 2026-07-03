"""Tests for Idleon entities."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.idleon.const import (
    CONF_DATA_SOURCE_TYPE,
    CONF_LOCAL_FILE_PATH,
    CONF_SCAN_INTERVAL,
    DATA_SOURCE_LOCAL_FILE,
    DOMAIN,
)
from custom_components.idleon.models import IdleonCharacter
from custom_components.idleon.sensor import _character_device_name


async def test_account_sensors(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test account sensors expose expected values."""
    entry = await _setup_entry(hass, sample_data_path)
    entity_registry = er.async_get(hass)

    total_level_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_total_level",
    )
    character_count_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_character_count",
    )
    gems_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_gems",
    )
    last_updated_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_last_updated",
    )
    last_updated_entity = entity_registry.async_get(last_updated_entity_id)
    highest_level_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_highest_character_level",
    )
    total_skill_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_total_skill_level",
    )
    total_money_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_total_money",
    )
    raw_money_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_raw_money",
    )
    raw_money_entity = entity_registry.async_get(raw_money_entity_id)
    green_stacks_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_green_stacks",
    )
    slab_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_slab_items_obtained",
    )
    achievements_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_achievements_completed",
    )
    currencies_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_currencies",
    )
    shrine_levels_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_shrine_levels",
    )
    statue_levels_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_statue_levels",
    )
    colosseum_scores_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_colosseum_scores",
    )
    minigame_scores_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_minigame_scores",
    )
    progress_totals_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_progress_totals",
    )
    pets_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_pets",
    )
    achievements_by_world_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_achievements_by_world",
    )
    task_levels_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_task_levels",
    )
    taskboard_merits_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_taskboard_merits",
    )
    taskboard_unlocks_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_taskboard_unlocks",
    )

    assert hass.states.get(total_level_entity_id).state == "365"
    assert hass.states.get(character_count_entity_id).state == "2"
    assert hass.states.get(gems_entity_id).state == "1234"
    assert hass.states.get(highest_level_entity_id).state == "210"
    assert hass.states.get(total_skill_entity_id).state == "205"
    assert hass.states.get(total_money_entity_id).state == "987654"
    assert raw_money_entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(raw_money_entity_id) is None
    assert hass.states.get(green_stacks_entity_id).state == "3"
    assert hass.states.get(slab_entity_id).state == "456"
    assert hass.states.get(achievements_entity_id).state == "78"
    assert hass.states.get(currencies_entity_id).state == "12"
    assert hass.states.get(shrine_levels_entity_id).state == "236"
    assert hass.states.get(statue_levels_entity_id).state == "848"
    assert hass.states.get(colosseum_scores_entity_id).state == "382839961.69"
    assert hass.states.get(minigame_scores_entity_id).state == "1827"
    assert hass.states.get(progress_totals_entity_id).state == "11"
    assert hass.states.get(pets_entity_id).state == "3"
    assert hass.states.get(achievements_by_world_entity_id).state == "78"
    assert hass.states.get(task_levels_entity_id).state == "2"
    assert hass.states.get(taskboard_merits_entity_id).state == "2"
    assert hass.states.get(taskboard_unlocks_entity_id).state == "3"
    highest_level_attributes = hass.states.get(highest_level_entity_id).attributes
    assert highest_level_attributes["highest_level_character"] == "Bubo Main"
    assert highest_level_attributes["class_counts"] == {
        "Bubonic Conjuror": 1,
        "Squire": 1,
    }
    assert hass.states.get(total_money_entity_id).attributes["money_breakdown"] == {
        "bank": 900000,
        "characters": 87654,
    }
    assert hass.states.get(green_stacks_entity_id).attributes["green_stack_sample"] == [
        "Oak Logs",
        "Copper Ore",
    ]
    assert (
        hass.states.get(currencies_entity_id).attributes["currencies"][
            "World Teleports"
        ]
        == 1700
    )
    assert (
        hass.states.get(currencies_entity_id).attributes["currencies"][
            "Forest Villa Keys"
        ]
        == 2737
    )
    assert (
        hass.states.get(shrine_levels_entity_id).attributes["shrine_levels"][
            "Primordial Shrine"
        ]
        == 23
    )
    assert (
        hass.states.get(statue_levels_entity_id).attributes["statue_levels"]["Power"]
        == 284
    )
    assert (
        hass.states.get(colosseum_scores_entity_id).attributes["colosseum_scores"][
            "Whimsical"
        ]
        == 266855608.33
    )
    assert (
        hass.states.get(minigame_scores_entity_id).attributes["minigame_scores"][
            "Poing"
        ]
        == 1471
    )
    assert (
        hass.states.get(progress_totals_entity_id).attributes["progress_totals"][
            "Highest Damage"
        ]
        == 123456789
    )
    assert hass.states.get(pets_entity_id).attributes["pets"]["Legacy Pets"] == {
        "Bored Bean": "1/2",
        "Slime": "0/1",
    }
    assert (
        hass.states.get(achievements_by_world_entity_id).attributes[
            "achievement_status"
        ]["World 1"]["progress"]["Achievement Hunter"]
        == 66
    )
    assert (
        hass.states.get(task_levels_entity_id).attributes["task_levels"]["World 1"][
            "Faceless Deathmachine"
        ]["progress_percent"]
        == 42
    )
    assert (
        hass.states.get(taskboard_merits_entity_id).attributes["taskboard_merits"][
            "World 2"
        ]["Obol drops"]
        == "3/7"
    )
    assert (
        hass.states.get(taskboard_unlocks_entity_id).attributes["taskboard_unlocks"][
            "Tab 1"
        ]["Militia Helm"]
        == "Available"
    )
    assert last_updated_entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(last_updated_entity_id) is None


async def test_character_sensors(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test character sensors expose expected values."""
    entry = await _setup_entry(hass, sample_data_path)
    entity_registry = er.async_get(hass)

    level_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_level",
    )
    class_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_class",
    )
    map_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_current_map",
    )
    activity_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_current_activity",
    )
    afk_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_afk_hours",
    )
    inventory_used_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_inventory_slots_used",
    )
    inventory_free_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_inventory_slots_free",
    )
    highest_skill_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_highest_skill",
    )
    total_skill_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_total_skill_level",
    )
    money_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_money",
    )
    wisdom_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_wisdom",
    )
    equipped_items_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_equipped_items",
    )

    assert hass.states.get(level_entity_id).state == "210"
    assert hass.states.get(class_entity_id).state == "Bubonic Conjuror"
    assert hass.states.get(map_entity_id).state == "Tremor Wurm Nest"
    assert hass.states.get(activity_entity_id).state == "AFK Fighting"
    assert hass.states.get(afk_entity_id).state == "12.5"
    assert hass.states.get(inventory_used_entity_id).state == "2"
    assert hass.states.get(inventory_free_entity_id).state == "1"
    assert hass.states.get(highest_skill_entity_id).state == "Alchemy (95)"
    assert hass.states.get(total_skill_entity_id).state == "205"
    assert hass.states.get(money_entity_id).state == "12345"
    assert hass.states.get(wisdom_entity_id) is None
    wisdom_registry_entry = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_wisdom",
    )
    assert wisdom_registry_entry is not None
    assert entity_registry.async_get(wisdom_registry_entry).disabled
    assert hass.states.get(equipped_items_entity_id).state == "4"

    highest_skill_attributes = hass.states.get(highest_skill_entity_id).attributes
    assert highest_skill_attributes["highest_skill"] == {
        "name": "Alchemy",
        "level": 95,
    }
    assert highest_skill_attributes["total_skill_level"] == 205
    assert highest_skill_attributes["skill_levels"]["Mining"] == 62
    assert highest_skill_attributes["stats"]["wisdom"] == 320

    equipped_items_attributes = hass.states.get(equipped_items_entity_id).attributes
    assert equipped_items_attributes["equipped_items"] == [
        "Farmer Brim",
        "Orange Tee",
    ]
    assert equipped_items_attributes["equipped_tool_count"] == 2
    assert equipped_items_attributes["equipped_food"] == ["Nomwich"]
    assert equipped_items_attributes["attack_loadout"] == [
        "Power Strike",
        "Book of the Wise",
    ]

    assert "inventory_slots_used" not in hass.states.get(level_entity_id).attributes
    assert "inventory_slots_used" not in hass.states.get(class_entity_id).attributes


async def test_binary_sensors(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test character binary sensors expose expected values."""
    entry = await _setup_entry(hass, sample_data_path)
    entity_registry = er.async_get(hass)

    inventory_entity_id = entity_registry.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_inventory_full",
    )
    attention_entity_id = entity_registry.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        f"{entry.entry_id}_miner_alt_character_needs_attention",
    )

    assert hass.states.get(inventory_entity_id).state == "on"
    assert hass.states.get(attention_entity_id).state == "off"

    inventory_attributes = hass.states.get(inventory_entity_id).attributes
    assert inventory_attributes["inventory_slots_total"] == 3
    assert inventory_attributes["inventory_slots_usable"] == 3
    assert inventory_attributes["inventory_slots_used"] == 2
    assert inventory_attributes["inventory_slots_free"] == 1
    assert inventory_attributes["inventory_sample"] == ["Nomwich", "Farmer Brim"]

    assert "inventory_slots_used" not in hass.states.get(attention_entity_id).attributes


async def test_device_model(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test account and character devices are created."""
    entry = await _setup_entry(hass, sample_data_path)
    device_registry = dr.async_get(hass)

    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{entry.entry_id}_account")}
    )
    character_device = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{entry.entry_id}_bubo_main")}
    )

    assert account_device is not None
    assert account_device.name == "Legends of Idleon Account"
    assert character_device is not None
    assert character_device.name == "Idleon Character - Bubo Main"
    assert character_device.via_device_id == account_device.id


def test_character_device_name_removes_duplicate_character_prefix() -> None:
    """Test indexed parser names become concise device names."""
    character = IdleonCharacter(
        character_id="character_0",
        name="Character 1 - Manix84",
        level=1,
        character_class="Death Bringer",
        current_map="Somewhere",
        current_activity="Fighting",
        afk_hours=1.0,
        inventory_full=False,
        needs_attention=False,
    )

    assert _character_device_name(character) == "Idleon Character 1 - Manix84"


def test_character_device_name_uses_indexed_character_id_fallback() -> None:
    """Test indexed character IDs still get numbered device names."""
    character = IdleonCharacter(
        character_id="character_9",
        name="Manix84_10",
        level=1,
        character_class="Elemental Sorcerer",
        current_map="Somewhere",
        current_activity="Fighting",
        afk_hours=1.0,
        inventory_full=False,
        needs_attention=False,
    )

    assert _character_device_name(character) == "Idleon Character 10 - Manix84_10"


async def _setup_entry(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> MockConfigEntry:
    """Set up a sample config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Idleon Local File",
        data={
            CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE,
            CONF_LOCAL_FILE_PATH: str(sample_data_path),
            CONF_SCAN_INTERVAL: 3600,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
