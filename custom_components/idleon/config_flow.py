"""Config flow for HA Idleon."""

from __future__ import annotations

import secrets
from contextlib import suppress
from logging import getLogger
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    AUTH_PROVIDER_APPLE,
    AUTH_PROVIDER_EMAIL,
    AUTH_PROVIDER_GOOGLE,
    AUTH_PROVIDER_STEAM,
    AUTH_PROVIDERS,
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
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .idleon_data import (
    IdleonAuthFailed,
    IdleonAuthPending,
    IdleonCannotConnect,
    IdleonClient,
    IdleonInvalidJson,
    IdleonInvalidSchema,
    parse_idleon_account,
)
from .idleon_data.cloud import (
    IdleonCloudClient,
    IdleonCloudCredentials,
    IdleonGoogleDeviceCode,
    steam_openid_login_url,
)
from .models import IdleonDataSource
from .steam_auth import (
    NoURLAvailableError,
    async_register_steam_auth_callback_view,
    steam_callback_url,
)

_LOGGER = getLogger(__name__)


class IdleonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle an Idleon config flow."""

    VERSION = 1
    _data_source_type: str | None = None
    _auth_provider: str | None = None
    _cloud_base_input: dict[str, Any] | None = None
    _pending_google_input: dict[str, Any] | None = None
    _pending_steam_input: dict[str, Any] | None = None
    _steam_openid_response_url: str | None = None
    _steam_state: str | None = None
    _steam_auth_failed_reason: str = "auth_failed"
    _google_device_code: IdleonGoogleDeviceCode | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Select the data source type."""
        if user_input is not None:
            self._data_source_type = _stored_data_source_type(
                user_input[CONF_DATA_SOURCE_TYPE]
            )
            self._auth_provider = _auth_provider_from_source_type(
                user_input[CONF_DATA_SOURCE_TYPE]
            )
            if self._auth_provider == AUTH_PROVIDER_STEAM:
                return await self.async_step_steam()
            return await self.async_step_source()

        return self.async_show_form(
            step_id="user",
            data_schema=_source_type_schema(),
        )

    async def async_step_auth_provider(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Select the Idleon cloud authentication provider."""
        if user_input is not None:
            self._auth_provider = user_input[CONF_AUTH_PROVIDER]
            self._cloud_base_input = _normalize_cloud_base_input(user_input)
            if self._auth_provider == AUTH_PROVIDER_GOOGLE:
                self._pending_google_input = self._cloud_base_input
                return await self.async_step_google()
            if self._auth_provider == AUTH_PROVIDER_STEAM:
                return await self.async_step_steam()
            return await self.async_step_source()

        return self.async_show_form(
            step_id="auth_provider",
            data_schema=_auth_provider_schema(),
        )

    async def async_step_source(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle source details and validation."""
        return await self._async_step_source_details("source", user_input)

    async def async_step_steam(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle Steam OpenID authorization."""
        errors: dict[str, str] = {}

        if user_input is not None and CONF_STEAM_OPENID_RESPONSE_URL in user_input:
            if user_input.get(CONF_STEAM_CALLBACK_STATE) != self._steam_state:
                _LOGGER.warning("Steam authorization callback state did not match")
                self._steam_auth_failed_reason = "auth_failed"
                return self.async_external_step_done(next_step_id="steam_auth_failed")
            self._steam_openid_response_url = str(
                user_input[CONF_STEAM_OPENID_RESPONSE_URL]
            )
            return self.async_external_step_done(next_step_id="steam_finish")

        if user_input is not None:
            try:
                normalized_input = _normalize_user_input(
                    self._data_source_type,
                    user_input,
                    auth_provider=self._auth_provider,
                    base_input=self._cloud_base_input,
                    require_steam_response=False,
                )
                self._pending_steam_input = normalized_input
                self._steam_state = secrets.token_urlsafe(24)
                async_register_steam_auth_callback_view(self.hass)
                callback_url = steam_callback_url(
                    self.hass,
                    self.flow_id,
                    self._steam_state,
                )
            except NoURLAvailableError:
                errors["base"] = "no_url_available"
            except IdleonAuthFailed:
                errors["base"] = "auth_failed"
            except Exception:
                _LOGGER.exception("Unexpected error starting Steam authorization")
                errors["base"] = "unknown"
            else:
                return self.async_external_step(
                    step_id="steam",
                    url=steam_openid_login_url(
                        callback_url,
                        _steam_openid_realm(callback_url),
                    ),
                )

        return self.async_show_form(
            step_id="steam",
            data_schema=_source_details_schema(
                self._data_source_type,
                auth_provider=self._auth_provider,
                steam_external=True,
            ),
            errors=errors,
        )

    async def async_step_steam_auth_failed(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Abort after a failed Steam external authorization."""
        return self.async_abort(reason=self._steam_auth_failed_reason)

    async def async_step_steam_finish(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Create an entry from a completed Steam authorization."""
        if self._pending_steam_input is None or self._steam_openid_response_url is None:
            return await self.async_step_user()

        normalized_input = dict(self._pending_steam_input)
        normalized_input[CONF_STEAM_OPENID_RESPONSE_URL] = (
            self._steam_openid_response_url
        )
        try:
            normalized_input, data_source = await _async_prepare_source(
                self.hass,
                normalized_input,
            )
            await _async_validate_source(self.hass, data_source)
        except IdleonAuthFailed as err:
            _LOGGER.warning("Steam authorization failed: %s", err)
            return self.async_abort(reason="auth_failed")
        except IdleonCannotConnect as err:
            _LOGGER.warning("Steam authorization data could not be fetched: %s", err)
            return self.async_abort(reason="cannot_connect")
        except IdleonInvalidJson as err:
            _LOGGER.warning("Steam authorization returned invalid JSON: %s", err)
            return self.async_abort(reason="invalid_json")
        except IdleonInvalidSchema as err:
            _LOGGER.warning("Steam authorization returned invalid schema: %s", err)
            return self.async_abort(reason="invalid_schema")
        except Exception:
            _LOGGER.exception("Unexpected error validating Steam authorization")
            return self.async_abort(reason="unknown")

        await self.async_set_unique_id(_source_unique_id(data_source))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=_entry_title(data_source),
            data=normalized_input,
        )

    async def _async_step_source_details(
        self,
        step_id: str,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle source details and validation for a source-like step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized_input = _normalize_user_input(
                    self._data_source_type,
                    user_input,
                    auth_provider=self._auth_provider,
                    base_input=self._cloud_base_input,
                )
                if _is_google_cloud_input(normalized_input):
                    self._pending_google_input = normalized_input
                    return await self.async_step_google()
                normalized_input, data_source = await _async_prepare_source(
                    self.hass,
                    normalized_input,
                )
                await _async_validate_source(self.hass, data_source)
            except IdleonAuthFailed:
                errors["base"] = "auth_failed"
            except IdleonCannotConnect:
                errors["base"] = "cannot_connect"
            except IdleonInvalidJson:
                errors["base"] = "invalid_json"
            except IdleonInvalidSchema:
                errors["base"] = "invalid_schema"
            except Exception:
                _LOGGER.exception("Unexpected error validating Idleon data source")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(_source_unique_id(data_source))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_entry_title(data_source),
                    data=normalized_input,
                )

        return self.async_show_form(
            step_id=step_id,
            data_schema=_source_details_schema(
                self._data_source_type,
                auth_provider=self._auth_provider,
            ),
            description_placeholders=_source_description_placeholders(
                self._auth_provider
            ),
            errors=errors,
        )

    async def async_step_google(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle Google device-code authorization."""
        errors: dict[str, str] = {}

        if self._pending_google_input is None:
            return await self.async_step_user()

        if self._google_device_code is None:
            try:
                self._google_device_code = await IdleonCloudClient(
                    self.hass
                ).async_start_google_device_flow()
            except IdleonCannotConnect:
                errors["base"] = "cannot_connect"
            except IdleonAuthFailed:
                errors["base"] = "auth_failed"
            except Exception:
                _LOGGER.exception("Unexpected error starting Google authorization")
                errors["base"] = "unknown"

        if user_input is not None and self._google_device_code is not None:
            try:
                normalized_input, data_source = await _async_prepare_google_source(
                    self.hass,
                    self._pending_google_input,
                    self._google_device_code,
                )
                await _async_validate_source(self.hass, data_source)
            except IdleonAuthPending:
                errors["base"] = "authorization_pending"
            except IdleonAuthFailed:
                errors["base"] = "auth_failed"
            except IdleonCannotConnect:
                errors["base"] = "cannot_connect"
            except IdleonInvalidJson:
                errors["base"] = "invalid_json"
            except IdleonInvalidSchema:
                errors["base"] = "invalid_schema"
            except Exception:
                _LOGGER.exception("Unexpected error validating Google authorization")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(_source_unique_id(data_source))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_entry_title(data_source),
                    data=normalized_input,
                )

        return self.async_show_form(
            step_id="google",
            data_schema=vol.Schema({}),
            description_placeholders=_google_description_placeholders(
                self._google_device_code
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return IdleonOptionsFlow(config_entry)


class IdleonOptionsFlow(OptionsFlow):
    """Handle Idleon options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Update refresh options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: _normalize_scan_interval(
                        user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    )
                },
            )

        current_data = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current_data),
        )


async def _async_validate_source(
    hass: HomeAssistant,
    data_source: IdleonDataSource,
) -> None:
    """Fetch and parse a source before storing the config entry."""
    raw_data = await IdleonClient(hass, data_source).async_get_data()
    parse_idleon_account(raw_data)


async def _async_prepare_source(
    hass: HomeAssistant,
    user_input: dict[str, Any],
) -> tuple[dict[str, Any], IdleonDataSource]:
    """Prepare entry data for validation and storage."""
    data_source = _data_source_from_input(user_input)
    if data_source.source_type != DATA_SOURCE_IDLEON_CLOUD:
        return user_input, data_source

    if data_source.auth_provider == AUTH_PROVIDER_GOOGLE:
        raise IdleonAuthFailed("Google authorization is required")
    if data_source.auth_provider == AUTH_PROVIDER_EMAIL:
        if not data_source.idleon_email:
            raise IdleonAuthFailed("Idleon email is required")
        if not data_source.idleon_password:
            if data_source.idleon_refresh_token:
                return user_input, data_source
            raise IdleonAuthFailed("Idleon password is required")
        credentials = await IdleonCloudClient(hass).async_sign_in_email_password(
            data_source.idleon_email,
            data_source.idleon_password,
        )
    elif data_source.auth_provider == AUTH_PROVIDER_STEAM:
        if not data_source.steam_openid_response_url:
            if data_source.idleon_refresh_token:
                return user_input, data_source
            raise IdleonAuthFailed("Steam OpenID response URL is required")
        credentials = await IdleonCloudClient(hass).async_sign_in_steam_openid_response(
            data_source.steam_openid_response_url
        )
    else:
        raise IdleonAuthFailed("Unsupported Idleon cloud login provider")
    prepared = _entry_data_from_cloud_credentials(user_input, credentials)
    return prepared, _data_source_from_input(prepared)


async def _async_prepare_google_source(
    hass: HomeAssistant,
    user_input: dict[str, Any],
    device_code: IdleonGoogleDeviceCode,
) -> tuple[dict[str, Any], IdleonDataSource]:
    """Exchange a completed Google device flow for storable source data."""
    credentials = await IdleonCloudClient(hass).async_sign_in_google_device_code(
        device_code.device_code
    )
    prepared = _entry_data_from_cloud_credentials(user_input, credentials)
    return prepared, _data_source_from_input(prepared)


def _entry_data_from_cloud_credentials(
    user_input: dict[str, Any],
    credentials: IdleonCloudCredentials,
) -> dict[str, Any]:
    """Return storable cloud source data without the one-time password."""
    prepared = dict(user_input)
    prepared.pop(CONF_IDLEON_PASSWORD, None)
    prepared.pop(CONF_STEAM_OPENID_RESPONSE_URL, None)
    prepared[CONF_IDLEON_USER_ID] = credentials.user_id
    prepared[CONF_IDLEON_REFRESH_TOKEN] = credentials.refresh_token
    if credentials.email:
        prepared[CONF_IDLEON_EMAIL] = credentials.email
    return prepared


def _source_type_schema(default: str = AUTH_PROVIDER_GOOGLE) -> vol.Schema:
    """Return the source type selection schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_DATA_SOURCE_TYPE,
                default=default,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {"value": DATA_SOURCE_LOCAL_FILE, "label": "Local JSON file"},
                        {"value": AUTH_PROVIDER_GOOGLE, "label": "Google"},
                        {"value": AUTH_PROVIDER_APPLE, "label": "Apple"},
                        {"value": AUTH_PROVIDER_EMAIL, "label": "Email"},
                        {"value": AUTH_PROVIDER_STEAM, "label": "Steam"},
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _auth_provider_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the cloud authentication provider schema."""
    defaults = defaults or {}
    scan_interval = defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    return vol.Schema(
        {
            vol.Required(
                CONF_AUTH_PROVIDER,
                default=defaults.get(CONF_AUTH_PROVIDER, AUTH_PROVIDER_GOOGLE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[AUTH_PROVIDER_GOOGLE, AUTH_PROVIDER_EMAIL],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=scan_interval,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="seconds",
                )
            ),
        }
    )


def _options_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the options schema for refresh settings."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="seconds",
                )
            ),
        }
    )


def _source_details_schema(
    data_source_type: str | None,
    defaults: dict[str, Any] | None = None,
    *,
    auth_provider: str | None = None,
    steam_external: bool = False,
) -> vol.Schema:
    """Return the source details schema."""
    defaults = defaults or {}
    scan_interval = defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    fields: dict[vol.Marker, Any] = {}

    if (
        data_source_type == DATA_SOURCE_IDLEON_CLOUD
        and auth_provider == AUTH_PROVIDER_EMAIL
    ):
        fields[
            vol.Required(
                CONF_IDLEON_EMAIL,
                default=defaults.get(CONF_IDLEON_EMAIL, ""),
            )
        ] = TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL))
        fields[vol.Required(CONF_IDLEON_PASSWORD)] = TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    elif (
        data_source_type == DATA_SOURCE_IDLEON_CLOUD
        and auth_provider == AUTH_PROVIDER_STEAM
        and not steam_external
    ):
        fields[
            vol.Required(
                CONF_STEAM_OPENID_RESPONSE_URL,
                default=defaults.get(CONF_STEAM_OPENID_RESPONSE_URL, ""),
            )
        ] = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))
    elif data_source_type == DATA_SOURCE_IDLEON_CLOUD:
        pass
    elif data_source_type == DATA_SOURCE_REMOTE_URL:
        fields[
            vol.Required(
                CONF_REMOTE_URL,
                default=defaults.get(CONF_REMOTE_URL, ""),
            )
        ] = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))
    else:
        fields[
            vol.Required(
                CONF_LOCAL_FILE_PATH,
                default=defaults.get(CONF_LOCAL_FILE_PATH, ""),
            )
        ] = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT))

    if data_source_type != DATA_SOURCE_IDLEON_CLOUD or auth_provider in AUTH_PROVIDERS:
        fields[
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=scan_interval,
            )
        ] = NumberSelector(
            NumberSelectorConfig(
                min=MIN_SCAN_INTERVAL,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="seconds",
            )
        )

    return vol.Schema(fields)


def _stored_data_source_type(source_type: str) -> str:
    """Return the stored data source type for a UI selection."""
    if source_type in AUTH_PROVIDERS:
        return DATA_SOURCE_IDLEON_CLOUD
    return source_type


def _auth_provider_from_source_type(source_type: str) -> str | None:
    """Return the cloud auth provider represented by a UI selection."""
    if source_type in AUTH_PROVIDERS:
        return source_type
    return None


def _source_type_from_entry_data(data: dict[str, Any]) -> str:
    """Return the UI source type represented by stored entry data."""
    if data.get(CONF_DATA_SOURCE_TYPE) == DATA_SOURCE_IDLEON_CLOUD:
        provider = data.get(CONF_AUTH_PROVIDER)
        if provider in AUTH_PROVIDERS:
            return provider
    return str(data.get(CONF_DATA_SOURCE_TYPE, AUTH_PROVIDER_GOOGLE))


def _normalize_user_input(
    data_source_type: str | None,
    user_input: dict[str, Any],
    *,
    auth_provider: str | None = None,
    base_input: dict[str, Any] | None = None,
    require_steam_response: bool = True,
) -> dict[str, Any]:
    """Validate conditional fields and return normalized entry data."""
    if not data_source_type:
        raise IdleonCannotConnect("Data source type is required")

    normalized: dict[str, Any] = {
        CONF_DATA_SOURCE_TYPE: data_source_type,
        CONF_SCAN_INTERVAL: _normalize_scan_interval(
            user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        ),
    }
    if base_input:
        normalized.update(base_input)

    if data_source_type == DATA_SOURCE_LOCAL_FILE:
        local_file_path = str(user_input.get(CONF_LOCAL_FILE_PATH) or "").strip()
        if not local_file_path:
            raise IdleonCannotConnect("Local file path is required")
        normalized[CONF_LOCAL_FILE_PATH] = local_file_path
    elif data_source_type == DATA_SOURCE_REMOTE_URL:
        remote_url = str(user_input.get(CONF_REMOTE_URL) or "").strip()
        if not remote_url:
            raise IdleonCannotConnect("Remote URL is required")
        normalized[CONF_REMOTE_URL] = remote_url
    elif data_source_type == DATA_SOURCE_IDLEON_CLOUD:
        provider = auth_provider or normalized.get(CONF_AUTH_PROVIDER)
        if provider == AUTH_PROVIDER_EMAIL:
            idleon_email = str(user_input.get(CONF_IDLEON_EMAIL) or "").strip()
            idleon_password = str(user_input.get(CONF_IDLEON_PASSWORD) or "")
            if not idleon_email or not idleon_password:
                raise IdleonAuthFailed("Idleon email and password are required")
            normalized[CONF_AUTH_PROVIDER] = provider
            normalized[CONF_IDLEON_EMAIL] = idleon_email
            normalized[CONF_IDLEON_PASSWORD] = idleon_password
        elif provider == AUTH_PROVIDER_GOOGLE:
            normalized[CONF_AUTH_PROVIDER] = provider
        elif provider == AUTH_PROVIDER_STEAM:
            steam_response_url = str(
                user_input.get(CONF_STEAM_OPENID_RESPONSE_URL) or ""
            ).strip()
            if require_steam_response and not steam_response_url:
                raise IdleonAuthFailed("Steam OpenID response URL is required")
            normalized[CONF_AUTH_PROVIDER] = provider
            if steam_response_url:
                normalized[CONF_STEAM_OPENID_RESPONSE_URL] = steam_response_url
        elif provider == AUTH_PROVIDER_APPLE:
            raise IdleonAuthFailed(f"{provider.title()} login is not implemented yet")
        else:
            raise IdleonAuthFailed("Unsupported Idleon cloud login provider")
    else:
        raise IdleonCannotConnect(f"Unsupported data source type: {data_source_type}")

    return normalized


def _normalize_cloud_base_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Return normalized cloud source/provider data."""
    auth_provider = str(user_input.get(CONF_AUTH_PROVIDER) or "").strip()
    if auth_provider not in {
        AUTH_PROVIDER_EMAIL,
        AUTH_PROVIDER_GOOGLE,
        AUTH_PROVIDER_STEAM,
    }:
        raise IdleonAuthFailed("Unsupported Idleon cloud login provider")
    return {
        CONF_DATA_SOURCE_TYPE: DATA_SOURCE_IDLEON_CLOUD,
        CONF_AUTH_PROVIDER: auth_provider,
        CONF_SCAN_INTERVAL: _normalize_scan_interval(
            user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        ),
    }


def _normalize_scan_interval(value: Any) -> int:
    """Return a valid scan interval."""
    return max(MIN_SCAN_INTERVAL, int(value))


def _data_source_from_input(user_input: dict[str, Any]) -> IdleonDataSource:
    """Build a source model from normalized input."""
    return IdleonDataSource(
        source_type=user_input[CONF_DATA_SOURCE_TYPE],
        local_file_path=user_input.get(CONF_LOCAL_FILE_PATH),
        remote_url=user_input.get(CONF_REMOTE_URL),
        auth_provider=user_input.get(CONF_AUTH_PROVIDER),
        idleon_email=user_input.get(CONF_IDLEON_EMAIL),
        idleon_password=user_input.get(CONF_IDLEON_PASSWORD),
        steam_openid_response_url=user_input.get(CONF_STEAM_OPENID_RESPONSE_URL),
        idleon_user_id=user_input.get(CONF_IDLEON_USER_ID),
        idleon_refresh_token=user_input.get(CONF_IDLEON_REFRESH_TOKEN),
        scan_interval=user_input[CONF_SCAN_INTERVAL],
    )


def _is_google_cloud_input(user_input: dict[str, Any]) -> bool:
    """Return whether normalized data starts a Google cloud authorization."""
    return (
        user_input.get(CONF_DATA_SOURCE_TYPE) == DATA_SOURCE_IDLEON_CLOUD
        and user_input.get(CONF_AUTH_PROVIDER) == AUTH_PROVIDER_GOOGLE
        and not user_input.get(CONF_IDLEON_REFRESH_TOKEN)
    )


def _google_description_placeholders(
    device_code: IdleonGoogleDeviceCode | None,
) -> dict[str, str]:
    """Return placeholders for the Google device-code flow."""
    if device_code is None:
        return {
            "verification_url": "https://www.google.com/device",
            "verification_url_complete": "https://www.google.com/device",
            "user_code": "Loading...",
            "expires_in": "",
        }
    return {
        "verification_url": device_code.verification_url,
        "verification_url_complete": (
            device_code.verification_url_complete or device_code.verification_url
        ),
        "user_code": device_code.user_code,
        "expires_in": str(device_code.expires_in),
    }


def _source_description_placeholders(auth_provider: str | None) -> dict[str, str]:
    """Return placeholders for source-specific setup instructions."""
    return {"steam_login_url": ""}


def _steam_openid_realm(callback_url: str) -> str:
    """Return the OpenID realm for a Home Assistant Steam callback URL."""
    parts = urlsplit(callback_url)
    return urlunsplit((parts.scheme, parts.netloc, "/", "", ""))


def _source_unique_id(data_source: IdleonDataSource) -> str:
    """Return a stable source identity without sensitive URL query values."""
    if data_source.source_type == DATA_SOURCE_REMOTE_URL and data_source.remote_url:
        parts = urlsplit(data_source.remote_url)
        redacted_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        return f"{DATA_SOURCE_REMOTE_URL}:{redacted_url}"
    if data_source.source_type == DATA_SOURCE_IDLEON_CLOUD:
        account_id = data_source.idleon_user_id or data_source.idleon_email
        return f"{DATA_SOURCE_IDLEON_CLOUD}:{account_id}"

    return f"{DATA_SOURCE_LOCAL_FILE}:{data_source.local_file_path}"


def _source_unique_id_configured(
    hass: HomeAssistant,
    data_source: IdleonDataSource,
    *,
    current_entry_id: str | None = None,
) -> bool:
    """Return whether another config entry already uses this data source."""
    source_unique_id = _source_unique_id(data_source)
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == current_entry_id:
            continue
        if entry.unique_id == source_unique_id:
            return True
        with suppress(KeyError):
            entry_data = {**entry.data, **entry.options}
            if (
                _source_unique_id(_data_source_from_input(entry_data))
                == source_unique_id
            ):
                return True
    return False


def _entry_title(data_source: IdleonDataSource) -> str:
    """Return a human readable entry title."""
    if data_source.source_type == DATA_SOURCE_IDLEON_CLOUD:
        return "Idleon Cloud"
    if data_source.source_type == DATA_SOURCE_REMOTE_URL:
        return "Idleon Remote URL"
    return "Idleon Local File"
