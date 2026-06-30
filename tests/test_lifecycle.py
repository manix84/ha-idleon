"""Tests for Idleon config entry lifecycle."""

from __future__ import annotations

from pathlib import Path

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.idleon.const import (
    CONF_DATA_SOURCE_TYPE,
    CONF_LOCAL_FILE_PATH,
    CONF_SCAN_INTERVAL,
    DATA_SOURCE_LOCAL_FILE,
    DOMAIN,
)


async def test_config_entry_unload_and_reload(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test the config entry can be unloaded and set up again."""
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

    entity_registry = er.async_get(hass)
    total_level_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_total_level",
    )
    assert hass.states.get(total_level_entity_id) is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(total_level_entity_id).state == STATE_UNAVAILABLE

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(total_level_entity_id).state == "365"


async def test_failed_refresh_marks_entities_unavailable_then_recovers(
    hass: HomeAssistant,
    sample_data_path: Path,
    tmp_path: Path,
) -> None:
    """Test failed coordinator refreshes make entities unavailable and recover."""
    source_path = tmp_path / "idleon.json"
    source_path.write_text(sample_data_path.read_text())

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Idleon Local File",
        data={
            CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE,
            CONF_LOCAL_FILE_PATH: str(source_path),
            CONF_SCAN_INTERVAL: 3600,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    total_level_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_account_total_level",
    )
    assert hass.states.get(total_level_entity_id).state == "365"

    source_path.write_text("{not json")
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(total_level_entity_id).state == STATE_UNAVAILABLE
    assert entry.runtime_data.coordinator.last_error_type == "IdleonInvalidJson"

    source_path.write_text(sample_data_path.read_text())
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(total_level_entity_id).state == "365"
    assert entry.runtime_data.coordinator.last_error_type is None
