"""Tests for repository and integration metadata."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from custom_components.idleon.const import DOMAIN, VERSION

ROOT = Path(__file__).parents[1]


def test_manifest_metadata() -> None:
    """Test Home Assistant manifest metadata stays consistent."""
    manifest = json.loads((ROOT / "custom_components/idleon/manifest.json").read_text())

    assert manifest["domain"] == DOMAIN
    assert manifest["version"] == VERSION
    assert manifest["config_flow"] is True
    assert manifest["integration_type"] == "service"
    assert manifest["iot_class"] == "cloud_polling"
    assert manifest["requirements"] == []


def test_hacs_metadata() -> None:
    """Test HACS metadata remains valid for a custom integration repository."""
    hacs = json.loads((ROOT / "hacs.json").read_text())

    assert hacs["name"] == "HA Idleon"
    assert hacs["homeassistant"] == "2026.6.4"


def test_project_version_matches_integration_version() -> None:
    """Test Python package metadata and integration constants use one version."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["version"] == VERSION
