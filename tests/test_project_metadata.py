"""Tests for repository and integration metadata."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from custom_components.idleon.const import DEFAULT_SCAN_INTERVAL, DOMAIN, VERSION

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


def test_default_refresh_interval_matches_idleon_toolbox() -> None:
    """Test default refresh follows Idleon Toolbox's four-hour cadence."""
    assert DEFAULT_SCAN_INTERVAL == 4 * 60 * 60


def test_brand_assets_exist() -> None:
    """Test HACS and local integration brand assets are present."""
    for path in (
        ROOT / "assets/official-idleon-icon.png",
        ROOT / "assets/project-icon.png",
        ROOT / "assets/project-icon-transparent.png",
        ROOT / "brands/icon.png",
        ROOT / "brands/icon@2x.png",
        ROOT / "brands/logo.png",
        ROOT / "brands/logo@2x.png",
        ROOT / "custom_components/idleon/icon.png",
        ROOT / "custom_components/idleon/icon@2x.png",
        ROOT / "custom_components/idleon/logo.png",
        ROOT / "custom_components/idleon/logo@2x.png",
        ROOT / "custom_components/idleon/brand/icon.png",
        ROOT / "custom_components/idleon/brand/icon@2x.png",
        ROOT / "custom_components/idleon/brand/logo.png",
        ROOT / "custom_components/idleon/brand/logo@2x.png",
    ):
        assert path.exists()
        assert path.stat().st_size > 0


def test_served_brand_assets_are_transparent_pngs() -> None:
    """Test Home Assistant served brand assets preserve transparency."""
    for path in (
        ROOT / "brands/icon.png",
        ROOT / "brands/icon@2x.png",
        ROOT / "brands/logo.png",
        ROOT / "brands/logo@2x.png",
        ROOT / "custom_components/idleon/icon.png",
        ROOT / "custom_components/idleon/icon@2x.png",
        ROOT / "custom_components/idleon/logo.png",
        ROOT / "custom_components/idleon/logo@2x.png",
        ROOT / "custom_components/idleon/brand/icon.png",
        ROOT / "custom_components/idleon/brand/icon@2x.png",
        ROOT / "custom_components/idleon/brand/logo.png",
        ROOT / "custom_components/idleon/brand/logo@2x.png",
    ):
        assert _png_color_type(path) == 6


def test_project_icon_is_documentation_only() -> None:
    """Test Home Assistant brand assets are not copied from the project icon."""
    assert (ROOT / "assets/project-icon-transparent.png").read_bytes() != (
        ROOT / "custom_components/idleon/brand/icon.png"
    ).read_bytes()


def test_project_version_matches_integration_version() -> None:
    """Test Python package metadata and integration constants use one version."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["version"] == VERSION


def _png_color_type(path: Path) -> int:
    """Return a PNG color type from the IHDR chunk."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return data[25]
