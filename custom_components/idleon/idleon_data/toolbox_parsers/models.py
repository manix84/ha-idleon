"""Typed models for IdleonToolbox-derived parser metadata."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolboxParserDefinition:
    """Metadata for one parser mirrored from IdleonToolbox."""

    parser_id: str
    source_path: str
    functions: tuple[str, ...]
    website_data: tuple[str, ...]
    raw_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ToolboxParsedSection:
    """Metadata-mode parsed output for one Toolbox parser section."""

    parser_id: str
    source_path: str
    status: str
    functions: tuple[str, ...]
    website_data: tuple[str, ...]
    raw_fields: MappingProxyType[str, Any]
    missing_raw_fields: tuple[str, ...]
