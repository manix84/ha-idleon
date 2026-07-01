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

    assert hass.states.get(total_level_entity_id).state == "365"
    assert hass.states.get(character_count_entity_id).state == "2"
    assert hass.states.get(gems_entity_id).state == "1234"


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

    assert hass.states.get(level_entity_id).state == "210"
    assert hass.states.get(class_entity_id).state == "Bubonic Conjuror"
    assert hass.states.get(map_entity_id).state == "Tremor Wurm Nest"
    assert hass.states.get(activity_entity_id).state == "AFK Fighting"
    assert hass.states.get(afk_entity_id).state == "12.5"

    level_attributes = hass.states.get(level_entity_id).attributes
    assert level_attributes["active_preset"] == 2
    assert level_attributes["inventory_slots_total"] == 3
    assert level_attributes["inventory_slots_used"] == 2
    assert level_attributes["inventory_slots_free"] == 1
    assert level_attributes["inventory_sample"] == ["Nomwich", "Farmer Brim"]

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
