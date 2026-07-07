"""Idleon cloud data access via Firebase REST APIs."""

from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

from aiohttp import ClientError, ClientResponseError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import AUTH_PROVIDER_EMAIL, AUTH_PROVIDER_GOOGLE, AUTH_PROVIDER_STEAM
from ..models import IdleonDataSource
from .exceptions import (
    IdleonAuthFailed,
    IdleonAuthPending,
    IdleonCannotConnect,
    IdleonInvalidSchema,
)

FIREBASE_API_KEY = "AIzaSyAU62kOE6xhSrFqoXQPv6_WHxYilmoUxDk"
FIREBASE_PROJECT_ID = "idlemmo"
IDENTITY_TOOLKIT_BASE = "https://identitytoolkit.googleapis.com/v1"
SECURE_TOKEN_BASE = "https://securetoken.googleapis.com/v1"
REALTIME_DATABASE_BASE = "https://idlemmo.firebaseio.com"
FIRESTORE_BASE = (
    "https://firestore.googleapis.com/v1/projects/"
    f"{FIREBASE_PROJECT_ID}/databases/(default)/documents"
)
GOOGLE_DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CLIENT_ID = "267901585099-u6fjd75v6k9gefq7bcokcndv99riir5j"
GOOGLE_CLIENT_SECRET = "HzoZF-UKUNfFwBuz4vafwsaR"
GOOGLE_AUTH_PROVIDER_ID = "google.com"
GOOGLE_OAUTH_SCOPE = "email profile"
FIREBASE_AUTH_REQUEST_URI = "http://localhost"
APPLE_AUTH_PROVIDER_ID = "apple.com"
APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_CLIENT_ID = "com.lavaflame.idleon.service.signin"
APPLE_REDIRECT_URI = "https://us-central1-idlemmo.cloudfunctions.net/xapsi"
APPLE_TOKEN_START_URL = "https://us-central1-idlemmo.cloudfunctions.net/tspa"
APPLE_TOKEN_STATUS_URL = "https://us-central1-idlemmo.cloudfunctions.net/capsc"
STEAM_AUTH_PROVIDER_ID = "steam.com"
STEAM_OPENID_LOGIN_URL = "https://steamcommunity.com/openid/login"
STEAM_OPENID_NS = "http://specs.openid.net/auth/2.0"
STEAM_OPENID_IDENTIFIER_SELECT = f"{STEAM_OPENID_NS}/identifier_select"
STEAM_CUSTOM_TOKEN_URL = "https://us-central1-idlemmo.cloudfunctions.net/asil"

_LOGGER = getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IdleonCloudCredentials:
    """Authenticated Idleon cloud credential material."""

    id_token: str
    refresh_token: str
    user_id: str
    email: str | None = None


@dataclass(frozen=True, slots=True)
class IdleonGoogleDeviceCode:
    """Google OAuth device-code flow details."""

    device_code: str
    user_code: str
    verification_url: str
    verification_url_complete: str | None
    expires_in: int
    interval: int


@dataclass(frozen=True, slots=True)
class IdleonAppleAuthSession:
    """Apple authorization session details returned by Idleon."""

    device_code: str
    nonce: str
    status_token: str


class IdleonCloudClient:
    """Read-only Idleon cloud client."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the cloud client."""
        self._session = async_get_clientsession(hass)

    async def async_sign_in_email_password(
        self,
        email: str,
        password: str,
    ) -> IdleonCloudCredentials:
        """Sign in with Firebase email/password credentials."""
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        data = await self._async_post_json(
            f"{IDENTITY_TOOLKIT_BASE}/accounts:signInWithPassword"
            f"?key={FIREBASE_API_KEY}",
            payload,
            auth_error_message="Idleon email/password authentication failed",
        )
        return _credentials_from_auth_response(data, fallback_email=email)

    async def async_start_google_device_flow(self) -> IdleonGoogleDeviceCode:
        """Start a Google OAuth device authorization flow."""
        data = await self._async_post_form(
            GOOGLE_DEVICE_CODE_URL,
            {
                "client_id": GOOGLE_CLIENT_ID,
                "scope": GOOGLE_OAUTH_SCOPE,
            },
            auth_error_message="Google device authorization could not be started",
        )
        return _google_device_code_from_response(data)

    async def async_sign_in_google_device_code(
        self,
        device_code: str,
    ) -> IdleonCloudCredentials:
        """Poll Google OAuth and exchange the result for Firebase credentials."""
        google_token = await self._async_poll_google_device_token(device_code)
        id_token = google_token.get("id_token")
        if not isinstance(id_token, str) or not id_token:
            raise IdleonAuthFailed("Google authorization returned no ID token")
        return await self.async_sign_in_google_id_token(id_token)

    async def async_sign_in_google_id_token(
        self,
        id_token: str,
    ) -> IdleonCloudCredentials:
        """Sign in to Firebase using a Google OAuth ID token."""
        payload = {
            "postBody": urlencode(
                {
                    "id_token": id_token,
                    "providerId": GOOGLE_AUTH_PROVIDER_ID,
                }
            ),
            "requestUri": FIREBASE_AUTH_REQUEST_URI,
            "returnIdpCredential": True,
            "returnSecureToken": True,
        }
        data = await self._async_post_json(
            f"{IDENTITY_TOOLKIT_BASE}/accounts:signInWithIdp?key={FIREBASE_API_KEY}",
            payload,
            auth_error_message="Google authentication failed",
        )
        return _credentials_from_auth_response(data)

    async def async_start_apple_auth_session(self) -> IdleonAppleAuthSession:
        """Start an Idleon Apple authorization session."""
        _LOGGER.debug("Starting Idleon Apple authorization session")
        data = await self._async_post_form(
            APPLE_TOKEN_START_URL,
            {},
            auth_error_message="Apple authorization could not be started",
        )
        return _apple_auth_session_from_response(data)

    async def async_sign_in_apple_auth_session(
        self,
        auth_session: IdleonAppleAuthSession,
    ) -> IdleonCloudCredentials:
        """Poll Idleon's Apple auth status and exchange it for Firebase credentials."""
        _LOGGER.debug("Checking Idleon Apple authorization status")
        apple_token = await self.async_get_apple_id_token(auth_session)
        _LOGGER.debug("Idleon Apple authorization completed; signing in to Firebase")
        return await self.async_sign_in_apple_id_token(
            apple_token["id_token"],
            nonce=apple_token["nonce"],
        )

    async def async_get_apple_id_token(
        self,
        auth_session: IdleonAppleAuthSession,
    ) -> dict[str, str]:
        """Return an Apple identity token from a completed Idleon Apple session."""
        data = await self._async_post_form(
            APPLE_TOKEN_STATUS_URL,
            {
                "device_code": auth_session.device_code,
                "statusToken": auth_session.status_token,
            },
            auth_error_message="Apple authorization failed",
        )
        return _apple_token_from_status_response(data)

    async def async_sign_in_apple_id_token(
        self,
        id_token: str,
        *,
        nonce: str,
    ) -> IdleonCloudCredentials:
        """Sign in to Firebase using an Apple identity token."""
        payload = {
            "postBody": urlencode(
                {
                    "id_token": id_token,
                    "nonce": nonce,
                    "providerId": APPLE_AUTH_PROVIDER_ID,
                }
            ),
            "requestUri": FIREBASE_AUTH_REQUEST_URI,
            "returnIdpCredential": True,
            "returnSecureToken": True,
        }
        data = await self._async_post_json(
            f"{IDENTITY_TOOLKIT_BASE}/accounts:signInWithIdp?key={FIREBASE_API_KEY}",
            payload,
            auth_error_message="Apple authentication failed",
        )
        return _credentials_from_auth_response(data)

    async def async_sign_in_steam_openid_response(
        self,
        response_url: str,
    ) -> IdleonCloudCredentials:
        """Sign in to Firebase using a Steam OpenID response URL."""
        _LOGGER.debug("Exchanging Steam OpenID response for Idleon custom token")
        custom_token = await self.async_get_steam_custom_token(response_url)
        _LOGGER.debug("Steam custom token received; signing in to Firebase")
        return await self.async_sign_in_custom_token(custom_token)

    async def async_get_steam_custom_token(self, response_url: str) -> str:
        """Exchange a Steam OpenID response for an Idleon Firebase custom token."""
        data = await self._async_post_json(
            STEAM_CUSTOM_TOKEN_URL,
            {"data": _steam_custom_token_request(response_url)},
            auth_error_message="Steam custom-token exchange failed",
        )
        return _custom_token_from_steam_response(data)

    async def async_sign_in_custom_token(
        self,
        custom_token: str,
    ) -> IdleonCloudCredentials:
        """Sign in to Firebase using a custom auth token."""
        payload = {
            "token": custom_token,
            "returnSecureToken": True,
        }
        data = await self._async_post_json(
            f"{IDENTITY_TOOLKIT_BASE}/accounts:signInWithCustomToken"
            f"?key={FIREBASE_API_KEY}",
            payload,
            auth_error_message="Steam Firebase custom-token sign-in failed",
        )
        return _credentials_from_auth_response(data)

    async def async_refresh_credentials(
        self,
        refresh_token: str,
    ) -> IdleonCloudCredentials:
        """Refresh an id token from a stored Firebase refresh token."""
        data = await self._async_post_form(
            f"{SECURE_TOKEN_BASE}/token?key={FIREBASE_API_KEY}",
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth_error_message="Idleon cloud token refresh failed",
        )
        return _credentials_from_refresh_response(data)

    async def async_get_cloud_save(
        self,
        data_source: IdleonDataSource,
    ) -> dict[str, Any]:
        """Return raw Idleon cloud save data in parser-compatible shape."""
        credentials = await self._async_credentials_from_source(data_source)
        character_names = await self._async_get_character_names(credentials)
        save_data = await self._async_get_save_data(credentials)
        companion_data = await self._async_get_companion_data(credentials)
        return {
            "charNameData": character_names,
            "saveData": save_data,
            "companion": companion_data,
        }

    async def _async_credentials_from_source(
        self,
        data_source: IdleonDataSource,
    ) -> IdleonCloudCredentials:
        """Return credentials from password input or a stored refresh token."""
        if (
            data_source.auth_provider == AUTH_PROVIDER_EMAIL
            and data_source.idleon_email
            and data_source.idleon_password
        ):
            return await self.async_sign_in_email_password(
                data_source.idleon_email,
                data_source.idleon_password,
            )
        if (
            data_source.auth_provider == AUTH_PROVIDER_GOOGLE
            and data_source.idleon_password
        ):
            return await self.async_sign_in_google_id_token(data_source.idleon_password)
        if (
            data_source.auth_provider == AUTH_PROVIDER_STEAM
            and data_source.steam_openid_response_url
        ):
            return await self.async_sign_in_steam_openid_response(
                data_source.steam_openid_response_url
            )
        if data_source.idleon_refresh_token:
            return await self.async_refresh_credentials(
                data_source.idleon_refresh_token
            )
        raise IdleonAuthFailed("Idleon cloud credentials are required")

    async def _async_get_character_names(
        self,
        credentials: IdleonCloudCredentials,
    ) -> Any:
        """Fetch the account character name list."""
        user_id = quote(credentials.user_id, safe="")
        data = await self._async_get_json(
            f"{REALTIME_DATABASE_BASE}/_uid/{user_id}.json"
            f"?auth={quote(credentials.id_token, safe='')}",
            credentials,
        )
        if not isinstance(data, list):
            raise IdleonInvalidSchema("Idleon cloud account has no character list")
        return data

    async def _async_get_save_data(
        self,
        credentials: IdleonCloudCredentials,
    ) -> dict[str, Any]:
        """Fetch the raw cloud save document."""
        user_id = quote(credentials.user_id, safe="")
        document = await self._async_get_json(
            f"{FIRESTORE_BASE}/_data/{user_id}",
            credentials,
        )
        if not isinstance(document, dict):
            raise IdleonInvalidSchema("Idleon cloud save document is not an object")
        fields = document.get("fields")
        if not isinstance(fields, dict):
            raise IdleonInvalidSchema("Idleon cloud save document has no fields")
        decoded = _decode_firestore_fields(fields)
        if not isinstance(decoded, dict):
            raise IdleonInvalidSchema("Idleon cloud save data is not an object")
        return decoded

    async def _async_get_companion_data(
        self,
        credentials: IdleonCloudCredentials,
    ) -> dict[str, Any]:
        """Fetch optional cloud companion data."""
        user_id = quote(credentials.user_id, safe="")
        try:
            data = await self._async_get_json(
                f"{REALTIME_DATABASE_BASE}/_comp/{user_id}.json"
                f"?auth={quote(credentials.id_token, safe='')}",
                credentials,
            )
        except IdleonAuthFailed, IdleonCannotConnect:
            _LOGGER.debug("Idleon cloud companion data could not be fetched")
            return {}
        if data is None:
            return {}
        if not isinstance(data, dict):
            _LOGGER.debug("Idleon cloud companion data was not an object")
            return {}
        return data

    async def _async_get_json(
        self,
        url: str,
        credentials: IdleonCloudCredentials,
    ) -> Any:
        """GET a JSON document from an authenticated Firebase endpoint."""
        try:
            async with self._session.get(
                url,
                headers={"Authorization": f"Bearer {credentials.id_token}"},
                timeout=ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                return await response.json()
        except ClientResponseError as err:
            if err.status in {401, 403}:
                raise IdleonAuthFailed("Idleon cloud authentication failed") from err
            raise IdleonCannotConnect("Idleon cloud data could not be fetched") from err
        except (ClientError, TimeoutError) as err:
            raise IdleonCannotConnect("Idleon cloud data could not be fetched") from err

    async def _async_post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        auth_error_message: str,
    ) -> Any:
        """POST JSON to a Firebase endpoint."""
        try:
            async with self._session.post(
                url,
                json=payload,
                timeout=ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                return await response.json()
        except ClientResponseError as err:
            if err.status in {400, 401, 403}:
                raise IdleonAuthFailed(
                    f"{auth_error_message} with status {err.status}"
                ) from err
            raise IdleonCannotConnect("Idleon cloud authentication failed") from err
        except (ClientError, TimeoutError) as err:
            raise IdleonCannotConnect("Idleon cloud authentication failed") from err

    async def _async_post_form(
        self,
        url: str,
        payload: dict[str, str],
        *,
        auth_error_message: str,
    ) -> Any:
        """POST form data to a Firebase endpoint."""
        try:
            async with self._session.post(
                url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                return await response.json()
        except ClientResponseError as err:
            if err.status in {400, 401, 403}:
                raise IdleonAuthFailed(auth_error_message) from err
            raise IdleonCannotConnect("Idleon cloud token refresh failed") from err
        except (ClientError, TimeoutError) as err:
            raise IdleonCannotConnect("Idleon cloud token refresh failed") from err

    async def _async_poll_google_device_token(self, device_code: str) -> dict[str, Any]:
        """Poll Google OAuth for a completed device authorization."""
        try:
            async with self._session.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=ClientTimeout(total=30),
            ) as response:
                data = await response.json()
                if response.status == 200:
                    if not isinstance(data, dict):
                        raise IdleonAuthFailed(
                            "Google authorization returned invalid data"
                        )
                    return data
                if isinstance(data, dict) and data.get("error") in {
                    "authorization_pending",
                    "slow_down",
                }:
                    raise IdleonAuthPending("Google authorization is not complete yet")
                response.raise_for_status()
        except IdleonAuthPending:
            raise
        except ClientResponseError as err:
            if err.status in {400, 401, 403}:
                raise IdleonAuthFailed("Google authorization failed") from err
            raise IdleonCannotConnect(
                "Google authorization could not be checked"
            ) from err
        except (ClientError, TimeoutError) as err:
            raise IdleonCannotConnect(
                "Google authorization could not be checked"
            ) from err

        raise IdleonAuthFailed("Google authorization failed")


def _credentials_from_auth_response(
    data: Any,
    *,
    fallback_email: str | None = None,
) -> IdleonCloudCredentials:
    """Return normalized credentials from an Identity Toolkit auth response."""
    if not isinstance(data, dict):
        raise IdleonAuthFailed("Idleon cloud authentication returned invalid data")
    id_token = data.get("idToken")
    refresh_token = data.get("refreshToken")
    user_id = data.get("localId")
    if not all(
        isinstance(value, str) and value for value in (id_token, refresh_token, user_id)
    ):
        raise IdleonAuthFailed("Idleon cloud authentication returned incomplete data")
    email = data.get("email")
    return IdleonCloudCredentials(
        id_token=id_token,
        refresh_token=refresh_token,
        user_id=user_id,
        email=email if isinstance(email, str) else fallback_email,
    )


def _google_device_code_from_response(data: Any) -> IdleonGoogleDeviceCode:
    """Return normalized Google OAuth device-code details."""
    if not isinstance(data, dict):
        raise IdleonAuthFailed("Google device authorization returned invalid data")
    device_code = data.get("device_code")
    user_code = data.get("user_code")
    verification_url = data.get("verification_url") or data.get("verification_uri")
    verification_url_complete = data.get("verification_url_complete")
    expires_in = _coerce_int(data.get("expires_in"), default=1800)
    interval = _coerce_int(data.get("interval"), default=5)
    if not all(
        isinstance(value, str) and value
        for value in (device_code, user_code, verification_url)
    ):
        raise IdleonAuthFailed("Google device authorization returned incomplete data")
    return IdleonGoogleDeviceCode(
        device_code=device_code,
        user_code=user_code,
        verification_url=verification_url,
        verification_url_complete=(
            verification_url_complete
            if isinstance(verification_url_complete, str)
            else None
        ),
        expires_in=expires_in,
        interval=interval,
    )


def _apple_auth_session_from_response(data: Any) -> IdleonAppleAuthSession:
    """Return normalized Idleon Apple auth session details."""
    if not isinstance(data, dict):
        raise IdleonAuthFailed("Apple authorization returned invalid data")
    device_code = data.get("device_code")
    nonce = data.get("h_nonce")
    status_token = data.get("statusToken")
    if not all(
        isinstance(value, str) and value for value in (device_code, nonce, status_token)
    ):
        raise IdleonAuthFailed("Apple authorization returned incomplete data")
    return IdleonAppleAuthSession(
        device_code=device_code,
        nonce=nonce,
        status_token=status_token,
    )


def _apple_token_from_status_response(data: Any) -> dict[str, str]:
    """Return Apple identity token details from Idleon's status response."""
    if not isinstance(data, dict):
        raise IdleonAuthFailed("Apple authorization returned invalid data")
    id_token = data.get("id_token")
    nonce = data.get("nonce")
    if not isinstance(id_token, str) or not id_token:
        raise IdleonAuthPending("Apple authorization is not complete yet")
    if not isinstance(nonce, str):
        raise IdleonAuthFailed("Apple authorization returned incomplete data")
    return {"id_token": id_token, "nonce": nonce}


def apple_authorize_url(auth_session: IdleonAppleAuthSession) -> str:
    """Return the Apple Sign In URL for an Idleon Apple auth session."""
    return (
        APPLE_AUTH_URL
        + "?"
        + urlencode(
            {
                "client_id": APPLE_CLIENT_ID,
                "nonce": auth_session.nonce,
                "redirect_uri": APPLE_REDIRECT_URI,
                "response_mode": "form_post",
                "response_type": "code id_token",
                "scope": "email",
                "code": auth_session.device_code,
                "state": auth_session.status_token,
            }
        )
    )


def steam_openid_login_url(return_to: str, realm: str) -> str:
    """Return a Steam OpenID login URL for a Home Assistant callback."""
    return (
        STEAM_OPENID_LOGIN_URL
        + "?"
        + urlencode(
            {
                "openid.ns": STEAM_OPENID_NS,
                "openid.mode": "checkid_setup",
                "openid.return_to": return_to,
                "openid.realm": realm,
                "openid.identity": STEAM_OPENID_IDENTIFIER_SELECT,
                "openid.claimed_id": STEAM_OPENID_IDENTIFIER_SELECT,
            }
        )
    )


def _steam_openid_request_uri(response_url: str) -> str:
    """Return the request URI Firebase should validate for Steam OpenID."""
    params = _steam_openid_response_params(response_url)
    return params.get("openid.return_to") or FIREBASE_AUTH_REQUEST_URI


def _steam_openid_response_params(response_url: str) -> dict[str, str]:
    """Return validated Steam OpenID response parameters."""
    parsed = urlsplit(response_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    required_params = (
        "openid.claimed_id",
        "openid.identity",
        "openid.mode",
        "openid.sig",
        "openid.signed",
    )
    if not params or not all(params.get(key) for key in required_params):
        raise IdleonAuthFailed("Steam OpenID response URL is incomplete")
    if params.get("openid.mode") != "id_res":
        raise IdleonAuthFailed("Steam OpenID response was not authorized")
    return params


def _steam_custom_token_request(response_url: str) -> dict[str, str]:
    """Return the Idleon cloud function payload for a Steam OpenID response."""
    params = _steam_openid_response_params(response_url)
    claimed_id = params.get("openid.claimed_id", "")
    steam_id = claimed_id.rsplit("/", maxsplit=1)[-1]
    if not steam_id.isdigit():
        raise IdleonAuthFailed("Steam OpenID response has no Steam ID")
    return {
        "claimedId": steam_id,
        "nonce": params["openid.response_nonce"],
        "assocHandle": params["openid.assoc_handle"],
        "sig": params["openid.sig"],
        "signed": params["openid.signed"],
    }


def _custom_token_from_steam_response(data: Any) -> str:
    """Return a Firebase custom token from Idleon's Steam auth response."""
    if not isinstance(data, dict):
        raise IdleonAuthFailed("Steam authentication returned invalid data")
    custom_token = data.get("result")
    if not isinstance(custom_token, str) or not custom_token:
        raise IdleonAuthFailed("Steam authentication returned no token")
    return custom_token


def _coerce_int(value: Any, *, default: int) -> int:
    """Return an integer from provider data."""
    try:
        return int(value)
    except TypeError, ValueError:
        return default


def _credentials_from_refresh_response(data: Any) -> IdleonCloudCredentials:
    """Return normalized credentials from a Secure Token refresh response."""
    if not isinstance(data, dict):
        raise IdleonAuthFailed("Idleon cloud token refresh returned invalid data")
    id_token = data.get("id_token")
    refresh_token = data.get("refresh_token")
    user_id = data.get("user_id")
    if not all(
        isinstance(value, str) and value for value in (id_token, refresh_token, user_id)
    ):
        raise IdleonAuthFailed("Idleon cloud token refresh returned incomplete data")
    return IdleonCloudCredentials(
        id_token=id_token,
        refresh_token=refresh_token,
        user_id=user_id,
    )


def _decode_firestore_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Decode a Firestore REST fields mapping."""
    return {key: _decode_firestore_value(value) for key, value in fields.items()}


def _decode_firestore_value(value: Any) -> Any:
    """Decode a Firestore REST value into Python primitives."""
    if not isinstance(value, dict):
        return value
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "timestampValue" in value:
        return value["timestampValue"]
    if "stringValue" in value:
        return value["stringValue"]
    if "bytesValue" in value:
        return value["bytesValue"]
    if "referenceValue" in value:
        return value["referenceValue"]
    if "geoPointValue" in value:
        return value["geoPointValue"]
    if "arrayValue" in value:
        array_value = value["arrayValue"]
        if not isinstance(array_value, dict):
            return []
        values = array_value.get("values", [])
        if not isinstance(values, list):
            return []
        return [_decode_firestore_value(item) for item in values]
    if "mapValue" in value:
        map_value = value["mapValue"]
        if not isinstance(map_value, dict):
            return {}
        fields = map_value.get("fields", {})
        if not isinstance(fields, dict):
            return {}
        return _decode_firestore_fields(fields)
    return value
