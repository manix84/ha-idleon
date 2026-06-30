"""Tests for the Idleon config flow."""

from __future__ import annotations

from pathlib import Path
from typing import Self

from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
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

    def __init__(self, text: str, *, error: Exception | None = None) -> None:
        self._text = text
        self._error = error

    async def __aenter__(self) -> Self:
        if self._error:
            raise self._error
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


async def test_config_flow_success_local_file(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test creating an entry from a local JSON file."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "source"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCAL_FILE_PATH: str(sample_data_path),
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Idleon Local File"
    assert result["data"][CONF_DATA_SOURCE_TYPE] == DATA_SOURCE_LOCAL_FILE
    assert result["data"][CONF_LOCAL_FILE_PATH] == str(sample_data_path)


async def test_config_flow_invalid_file(hass: HomeAssistant, tmp_path: Path) -> None:
    """Test an unreadable local file returns a clean error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCAL_FILE_PATH: str(tmp_path / "missing.json"),
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_invalid_local_json(
    hass: HomeAssistant,
    tmp_path: Path,
) -> None:
    """Test malformed local JSON returns a clean error."""
    invalid_json_path = tmp_path / "idleon.json"
    invalid_json_path.write_text("{not json")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCAL_FILE_PATH: str(invalid_json_path),
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_json"}


async def test_config_flow_success_remote_url(
    hass: HomeAssistant,
    sample_data_path: Path,
    monkeypatch,
) -> None:
    """Test creating an entry from a remote JSON URL."""
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.client.async_get_clientsession",
        lambda _hass: _FakeSession(_FakeResponse(sample_data_path.read_text())),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_REMOTE_URL},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "source"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REMOTE_URL: "https://example.com/idleon.json?token=secret",
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Idleon Remote URL"
    assert result["data"][CONF_DATA_SOURCE_TYPE] == DATA_SOURCE_REMOTE_URL


async def test_config_flow_invalid_url(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test a remote fetch failure returns a clean error."""
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.client.async_get_clientsession",
        lambda _hass: _FakeSession(
            _FakeResponse("", error=ClientError("connection failed"))
        ),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_REMOTE_URL},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REMOTE_URL: "https://example.com/idleon.json",
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_remote_timeout(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test a remote timeout returns a clean connection error."""
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.client.async_get_clientsession",
        lambda _hass: _FakeSession(_FakeResponse("", error=TimeoutError("timed out"))),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_REMOTE_URL},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REMOTE_URL: "https://example.com/idleon.json",
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_remote_invalid_json(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test malformed remote JSON returns a clean error."""
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.client.async_get_clientsession",
        lambda _hass: _FakeSession(_FakeResponse("{not json")),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_REMOTE_URL},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REMOTE_URL: "https://example.com/idleon.json",
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_json"}


async def test_config_flow_duplicate_source_aborts(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test configuring the same source twice aborts cleanly."""
    first_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE},
    )
    first_result = await hass.config_entries.flow.async_configure(
        first_result["flow_id"],
        user_input={
            CONF_LOCAL_FILE_PATH: str(sample_data_path),
            CONF_SCAN_INTERVAL: 3600,
        },
    )
    assert first_result["type"] is FlowResultType.CREATE_ENTRY

    second_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE},
    )
    second_result = await hass.config_entries.flow.async_configure(
        second_result["flow_id"],
        user_input={
            CONF_LOCAL_FILE_PATH: str(sample_data_path),
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert second_result["type"] is FlowResultType.ABORT
    assert second_result["reason"] == "already_configured"


async def test_options_flow_updates_source(
    hass: HomeAssistant,
    sample_data_path: Path,
    tmp_path: Path,
) -> None:
    """Test options flow validates and stores updated source settings."""
    updated_path = tmp_path / "updated_idleon_data.json"
    updated_path.write_text(sample_data_path.read_text())

    config_entry = await _create_local_file_entry(hass, sample_data_path)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "source"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCAL_FILE_PATH: str(updated_path),
            CONF_SCAN_INTERVAL: 7200,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE,
        CONF_LOCAL_FILE_PATH: str(updated_path),
        CONF_SCAN_INTERVAL: 7200,
    }


async def _create_local_file_entry(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> MockConfigEntry:
    """Create a local file config entry without setting it up."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Idleon Local File",
        data={
            CONF_LOCAL_FILE_PATH: str(sample_data_path),
            CONF_SCAN_INTERVAL: 3600,
            CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE,
        },
    )
    entry.add_to_hass(hass)
    return entry
