"""HA Idleon integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DATA_SOURCE_TYPE,
    CONF_LOCAL_FILE_PATH,
    CONF_REMOTE_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import IdleonDataUpdateCoordinator
from .idleon_data import IdleonClient
from .models import IdleonDataSource


@dataclass(slots=True)
class IdleonRuntimeData:
    """Runtime objects attached to the config entry."""

    data_source: IdleonDataSource
    client: IdleonClient
    coordinator: IdleonDataUpdateCoordinator


type IdleonConfigEntry = ConfigEntry[IdleonRuntimeData]


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
    return IdleonDataSource(
        source_type=entry.data[CONF_DATA_SOURCE_TYPE],
        local_file_path=entry.data.get(CONF_LOCAL_FILE_PATH),
        remote_url=entry.data.get(CONF_REMOTE_URL),
        scan_interval=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

