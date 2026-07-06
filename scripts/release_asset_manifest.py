"""Build the list of integration assets that belong in release archives."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.idleon.idleon_data.equipment import (  # noqa: E402
    EQUIPMENT_ITEM_ASSETS,
)
from custom_components.idleon.utils.number_format import IDLEON_COIN_TIERS  # noqa: E402

INTEGRATION_DIR = Path("custom_components/idleon")
ASSETS_DIR = INTEGRATION_DIR / "assets"

CHARACTER_STAT_ASSETS = ("strength", "agility", "wisdom", "luck")
STATIC_ASSET_EXTENSIONS = {".png"}


def release_asset_paths(root: Path) -> set[Path]:
    """Return integration asset paths that should ship in release archives."""
    asset_root = root / ASSETS_DIR
    assets: set[Path] = set()

    _add_existing(assets, root, asset_root / "gem.png")
    _add_existing(assets, root, asset_root / "jade.png")
    _add_existing(assets, root, asset_root / "pet_crystal.png")

    for coin_name, _tier_value in IDLEON_COIN_TIERS:
        coin_slug = coin_name.lower().replace(" ", "_")
        _add_required(assets, root, asset_root / "coins" / f"{coin_slug}.png")

    for stat_name in CHARACTER_STAT_ASSETS:
        _add_required(assets, root, asset_root / "stats" / f"{stat_name}.png")

    for path in _iter_matching_assets(asset_root / "skills", "*.png"):
        assets.add(path.relative_to(root))

    for path in _iter_matching_assets(asset_root / "classes", "*/*_icon.png"):
        assets.add(path.relative_to(root))

    for path in _iter_matching_assets(asset_root / "colosseum", "*.png"):
        assets.add(path.relative_to(root))

    for path in _iter_matching_assets(asset_root / "pouches", "**/*.png"):
        assets.add(path.relative_to(root))

    for path in _iter_matching_assets(asset_root / "activity", "**/*.png"):
        assets.add(path.relative_to(root))

    for path in _iter_matching_assets(asset_root / "monsters", "*.png"):
        assets.add(path.relative_to(root))

    for relative_asset_path in sorted(set(EQUIPMENT_ITEM_ASSETS.values())):
        _add_required(assets, root, asset_root / relative_asset_path)

    return assets


def should_include_integration_file(path: Path, root: Path) -> bool:
    """Return whether an integration file should be included in the release ZIP."""
    relative_path = path.relative_to(root)
    if "__pycache__" in path.parts:
        return False
    if not path.is_file():
        return False
    if not _is_under(relative_path, ASSETS_DIR):
        return True
    return relative_path in release_asset_paths(root)


def _iter_matching_assets(directory: Path, pattern: str) -> Iterable[Path]:
    """Yield existing runtime image assets for a category."""
    if not directory.exists():
        return ()
    return (
        path
        for path in sorted(directory.glob(pattern))
        if path.is_file() and path.suffix.lower() in STATIC_ASSET_EXTENSIONS
    )


def _add_existing(assets: set[Path], root: Path, path: Path) -> None:
    """Add an optional asset when it exists."""
    if path.is_file():
        assets.add(path.relative_to(root))


def _add_required(assets: set[Path], root: Path, path: Path) -> None:
    """Add a required asset or fail the release build with a clear error."""
    if not path.is_file():
        msg = f"Missing release asset: {path.relative_to(root)}"
        raise SystemExit(msg)
    assets.add(path.relative_to(root))


def _is_under(path: Path, parent: Path) -> bool:
    """Return whether a relative path is under another relative path."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    for asset_path in sorted(release_asset_paths(Path.cwd())):
        sys.stdout.write(f"{asset_path.as_posix()}\n")
