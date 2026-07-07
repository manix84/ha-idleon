"""Tests for repository and integration metadata."""

from __future__ import annotations

import json
import subprocess
import tomllib
import zipfile
from pathlib import Path

from PIL import Image

from custom_components.idleon.const import DEFAULT_SCAN_INTERVAL, DOMAIN, VERSION
from scripts.release_asset_manifest import release_asset_paths

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

    assert hacs["name"] == "Legends of Idleon"
    assert hacs["homeassistant"] == "2026.6.4"


def test_default_refresh_interval_is_five_minutes() -> None:
    """Test default refresh uses Home Assistant's minimum five-minute cadence."""
    assert DEFAULT_SCAN_INTERVAL == 5 * 60


def test_brand_assets_exist() -> None:
    """Test HACS and local integration brand assets are present."""
    for path in (
        ROOT / "assets/official-idleon-vial-icon.png",
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


def test_coin_assets_exist() -> None:
    """Test money coin assets are bundled with the integration."""
    coin_names = {
        "copper",
        "silver",
        "gold",
        "platinum",
        "dementia",
        "void",
        "lustre",
        "starfire",
        "dreadlo",
        "godshard",
        "sunder",
        "tydal",
        "marbiglass",
        "orberal",
        "eclipse",
        "neuro",
        "isometric",
        "cyber",
        "synthesis",
        "polarity",
    }

    for coin_name in coin_names:
        path = ROOT / f"custom_components/idleon/assets/coins/{coin_name}.png"
        assert path.exists()
        assert path.stat().st_size > 0
        assert _png_dimensions(path) == (36, 36)
        assert _png_has_transparent_edge_padding(path)


def test_gem_asset_exists_with_padding() -> None:
    """Test the bundled gem asset keeps transparent visual padding."""
    source_path = ROOT / "assets/gem.png"
    served_path = ROOT / "custom_components/idleon/assets/gem.png"

    assert source_path.exists()
    assert source_path.stat().st_size > 0
    assert served_path.exists()
    assert served_path.stat().st_size > 0
    assert _png_dimensions(source_path) == (72, 72)
    assert _png_dimensions(served_path) == (88, 88)


def test_pet_crystal_asset_exists_with_padding() -> None:
    """Test the bundled Pet Crystal asset keeps transparent visual padding."""
    source_path = ROOT / "assets/pet_crystal.png"
    served_path = ROOT / "custom_components/idleon/assets/pet_crystal.png"

    assert source_path.exists()
    assert source_path.stat().st_size > 0
    assert served_path.exists()
    assert served_path.stat().st_size > 0
    assert _png_dimensions(source_path) == (72, 72)
    assert _png_dimensions(served_path) == (72, 72)
    assert _png_has_transparent_edge_padding(served_path)


def test_jade_asset_exists_with_padding() -> None:
    """Test the bundled Jade asset keeps transparent visual padding."""
    source_path = ROOT / "assets/jade.png"
    served_path = ROOT / "custom_components/idleon/assets/jade.png"

    assert source_path.exists()
    assert source_path.stat().st_size > 0
    assert served_path.exists()
    assert served_path.stat().st_size > 0
    assert _png_dimensions(source_path) == (51, 56)
    assert _png_dimensions(served_path) == (51, 56)
    assert _png_has_transparent_edge_padding(served_path)


def test_colosseum_assets_exist_with_padding() -> None:
    """Test colosseum score assets are bundled with transparent visual padding."""
    for colosseum_name in (
        "astro",
        "chillsnap",
        "dewdrop",
        "molten",
        "sandstone",
        "whimsical",
    ):
        source_path = ROOT / f"assets/colosseum/{colosseum_name}.png"
        served_path = (
            ROOT / f"custom_components/idleon/assets/colosseum/{colosseum_name}.png"
        )

        assert source_path.exists()
        assert source_path.stat().st_size > 0
        assert served_path.exists()
        assert served_path.stat().st_size > 0
        assert _png_has_transparent_edge_padding(served_path)


def test_class_icon_assets_exist() -> None:
    """Test representative class icon assets are bundled with the integration."""
    class_icons = (
        "beginner/beginner_icon.png",
        "archer/bowman_icon.png",
        "mage/bubonic_conjuror_icon.png",
        "warrior/death_bringer_icon.png",
    )

    for class_icon in class_icons:
        path = ROOT / f"custom_components/idleon/assets/classes/{class_icon}"
        assert path.exists()
        assert path.stat().st_size > 0


def test_stat_assets_exist() -> None:
    """Test main character stat assets are bundled with the integration."""
    for stat_name in ("strength", "agility", "wisdom", "luck"):
        path = ROOT / f"custom_components/idleon/assets/stats/{stat_name}.png"
        assert path.exists()
        assert path.stat().st_size > 0
        assert _png_dimensions(path) == (88, 88)


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


def test_release_archive_is_hacs_compatible() -> None:
    """Test the release archive contains the HACS integration layout."""
    result = subprocess.run(
        ["scripts/build-release"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    archive_path = Path(result.stdout.strip())

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "custom_components/idleon/__init__.py" in names
    assert "custom_components/idleon/manifest.json" in names
    assert "custom_components/idleon/brand/icon.png" in names
    assert "hacs.json" in names
    assert "README.md" in names
    assert "LICENSE" in names

    integrations = {
        parts[1]
        for name in names
        if (parts := Path(name).parts)
        and len(parts) > 2
        and parts[0] == "custom_components"
    }
    assert integrations == {"idleon"}


def test_release_archive_contains_only_runtime_assets() -> None:
    """Test release archives exclude source and unused asset categories."""
    result = subprocess.run(
        ["scripts/build-release"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    archive_path = Path(result.stdout.strip())

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    expected_runtime_assets = {
        "custom_components/idleon/assets/gem.png",
        "custom_components/idleon/assets/jade.png",
        "custom_components/idleon/assets/pet_crystal.png",
        "custom_components/idleon/assets/coins/gold.png",
        "custom_components/idleon/assets/classes/mage/bubonic_conjuror_icon.png",
        "custom_components/idleon/assets/colosseum/whimsical.png",
        "custom_components/idleon/assets/pouches/bug/big.png",
        "custom_components/idleon/assets/skills/alchemy.png",
        "custom_components/idleon/assets/stats/wisdom.png",
    }
    assert expected_runtime_assets <= names
    assert (
        "custom_components/idleon/assets/classes/mage/bubonic_conjuror.png" not in names
    )
    assert not any(name.startswith("assets/") for name in names)
    assert not any(name.endswith((".psd", ".pdf")) for name in names)


def test_release_asset_manifest_matches_runtime_asset_policy() -> None:
    """Test the release asset manifest includes only runtime asset categories."""
    names = {path.as_posix() for path in release_asset_paths(ROOT)}

    assert "custom_components/idleon/assets/gem.png" in names
    assert "custom_components/idleon/assets/jade.png" in names
    assert "custom_components/idleon/assets/pet_crystal.png" in names
    assert "custom_components/idleon/assets/companions.png" in names
    assert "custom_components/idleon/assets/character.png" in names
    assert "custom_components/idleon/assets/highest_character_level.png" in names
    assert "custom_components/idleon/assets/green_stack.png" in names
    assert "custom_components/idleon/assets/shrine.png" in names
    assert "custom_components/idleon/assets/world/tome/tome.png" in names
    assert "custom_components/idleon/assets/coins/polarity.png" in names
    assert (
        "custom_components/idleon/assets/classes/warrior/death_bringer_icon.png"
        in names
    )
    assert "custom_components/idleon/assets/colosseum/dewdrop.png" in names
    assert "custom_components/idleon/assets/pouches/mining/average.png" in names
    assert "custom_components/idleon/assets/activity/mining/copper.png" in names
    assert (
        "custom_components/idleon/assets/activity/monuments/paying_respect.png" in names
    )
    assert "custom_components/idleon/assets/skills/alchemy.png" in names
    assert "custom_components/idleon/assets/stats/strength.png" in names
    assert "custom_components/idleon/assets/monsters/000_nothing.png" in names
    assert "custom_components/idleon/assets/monsters/114_pirate_deckhand.png" in names
    assert (
        "custom_components/idleon/assets/classes/warrior/death_bringer.png" not in names
    )
    assert not any("/candy/" in name for name in names)


def test_release_entity_picture_assets_have_padding() -> None:
    """Test shipped entity picture assets fit Home Assistant circular crops."""
    for path in release_asset_paths(ROOT):
        if path.suffix.lower() == ".png" and path.is_relative_to(
            Path("custom_components/idleon/assets")
        ):
            assert _png_has_transparent_edge_padding(ROOT / path)


def _png_color_type(path: Path) -> int:
    """Return a PNG color type from the IHDR chunk."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return data[25]


def _png_dimensions(path: Path) -> tuple[int, int]:
    """Return PNG dimensions from the IHDR chunk."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return int.from_bytes(data[16:20]), int.from_bytes(data[20:24])


def _png_has_transparent_edge_padding(path: Path) -> bool:
    """Return whether a PNG has transparent padding on at least one edge."""
    image = Image.open(path).convert("RGBA")
    alpha_bounds = image.getchannel("A").getbbox()
    if alpha_bounds is None:
        return True
    left, top, right, bottom = alpha_bounds
    return any((left, top, image.width - right, image.height - bottom))
