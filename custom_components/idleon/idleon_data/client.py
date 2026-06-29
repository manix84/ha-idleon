"""Read raw Idleon JSON from supported v1 data sources."""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from aiohttp import ClientError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import DATA_SOURCE_LOCAL_FILE, DATA_SOURCE_REMOTE_URL
from ..models import IdleonDataSource
from .exceptions import IdleonCannotConnect, IdleonInvalidJson


class IdleonClient:
    """Client for read-only Idleon JSON data sources."""

    def __init__(self, hass: HomeAssistant, data_source: IdleonDataSource) -> None:
        """Initialize the client."""
        self._hass = hass
        self._data_source = data_source

    async def async_get_data(self) -> Any:
        """Fetch raw JSON data from the configured source."""
        if self._data_source.source_type == DATA_SOURCE_LOCAL_FILE:
            return await self._async_get_local_file()
        if self._data_source.source_type == DATA_SOURCE_REMOTE_URL:
            return await self._async_get_remote_url()

        raise IdleonCannotConnect(
            f"Unsupported data source type: {self._data_source.source_type}"
        )

    async def _async_get_local_file(self) -> Any:
        """Load JSON from a local file path."""
        path = self._data_source.local_file_path
        if not path:
            raise IdleonCannotConnect("Local file path is required")

        def load_file() -> Any:
            with open(path, encoding="utf-8") as file:
                return json.load(file)

        try:
            return await self._hass.async_add_executor_job(load_file)
        except JSONDecodeError as err:
            raise IdleonInvalidJson("Local file does not contain valid JSON") from err
        except OSError as err:
            raise IdleonCannotConnect("Local file could not be read") from err

    async def _async_get_remote_url(self) -> Any:
        """Load JSON from a remote URL."""
        url = self._data_source.remote_url
        if not url:
            raise IdleonCannotConnect("Remote URL is required")

        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url, timeout=ClientTimeout(total=30)) as response:
                response.raise_for_status()
                text = await response.text()
        except ClientError as err:
            raise IdleonCannotConnect("Remote URL could not be fetched") from err

        try:
            return json.loads(text)
        except JSONDecodeError as err:
            raise IdleonInvalidJson("Remote URL did not return valid JSON") from err
