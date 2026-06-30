"""Tests for Idleon config entry lifecycle."""

from __future__ import annotations

from pathlib import Path
from typing import Self

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.idleon.const import (
    CONF_DATA_SOURCE_TYPE,
    CONF_LOCAL_FILE_PATH,
    CONF_REMOTE_URL,
    CONF_SCAN_INTERVAL,
    DATA_SOURCE_LOCAL_FILE,
    DATA_SOURCE_REMOTE_URL,
    DOMAIN,
)


class _FakeResponse:
    """Minimal aiohttp response fake."""

    def __init__(self, text: str) -> None:
        self._text = text

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        """Raise for HTTP status."""

    async def text(self) -> str:
        """Return response text."""
        return self._text


class _FakeSession:
    """Minimal aiohttp client session fake."""

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def get(self, *_args: object, **_kwargs: object) -> _FakeResponse:
        """Return the fake response context manager."""
        return self._response


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


async def test_remote_config_entry_sets_up_entities(
    hass: HomeAssistant,
    sample_data_path: Path,
    monkeypatch,
) -> None:
    """Test a remote URL config entry sets up entities from fetched JSON."""
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.client.async_get_clientsession",
        lambda _hass: _FakeSession(_FakeResponse(sample_data_path.read_text())),
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Idleon Remote URL",
        data={
            CONF_DATA_SOURCE_TYPE: DATA_SOURCE_REMOTE_URL,
            CONF_REMOTE_URL: "https://example.com/idleon.json",
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
    character_level_entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_bubo_main_character_level",
    )

    assert hass.states.get(total_level_entity_id).state == "365"
    assert hass.states.get(character_level_entity_id).state == "210"


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
