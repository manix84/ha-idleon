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
    CONF_AUTH_PROVIDER,
    CONF_DATA_SOURCE_TYPE,
    CONF_IDLEON_EMAIL,
    CONF_IDLEON_REFRESH_TOKEN,
    CONF_IDLEON_USER_ID,
    CONF_LOCAL_FILE_PATH,
    CONF_REMOTE_URL,
    CONF_SCAN_INTERVAL,
    DATA_SOURCE_LOCAL_FILE,
    DATA_SOURCE_REMOTE_URL,
    DATA_SOURCE_TYPES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .idleon_data import (
    IdleonCannotConnect,
    IdleonClient,
    IdleonInvalidJson,
    IdleonInvalidSchema,
    parse_idleon_account,
)
from .models import IdleonDataSource

_LOGGER = getLogger(__name__)


class IdleonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle an Idleon config flow."""

    VERSION = 1
    _data_source_type: str | None = None

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
                data_source = _data_source_from_input(normalized_input)
                await _async_validate_source(self.hass, data_source)
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
                data_source = _data_source_from_input(normalized_input)
                await _async_validate_source(self.hass, data_source)
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


async def _async_validate_source(
    hass: HomeAssistant,
    data_source: IdleonDataSource,
) -> None:
    """Fetch and parse a source before storing the config entry."""
    raw_data = await IdleonClient(hass, data_source).async_get_data()
    parse_idleon_account(raw_data)


def _source_type_schema(default: str = DATA_SOURCE_LOCAL_FILE) -> vol.Schema:
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

    if data_source_type == DATA_SOURCE_REMOTE_URL:
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
        idleon_user_id=user_input.get(CONF_IDLEON_USER_ID),
        idleon_refresh_token=user_input.get(CONF_IDLEON_REFRESH_TOKEN),
        scan_interval=user_input[CONF_SCAN_INTERVAL],
    )


def _source_unique_id(data_source: IdleonDataSource) -> str:
    """Return a stable source identity without sensitive URL query values."""
    if data_source.source_type == DATA_SOURCE_REMOTE_URL and data_source.remote_url:
        parts = urlsplit(data_source.remote_url)
        redacted_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        return f"{DATA_SOURCE_REMOTE_URL}:{redacted_url}"

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
    if data_source.source_type == DATA_SOURCE_REMOTE_URL:
        return "Idleon Remote URL"
    return "Idleon Local File"
