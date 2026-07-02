"""Idleon cloud data access via Firebase REST APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from aiohttp import ClientError, ClientResponseError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import AUTH_PROVIDER_EMAIL
from ..models import IdleonDataSource
from .exceptions import IdleonAuthFailed, IdleonCannotConnect, IdleonInvalidSchema

FIREBASE_API_KEY = "AIzaSyAU62kOE6xhSrFqoXQPv6_WHxYilmoUxDk"
FIREBASE_PROJECT_ID = "idlemmo"
IDENTITY_TOOLKIT_BASE = "https://identitytoolkit.googleapis.com/v1"
SECURE_TOKEN_BASE = "https://securetoken.googleapis.com/v1"
REALTIME_DATABASE_BASE = "https://idlemmo.firebaseio.com"
FIRESTORE_BASE = (
    "https://firestore.googleapis.com/v1/projects/"
    f"{FIREBASE_PROJECT_ID}/databases/(default)/documents"
)


@dataclass(frozen=True, slots=True)
class IdleonCloudCredentials:
    """Authenticated Idleon cloud credential material."""

    id_token: str
    refresh_token: str
    user_id: str
    email: str | None = None


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
        return {
            "charNameData": character_names,
            "saveData": save_data,
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
                raise IdleonAuthFailed(auth_error_message) from err
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
