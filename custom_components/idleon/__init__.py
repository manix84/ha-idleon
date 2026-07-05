"""HA Idleon integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

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
    DOMAIN,
    PLATFORMS,
)
from .coordinator import IdleonDataUpdateCoordinator
from .idleon_data import IdleonClient
from .models import IdleonDataSource
from .steam_auth import async_register_steam_auth_callback_view

STATIC_URL_PATH = "/idleon_static"
STATIC_ASSET_PATH = Path(__file__).parent / "assets"


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
    if hass.http is not None:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    STATIC_URL_PATH,
                    str(STATIC_ASSET_PATH),
                    cache_headers=True,
                )
            ]
        )
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
    _async_repair_character_device_relationships(hass, entry)
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


def _async_repair_character_device_relationships(
    hass: HomeAssistant,
    entry: IdleonConfigEntry,
) -> None:
    """Ensure existing character devices are connected via the account device."""
    device_registry = dr.async_get(hass)
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, _account_device_identifier(entry))}
    )
    if account_device is None:
        return

    for character in entry.runtime_data.coordinator.data.characters:
        character_device = device_registry.async_get_device(
            identifiers={(DOMAIN, _character_device_identifier(entry, character))}
        )
        if character_device is None:
            continue
        if character_device.via_device_id == account_device.id:
            continue
        device_registry.async_update_device(
            character_device.id,
            via_device_id=account_device.id,
        )


def _account_device_identifier(entry: ConfigEntry) -> str:
    """Return the account device identifier."""
    return f"{entry.entry_id}_account"


def _character_device_identifier(entry: ConfigEntry, character: Any) -> str:
    """Return a character device identifier."""
    return f"{entry.entry_id}_{character.character_id}"
