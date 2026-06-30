"""Helpers for loading split Idleon websiteData reference files."""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WEBSITE_DATA_DIR = ROOT / "examples/websiteData"
MANIFEST_FILENAME = "_manifest.json"


class WebsiteDataNotFoundError(FileNotFoundError):
    """Raised when split websiteData reference files are unavailable."""


def load_website_data_part(
    key: str,
    *,
    base_path: Path | None = None,
) -> Any:
    """Load one split websiteData JSON part by top-level key."""
    data_dir = base_path or DEFAULT_WEBSITE_DATA_DIR
    manifest = load_website_data_manifest(base_path=data_dir)
    files = manifest.get("files")
    if not isinstance(files, Mapping) or key not in files:
        msg = f"websiteData key not found: {key}"
        raise WebsiteDataNotFoundError(msg)

    entry = files[key]
    if not isinstance(entry, Mapping):
        msg = f"websiteData manifest entry is invalid: {key}"
        raise WebsiteDataNotFoundError(msg)

    json_filename = entry.get("json")
    if not isinstance(json_filename, str):
        msg = f"websiteData manifest entry has no JSON file: {key}"
        raise WebsiteDataNotFoundError(msg)

    return json.loads((data_dir / json_filename).read_text())


def load_website_data_manifest(
    *,
    base_path: Path | None = None,
) -> Mapping[str, Any]:
    """Load the split websiteData manifest."""
    data_dir = base_path or DEFAULT_WEBSITE_DATA_DIR
    path = data_dir / MANIFEST_FILENAME
    if not path.exists():
        msg = (
            f"Split websiteData manifest not found at {path}. "
            "Run scripts/split-website-data first."
        )
        raise WebsiteDataNotFoundError(msg)
    data = json.loads(path.read_text())
    if not isinstance(data, Mapping):
        msg = f"Split websiteData manifest is invalid at {path}"
        raise WebsiteDataNotFoundError(msg)
    return data


@lru_cache(maxsize=16)
def load_default_website_data_part(key: str) -> Any:
    """Load and cache one split websiteData part from the default location."""
    return load_website_data_part(key)
