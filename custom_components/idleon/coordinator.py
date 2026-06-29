"""Data update coordinator for HA Idleon."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from logging import getLogger

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .idleon_data import IdleonClient, IdleonDataError, parse_idleon_account
from .models import IdleonAccount

_LOGGER = getLogger(__name__)


class IdleonDataUpdateCoordinator(DataUpdateCoordinator[IdleonAccount]):
    """Coordinator that fetches and parses Idleon account data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: IdleonClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            always_update=False,
        )
        self._client = client
        self.last_successful_update: datetime | None = None
        self.last_error_type: str | None = None
        self.last_error_message: str | None = None

    async def _async_update_data(self) -> IdleonAccount:
        """Fetch source JSON and parse it into an account model."""
        try:
            raw_data = await self._client.async_get_data()
            account = parse_idleon_account(raw_data)
        except IdleonDataError as err:
            self.last_error_type = type(err).__name__
            self.last_error_message = str(err)
            raise UpdateFailed(str(err)) from err

        self.last_successful_update = datetime.now(UTC)
        self.last_error_type = None
        self.last_error_message = None
        return account
