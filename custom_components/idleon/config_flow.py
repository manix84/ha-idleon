"""Config flow for HA Idleon."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
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
    CONF_DATA_SOURCE_TYPE,
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


class IdleonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle an Idleon config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized_input = _normalize_user_input(user_input)
                data_source = _data_source_from_input(normalized_input)
                await self.async_set_unique_id(_source_unique_id(data_source))
                self._abort_if_unique_id_configured()
                await _async_validate_source(self.hass, data_source)
            except IdleonCannotConnect:
                errors["base"] = "cannot_connect"
            except IdleonInvalidJson:
                errors["base"] = "invalid_json"
            except IdleonInvalidSchema:
                errors["base"] = "invalid_schema"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=_entry_title(data_source),
                    data=normalized_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_data_schema(),
            errors=errors,
        )


async def _async_validate_source(
    hass: HomeAssistant,
    data_source: IdleonDataSource,
) -> None:
    """Fetch and parse a source before storing the config entry."""
    raw_data = await IdleonClient(hass, data_source).async_get_data()
    parse_idleon_account(raw_data)


def _data_schema() -> vol.Schema:
    """Return the config flow schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_DATA_SOURCE_TYPE,
                default=DATA_SOURCE_LOCAL_FILE,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=DATA_SOURCE_TYPES,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_LOCAL_FILE_PATH): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_REMOTE_URL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=DEFAULT_SCAN_INTERVAL,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="seconds",
                )
            ),
        }
    )


def _normalize_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Validate conditional fields and return normalized entry data."""
    data_source_type = user_input[CONF_DATA_SOURCE_TYPE]
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
        scan_interval=user_input[CONF_SCAN_INTERVAL],
    )


def _source_unique_id(data_source: IdleonDataSource) -> str:
    """Return a stable source identity without sensitive URL query values."""
    if data_source.source_type == DATA_SOURCE_REMOTE_URL and data_source.remote_url:
        parts = urlsplit(data_source.remote_url)
        redacted_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        return f"{DATA_SOURCE_REMOTE_URL}:{redacted_url}"

    return f"{DATA_SOURCE_LOCAL_FILE}:{data_source.local_file_path}"


def _entry_title(data_source: IdleonDataSource) -> str:
    """Return a human readable entry title."""
    if data_source.source_type == DATA_SOURCE_REMOTE_URL:
        return "Idleon Remote URL"
    return "Idleon Local File"
