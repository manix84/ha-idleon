"""Tests for the Idleon config flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self
from urllib.parse import parse_qs, urlsplit

from aiohttp import ClientError, ClientResponseError
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from yarl import URL

from custom_components.idleon.const import (
    AUTH_PROVIDER_APPLE,
    AUTH_PROVIDER_EMAIL,
    AUTH_PROVIDER_GOOGLE,
    AUTH_PROVIDER_STEAM,
    CONF_AUTH_PROVIDER,
    CONF_DATA_SOURCE_TYPE,
    CONF_IDLEON_EMAIL,
    CONF_IDLEON_PASSWORD,
    CONF_IDLEON_REFRESH_TOKEN,
    CONF_IDLEON_USER_ID,
    CONF_LOCAL_FILE_PATH,
    CONF_REMOTE_URL,
    CONF_SCAN_INTERVAL,
    CONF_STEAM_CALLBACK_STATE,
    CONF_STEAM_OPENID_RESPONSE_URL,
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
        self.requests: list[tuple[str, str, dict[str, object]]] = []

    def post(self, url: str, **kwargs: object) -> _FakeJsonResponse:
        """Return the next fake POST response."""
        self.requests.append(("POST", url, kwargs))
        return self._responses.pop(0)

    def get(self, url: str, **kwargs: object) -> _FakeJsonResponse:
        """Return the next fake GET response."""
        self.requests.append(("GET", url, kwargs))
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


def _steam_openid_response_url(return_to: str) -> str:
    """Return a synthetic Steam OpenID response URL."""
    return str(
        URL(return_to).update_query(
            {
                "openid.ns": "http://specs.openid.net/auth/2.0",
                "openid.mode": "id_res",
                "openid.op_endpoint": "https://steamcommunity.com/openid/login",
                "openid.claimed_id": "https://steamcommunity.com/openid/id/123",
                "openid.identity": "https://steamcommunity.com/openid/id/123",
                "openid.return_to": return_to,
                "openid.response_nonce": "nonce",
                "openid.assoc_handle": "assoc",
                "openid.signed": "signed,fields",
                "openid.sig": "signature",
            }
        )
    )


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


async def test_config_flow_success_idleon_cloud_apple(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test creating an entry from Apple auth."""
    fake_session = _FakeCloudSession(
        [
            _FakeJsonResponse(
                {
                    "device_code": "apple-device-code",
                    "h_nonce": "apple-nonce",
                    "statusToken": "apple-status-token",
                }
            ),
            _FakeJsonResponse(
                {
                    "id_token": "apple-id-token",
                    "nonce": "apple-raw-nonce",
                }
            ),
            _FakeJsonResponse(
                {
                    "idToken": "firebase-id-token",
                    "refreshToken": "firebase-refresh-token",
                    "localId": "uid-apple",
                    "email": "apple@example.com",
                }
            ),
            _FakeJsonResponse(
                {
                    "id_token": "refresh-id-token",
                    "refresh_token": "stored-refresh-token",
                    "user_id": "uid-apple",
                }
            ),
            _FakeJsonResponse(["AppleChar"]),
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
            CONF_DATA_SOURCE_TYPE: AUTH_PROVIDER_APPLE,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "apple"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 3600},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "apple"
    authorization_url = result["description_placeholders"]["authorization_url"]
    assert "appleid.apple.com/auth/authorize" in authorization_url
    authorization_params = parse_qs(urlsplit(authorization_url).query)
    assert authorization_params["client_id"] == ["com.lavaflame.idleon.service.signin"]
    assert authorization_params["code"] == ["apple-device-code"]
    assert authorization_params["state"] == ["apple-status-token"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Idleon Cloud"
    assert result["data"][CONF_DATA_SOURCE_TYPE] == DATA_SOURCE_IDLEON_CLOUD
    assert result["data"][CONF_AUTH_PROVIDER] == AUTH_PROVIDER_APPLE
    assert result["data"][CONF_IDLEON_EMAIL] == "apple@example.com"
    assert result["data"][CONF_IDLEON_USER_ID] == "uid-apple"
    assert result["data"][CONF_IDLEON_REFRESH_TOKEN] == "firebase-refresh-token"
    assert "cloudfunctions.net/tspa" in fake_session.requests[0][1]
    assert "cloudfunctions.net/capsc" in fake_session.requests[1][1]
    status_payload = fake_session.requests[1][2]["data"]
    assert status_payload == {
        "device_code": "apple-device-code",
        "statusToken": "apple-status-token",
    }
    assert "accounts:signInWithIdp" in fake_session.requests[2][1]
    apple_payload = fake_session.requests[2][2]["json"]
    assert isinstance(apple_payload, dict)
    assert apple_payload["postBody"] == (
        "id_token=apple-id-token&nonce=apple-raw-nonce&providerId=apple.com"
    )


async def test_config_flow_idleon_cloud_apple_authorization_pending(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test an unfinished Apple authorization returns a clean pending error."""
    fake_session = _FakeCloudSession(
        [
            _FakeJsonResponse(
                {
                    "device_code": "apple-device-code",
                    "h_nonce": "apple-nonce",
                    "statusToken": "apple-status-token",
                }
            ),
            _FakeJsonResponse({}),
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
            CONF_DATA_SOURCE_TYPE: AUTH_PROVIDER_APPLE,
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
    assert result["step_id"] == "apple"
    assert result["errors"] == {"base": "authorization_pending"}


async def test_config_flow_success_idleon_cloud_steam(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test creating an entry from Idleon Cloud Steam OpenID auth."""
    fake_session = _FakeCloudSession(
        [
            _FakeJsonResponse({"result": "steam-custom-token"}),
            _FakeJsonResponse(
                {
                    "idToken": "firebase-id-token",
                    "refreshToken": "firebase-refresh-token",
                    "localId": "uid-steam",
                }
            ),
            _FakeJsonResponse(
                {
                    "id_token": "refresh-id-token",
                    "refresh_token": "stored-refresh-token",
                    "user_id": "uid-steam",
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
    monkeypatch.setattr(
        "custom_components.idleon.config_flow.steam_callback_url",
        lambda _hass, flow_id, state: (
            "https://ha.example.com/api/idleon/steam/auth/callback"
            f"?flow_id={flow_id}&steam_callback_state={state}"
        ),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_DATA_SOURCE_TYPE: AUTH_PROVIDER_STEAM,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "steam"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 3600},
    )

    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["step_id"] == "steam"
    steam_login_url = result["url"]
    assert "steamcommunity.com/openid/login" in steam_login_url
    steam_login_params = parse_qs(urlsplit(steam_login_url).query)
    assert steam_login_params["openid.ns"] == ["http://specs.openid.net/auth/2.0"]
    return_to = steam_login_params["openid.return_to"][0]
    assert return_to.startswith(
        "https://ha.example.com/api/idleon/steam/auth/callback?"
    )
    return_to_params = parse_qs(urlsplit(return_to).query)
    assert return_to_params["flow_id"] == [result["flow_id"]]
    assert return_to_params[CONF_STEAM_CALLBACK_STATE]
    assert steam_login_params["openid.realm"] == ["https://ha.example.com/"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_STEAM_CALLBACK_STATE: return_to_params[CONF_STEAM_CALLBACK_STATE][0],
            CONF_STEAM_OPENID_RESPONSE_URL: _steam_openid_response_url(return_to),
        },
    )

    assert result["type"] is FlowResultType.EXTERNAL_STEP_DONE
    assert result["step_id"] == "steam_finish"

    result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Idleon Cloud"
    assert result["data"][CONF_DATA_SOURCE_TYPE] == DATA_SOURCE_IDLEON_CLOUD
    assert result["data"][CONF_AUTH_PROVIDER] == AUTH_PROVIDER_STEAM
    assert result["data"][CONF_IDLEON_USER_ID] == "uid-steam"
    assert result["data"][CONF_IDLEON_REFRESH_TOKEN] == "firebase-refresh-token"
    assert CONF_STEAM_OPENID_RESPONSE_URL not in result["data"]
    assert "cloudfunctions.net/asil" in fake_session.requests[0][1]
    post_payload = fake_session.requests[0][2]["json"]
    assert isinstance(post_payload, dict)
    assert post_payload["data"] == {
        "claimedId": "123",
        "nonce": "nonce",
        "assocHandle": "assoc",
        "sig": "signature",
        "signed": "signed,fields",
    }
    assert "accounts:signInWithCustomToken" in fake_session.requests[1][1]
    custom_payload = fake_session.requests[1][2]["json"]
    assert isinstance(custom_payload, dict)
    assert custom_payload["token"] == "steam-custom-token"


async def test_config_flow_idleon_cloud_steam_auth_failure(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Test invalid Steam OpenID response URL returns a clean error."""
    fake_session = _FakeCloudSession([])
    monkeypatch.setattr(
        "custom_components.idleon.idleon_data.cloud.async_get_clientsession",
        lambda _hass: fake_session,
    )
    monkeypatch.setattr(
        "custom_components.idleon.config_flow.steam_callback_url",
        lambda _hass, flow_id, state: (
            "https://ha.example.com/api/idleon/steam/auth/callback"
            f"?flow_id={flow_id}&steam_callback_state={state}"
        ),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_DATA_SOURCE_TYPE: AUTH_PROVIDER_STEAM,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 3600},
    )

    assert result["type"] is FlowResultType.EXTERNAL_STEP

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_STEAM_CALLBACK_STATE: "wrong-state",
            CONF_STEAM_OPENID_RESPONSE_URL: "https://example.com/not-steam",
        },
    )

    assert result["type"] is FlowResultType.EXTERNAL_STEP_DONE
    assert result["step_id"] == "steam_auth_failed"

    result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "auth_failed"
    assert fake_session.requests == []


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
