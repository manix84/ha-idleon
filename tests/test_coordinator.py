"""Tests for the Idleon coordinator."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.idleon.coordinator import IdleonDataUpdateCoordinator
from custom_components.idleon.idleon_data import IdleonCannotConnect


class _SuccessfulClient:
    """Client fake that returns fixture data."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    async def async_get_data(self) -> dict[str, Any]:
        """Return fixture data."""
        return self.data


class _FailingClient:
    """Client fake that raises a data source error."""

    async def async_get_data(self) -> None:
        """Raise a data source error."""
        raise IdleonCannotConnect("source failed")


async def test_coordinator_successful_update(
    hass: HomeAssistant,
    sample_data_path: Path,
) -> None:
    """Test a successful coordinator update."""
    coordinator = IdleonDataUpdateCoordinator(
        hass,
        _SuccessfulClient(json.loads(sample_data_path.read_text())),
        timedelta(seconds=3600),
    )

    account = await coordinator._async_update_data()

    assert account.character_count == 2
    assert account.total_level == 365
    assert coordinator.last_successful_update is not None
    assert coordinator.last_error_type is None


async def test_coordinator_failed_update(hass: HomeAssistant) -> None:
    """Test a failed coordinator update records error details."""
    coordinator = IdleonDataUpdateCoordinator(
        hass,
        _FailingClient(),
        timedelta(seconds=3600),
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.last_error_type == "IdleonCannotConnect"
    assert coordinator.last_error_message == "source failed"

