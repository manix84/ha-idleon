"""Tests for Idleon diagnostics."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.idleon.const import (
    CONF_DATA_SOURCE_TYPE,
    CONF_LOCAL_FILE_PATH,
    CONF_REMOTE_URL,
    CONF_SCAN_INTERVAL,
    DATA_SOURCE_LOCAL_FILE,
    DOMAIN,
    VERSION,
)
from custom_components.idleon.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_redaction(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test diagnostics redact sensitive source details."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Idleon Local File",
        data={
            CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE,
            CONF_LOCAL_FILE_PATH: str(sample_data_path),
            CONF_REMOTE_URL: "https://example.com/data.json?token=secret",
            CONF_SCAN_INTERVAL: 3600,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["integration"]["version"] == VERSION
    assert diagnostics["data_source"]["local_file_path"] == "<redacted local file path>"
    assert diagnostics["data_source"]["remote_url"] == (
        "https://example.com/data.json?REDACTED"
    )
    assert diagnostics["account"]["character_count"] == 2
    assert diagnostics["account"]["source_updated_at"] == "2026-06-29T12:00:00+00:00"
    assert "raw" not in diagnostics
    assert "characters" not in diagnostics["account"]
