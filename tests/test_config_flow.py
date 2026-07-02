"""Tests for the Idleon config flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self

from aiohttp import ClientError, ClientResponseError
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.idleon.const import (
    AUTH_PROVIDER_EMAIL,
    AUTH_PROVIDER_GOOGLE,
    CONF_AUTH_PROVIDER,
    CONF_DATA_SOURCE_TYPE,
    CONF_IDLEON_EMAIL,
    CONF_IDLEON_PASSWORD,
    CONF_IDLEON_REFRESH_TOKEN,
    CONF_IDLEON_USER_ID,
    CONF_LOCAL_FILE_PATH,
    CONF_REMOTE_URL,
    CONF_SCAN_INTERVAL,
    DATA_SOURCE_IDLEON_CLOUD,
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

    async def json(self) -> Any:
        """Return response JSON."""
        raise AssertionError("JSON was not configured for this fake response")


class _FakeSession:
    """Minimal aiohttp client session fake."""

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def get(self, *_args: object, **_kwargs: object) -> _FakeResponse:
        """Return the fake response context manager."""
        return self._response


class _FakeJsonResponse:
    """Minimal aiohttp JSON response fake."""

    def __init__(
        self,
        data: Any,
        *,
        status_error: int | None = None,
        status: int = 200,
    ) -> None:
        self._data = data
        self._status_error = status_error
        self.status = status_error or status

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        """Raise a configured HTTP error."""
        if self._status_error is not None:
            raise ClientResponseError(
                request_info=None,
                history=(),
                status=self._status_error,
            )

    async def json(self) -> Any:
        """Return response JSON."""
        return self._data


class _FakeCloudSession:
    """Minimal aiohttp client session fake for Firebase calls."""

    def __init__(self, responses: list[_FakeJsonResponse]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str]] = []

    def post(self, url: str, **_kwargs: object) -> _FakeJsonResponse:
        """Return the next fake POST response."""
        self.requests.append(("POST", url))
        return self._responses.pop(0)

    def get(self, url: str, **_kwargs: object) -> _FakeJsonResponse:
        """Return the next fake GET response."""
        self.requests.append(("GET", url))
        return self._responses.pop(0)


def _cloud_firestore_document() -> dict[str, Any]:
    """Return a minimal Firestore REST document for one character."""
    return {
        "fields": {
            "CharacterClass_0": {"integerValue": "14"},
            "CurrentMap_0": {"integerValue": "325"},
            "Lv0_0": {
                "arrayValue": {
                    "values": [
                        {"integerValue": "1134"},
                    ],
                },
            },
            "GemsOwned": {"integerValue": "123"},
        }
    }


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


async def test_config_flow_invalid_schema(
    hass: HomeAssistant,
    tmp_path: Path,
) -> None:
    """Test structurally invalid local JSON returns a schema error."""
    invalid_schema_path = tmp_path / "idleon.json"
    invalid_schema_path.write_text('{"not_characters": []}')

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DATA_SOURCE_TYPE: DATA_SOURCE_LOCAL_FILE},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCAL_FILE_PATH: str(invalid_schema_path),
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_schema"}


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


async def test_config_flow_success_idleon_cloud_email(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test creating an entry from Idleon Cloud email/password auth."""
    fake_session = _FakeCloudSession(
        [
            _FakeJsonResponse(
                {
                    "idToken": "setup-id-token",
                    "refreshToken": "setup-refresh-token",
                    "localId": "uid-123",
                    "email": "player@example.com",
                }
            ),
            _FakeJsonResponse(
                {
                    "id_token": "refresh-id-token",
                    "refresh_token": "stored-refresh-token",
                    "user_id": "uid-123",
                }
            ),
            _FakeJsonResponse(["Manix84"]),
            _FakeJsonResponse(_cloud_firestore_document()),
        ]
    )
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.cloud.async_get_clientsession",
        lambda _hass: fake_session,
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_DATA_SOURCE_TYPE: AUTH_PROVIDER_EMAIL,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "source"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_IDLEON_EMAIL: "player@example.com",
            CONF_IDLEON_PASSWORD: "super-secret",
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Idleon Cloud"
    assert result["data"][CONF_DATA_SOURCE_TYPE] == DATA_SOURCE_IDLEON_CLOUD
    assert result["data"][CONF_IDLEON_EMAIL] == "player@example.com"
    assert result["data"][CONF_IDLEON_USER_ID] == "uid-123"
    assert result["data"][CONF_IDLEON_REFRESH_TOKEN] == "setup-refresh-token"
    assert CONF_IDLEON_PASSWORD not in result["data"]
    assert fake_session.requests[0][0] == "POST"
    assert "signInWithPassword" in fake_session.requests[0][1]


async def test_config_flow_idleon_cloud_auth_failure(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test Idleon Cloud auth failure returns a clean error."""
    fake_session = _FakeCloudSession([_FakeJsonResponse({}, status_error=400)])
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.cloud.async_get_clientsession",
        lambda _hass: fake_session,
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_DATA_SOURCE_TYPE: AUTH_PROVIDER_EMAIL,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_IDLEON_EMAIL: "player@example.com",
            CONF_IDLEON_PASSWORD: "wrong-password",
            CONF_SCAN_INTERVAL: 3600,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "auth_failed"}


async def test_config_flow_success_idleon_cloud_google(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test creating an entry from Idleon Cloud Google device auth."""
    fake_session = _FakeCloudSession(
        [
            _FakeJsonResponse(
                {
                    "device_code": "device-code",
                    "user_code": "ABCD-EFGH",
                    "verification_url": "https://www.google.com/device",
                    "verification_url_complete": (
                        "https://www.google.com/device?user_code=ABCD-EFGH"
                    ),
                    "expires_in": 1800,
                    "interval": 5,
                }
            ),
            _FakeJsonResponse({"id_token": "google-id-token"}),
            _FakeJsonResponse(
                {
                    "idToken": "firebase-id-token",
                    "refreshToken": "firebase-refresh-token",
                    "localId": "uid-google",
                    "email": "player@gmail.com",
                }
            ),
            _FakeJsonResponse(
                {
                    "id_token": "refresh-id-token",
                    "refresh_token": "stored-refresh-token",
                    "user_id": "uid-google",
                }
            ),
            _FakeJsonResponse(["Manix84"]),
            _FakeJsonResponse(_cloud_firestore_document()),
        ]
    )
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.cloud.async_get_clientsession",
        lambda _hass: fake_session,
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_DATA_SOURCE_TYPE: AUTH_PROVIDER_GOOGLE,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "source"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 3600},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "google"
    assert result["description_placeholders"]["user_code"] == "ABCD-EFGH"
    assert (
        result["description_placeholders"]["verification_url_complete"]
        == "https://www.google.com/device?user_code=ABCD-EFGH"
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Idleon Cloud"
    assert result["data"][CONF_DATA_SOURCE_TYPE] == DATA_SOURCE_IDLEON_CLOUD
    assert result["data"][CONF_AUTH_PROVIDER] == AUTH_PROVIDER_GOOGLE
    assert result["data"][CONF_IDLEON_EMAIL] == "player@gmail.com"
    assert result["data"][CONF_IDLEON_USER_ID] == "uid-google"
    assert result["data"][CONF_IDLEON_REFRESH_TOKEN] == "firebase-refresh-token"
    assert CONF_IDLEON_PASSWORD not in result["data"]
    assert "device/code" in fake_session.requests[0][1]
    assert "accounts:signInWithIdp" in fake_session.requests[2][1]


async def test_config_flow_idleon_cloud_google_pending(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test pending Google device auth asks the user to submit again."""
    fake_session = _FakeCloudSession(
        [
            _FakeJsonResponse(
                {
                    "device_code": "device-code",
                    "user_code": "ABCD-EFGH",
                    "verification_url": "https://www.google.com/device",
                    "verification_url_complete": (
                        "https://www.google.com/device?user_code=ABCD-EFGH"
                    ),
                    "expires_in": 1800,
                    "interval": 5,
                }
            ),
            _FakeJsonResponse({"error": "authorization_pending"}, status=400),
        ]
    )
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.cloud.async_get_clientsession",
        lambda _hass: fake_session,
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_DATA_SOURCE_TYPE: AUTH_PROVIDER_GOOGLE,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 3600},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "google"
    assert result["errors"] == {"base": "authorization_pending"}


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


async def test_options_flow_updates_refresh_interval(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test options flow only stores refresh settings."""
    config_entry = await _create_local_file_entry(hass, sample_data_path)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 7200,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SCAN_INTERVAL: 7200}
    assert config_entry.title == "Idleon Local File"
    assert config_entry.data[CONF_LOCAL_FILE_PATH] == str(sample_data_path)


async def test_options_flow_accepts_minimum_refresh_interval(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test options flow accepts the minimum refresh interval."""
    config_entry = await _create_local_file_entry(hass, sample_data_path)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 300,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SCAN_INTERVAL: 300}


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
