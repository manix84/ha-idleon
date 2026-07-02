"""Config flow for HA Idleon."""

from __future__ import annotations

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
    DATA_SOURCE_TYPES,
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
)
from .models import IdleonDataSource

_LOGGER = getLogger(__name__)


class IdleonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle an Idleon config flow."""

    VERSION = 1
    _data_source_type: str | None = None
    _pending_google_input: dict[str, Any] | None = None
    _google_device_code: IdleonGoogleDeviceCode | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Select the data source type."""
        if user_input is not None:
            self._data_source_type = user_input[CONF_DATA_SOURCE_TYPE]
            return await self.async_step_source()

        return self.async_show_form(
            step_id="user",
            data_schema=_source_type_schema(),
        )

    async def async_step_source(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle source details and validation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized_input = _normalize_user_input(
                    self._data_source_type,
                    user_input,
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
            step_id="source",
            data_schema=_source_details_schema(self._data_source_type),
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
        current_data = {**config_entry.data, **config_entry.options}
        self._data_source_type = current_data[CONF_DATA_SOURCE_TYPE]
        self._pending_google_input: dict[str, Any] | None = None
        self._google_device_code: IdleonGoogleDeviceCode | None = None

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Select the data source type."""
        if user_input is not None:
            self._data_source_type = user_input[CONF_DATA_SOURCE_TYPE]
            return await self.async_step_source()

        return self.async_show_form(
            step_id="init",
            data_schema=_source_type_schema(self._data_source_type),
        )

    async def async_step_source(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle source option details and validation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized_input = _normalize_user_input(
                    self._data_source_type,
                    user_input,
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
                if _source_unique_id_configured(
                    self.hass,
                    data_source,
                    current_entry_id=self._config_entry.entry_id,
                ):
                    errors["base"] = "already_configured"
                    return self.async_show_form(
                        step_id="source",
                        data_schema=_source_details_schema(
                            self._data_source_type,
                            {**self._config_entry.data, **self._config_entry.options},
                        ),
                        errors=errors,
                    )
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    title=_entry_title(data_source),
                    unique_id=_source_unique_id(data_source),
                )
                return self.async_create_entry(
                    title="",
                    data=normalized_input,
                )

        current_data = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="source",
            data_schema=_source_details_schema(self._data_source_type, current_data),
            errors=errors,
        )

    async def async_step_google(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle Google device-code authorization in options."""
        errors: dict[str, str] = {}

        if self._pending_google_input is None:
            return await self.async_step_init()

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
                if _source_unique_id_configured(
                    self.hass,
                    data_source,
                    current_entry_id=self._config_entry.entry_id,
                ):
                    errors["base"] = "already_configured"
                else:
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        title=_entry_title(data_source),
                        unique_id=_source_unique_id(data_source),
                    )
                    return self.async_create_entry(
                        title="",
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
    if data_source.auth_provider != AUTH_PROVIDER_EMAIL:
        raise IdleonAuthFailed("Only Idleon email/password login is supported")
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
    prepared[CONF_IDLEON_USER_ID] = credentials.user_id
    prepared[CONF_IDLEON_REFRESH_TOKEN] = credentials.refresh_token
    if credentials.email:
        prepared[CONF_IDLEON_EMAIL] = credentials.email
    return prepared


def _source_type_schema(default: str = DATA_SOURCE_IDLEON_CLOUD) -> vol.Schema:
    """Return the source type selection schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_DATA_SOURCE_TYPE,
                default=default,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=DATA_SOURCE_TYPES,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _source_details_schema(
    data_source_type: str | None,
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    """Return the source details schema."""
    defaults = defaults or {}
    scan_interval = defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    fields: dict[vol.Marker, Any] = {}

    if data_source_type == DATA_SOURCE_IDLEON_CLOUD:
        fields[
            vol.Required(
                CONF_AUTH_PROVIDER,
                default=defaults.get(CONF_AUTH_PROVIDER, AUTH_PROVIDER_EMAIL),
            )
        ] = SelectSelector(
            SelectSelectorConfig(
                options=[AUTH_PROVIDER_EMAIL, AUTH_PROVIDER_GOOGLE],
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
        fields[
            vol.Optional(
                CONF_IDLEON_EMAIL,
                default=defaults.get(CONF_IDLEON_EMAIL, ""),
            )
        ] = TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL))
        fields[vol.Optional(CONF_IDLEON_PASSWORD)] = TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
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


def _normalize_user_input(
    data_source_type: str | None,
    user_input: dict[str, Any],
) -> dict[str, Any]:
    """Validate conditional fields and return normalized entry data."""
    if not data_source_type:
        raise IdleonCannotConnect("Data source type is required")

    scan_interval = max(
        MIN_SCAN_INTERVAL,
        int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
    )

    normalized: dict[str, Any] = {
        CONF_DATA_SOURCE_TYPE: data_source_type,
        CONF_SCAN_INTERVAL: scan_interval,
    }

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
        auth_provider = str(
            user_input.get(CONF_AUTH_PROVIDER) or AUTH_PROVIDER_EMAIL
        ).strip()
        normalized[CONF_AUTH_PROVIDER] = auth_provider
        if auth_provider == AUTH_PROVIDER_EMAIL:
            idleon_email = str(user_input.get(CONF_IDLEON_EMAIL) or "").strip()
            idleon_password = str(user_input.get(CONF_IDLEON_PASSWORD) or "")
            if not idleon_email or not idleon_password:
                raise IdleonAuthFailed("Idleon email and password are required")
            normalized[CONF_IDLEON_EMAIL] = idleon_email
            normalized[CONF_IDLEON_PASSWORD] = idleon_password
        elif auth_provider != AUTH_PROVIDER_GOOGLE:
            raise IdleonAuthFailed("Unsupported Idleon cloud login provider")
    else:
        raise IdleonCannotConnect(f"Unsupported data source type: {data_source_type}")

    return normalized


def _data_source_from_input(user_input: dict[str, Any]) -> IdleonDataSource:
    """Build a source model from normalized input."""
    return IdleonDataSource(
        source_type=user_input[CONF_DATA_SOURCE_TYPE],
        local_file_path=user_input.get(CONF_LOCAL_FILE_PATH),
        remote_url=user_input.get(CONF_REMOTE_URL),
        auth_provider=user_input.get(CONF_AUTH_PROVIDER),
        idleon_email=user_input.get(CONF_IDLEON_EMAIL),
        idleon_password=user_input.get(CONF_IDLEON_PASSWORD),
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
            "user_code": "Loading...",
            "expires_in": "",
        }
    return {
        "verification_url": device_code.verification_url,
        "user_code": device_code.user_code,
        "expires_in": str(device_code.expires_in),
    }


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
