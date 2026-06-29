"""Tests for the Idleon config flow."""

from __future__ import annotations

from pathlib import Path

from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

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

    async def __aenter__(self) -> "_FakeResponse":
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
        data={
            CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE,
            CONF_LOCAL_FILE_PATH: str(sample_data_path),
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is config_entries.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Idleon Local File"
    assert result["data"][CONF_LOCAL_FILE_PATH] == str(sample_data_path)


async def test_config_flow_invalid_file(hass: HomeAssistant, tmp_path: Path) -> None:
    """Test an unreadable local file returns a clean error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE,
            CONF_LOCAL_FILE_PATH: str(tmp_path / "missing.json"),
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is config_entries.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


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
        data={
            CONF_DATA_SOURCE_TYPE: DATA_SOURCE_REMOTE_URL,
            CONF_REMOTE_URL: "https://example.com/idleon.json?token=secret",
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is config_entries.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Idleon Remote URL"


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
        data={
            CONF_DATA_SOURCE_TYPE: DATA_SOURCE_REMOTE_URL,
            CONF_REMOTE_URL: "https://example.com/idleon.json",
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is config_entries.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

