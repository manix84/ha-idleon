"""Shared test fixtures for HA Idleon."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in tests."""


@pytest.fixture
def fixture_path() -> Path:
    """Return the fixture directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_data_path(fixture_path: Path) -> Path:
    """Return the sample Idleon data fixture path."""
    return fixture_path / "sample_idleon_data.json"

