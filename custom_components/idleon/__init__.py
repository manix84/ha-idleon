"""HA Idleon integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_AUTH_PROVIDER,
    CONF_DATA_SOURCE_TYPE,
    CONF_IDLEON_EMAIL,
    CONF_IDLEON_PASSWORD,
    CONF_IDLEON_REFRESH_TOKEN,
    CONF_IDLEON_USER_ID,
    CONF_LOCAL_FILE_PATH,
    CONF_REMOTE_URL,
    CONF_SCAN_INTERVAL,
    CONF_STEAM_OPENID_RESPONSE_URL,
    DEFAULT_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import IdleonDataUpdateCoordinator
from .idleon_data import IdleonClient
from .models import IdleonDataSource
from .steam_auth import async_register_steam_auth_callback_view


@dataclass(slots=True)
class IdleonRuntimeData:
    """Runtime objects attached to the config entry."""

    data_source: IdleonDataSource
    client: IdleonClient
    coordinator: IdleonDataUpdateCoordinator


type IdleonConfigEntry = ConfigEntry[IdleonRuntimeData]


async def async_setup(hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Set up HA Idleon integration globals."""
    async_register_steam_auth_callback_view(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: IdleonConfigEntry) -> bool:
    """Set up HA Idleon from a config entry."""
    data_source = _data_source_from_entry(entry)
    client = IdleonClient(hass, data_source)
    coordinator = IdleonDataUpdateCoordinator(
        hass,
        client,
        timedelta(seconds=data_source.scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = IdleonRuntimeData(
        data_source=data_source,
        client=client,
        coordinator=coordinator,
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IdleonConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data = None  # type: ignore[assignment]
    return unload_ok


def _data_source_from_entry(entry: ConfigEntry) -> IdleonDataSource:
    """Build a data source model from config entry data."""
    data = {**entry.data, **entry.options}
    return IdleonDataSource(
        source_type=data[CONF_DATA_SOURCE_TYPE],
        local_file_path=data.get(CONF_LOCAL_FILE_PATH),
        remote_url=data.get(CONF_REMOTE_URL),
        auth_provider=data.get(CONF_AUTH_PROVIDER),
        idleon_email=data.get(CONF_IDLEON_EMAIL),
        idleon_password=data.get(CONF_IDLEON_PASSWORD),
        steam_openid_response_url=data.get(CONF_STEAM_OPENID_RESPONSE_URL),
        idleon_user_id=data.get(CONF_IDLEON_USER_ID),
        idleon_refresh_token=data.get(CONF_IDLEON_REFRESH_TOKEN),
        scan_interval=data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )


async def _async_update_listener(
    hass: HomeAssistant,
    entry: IdleonConfigEntry,
) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
