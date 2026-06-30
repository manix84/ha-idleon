"""Registry and metadata-mode runner for IdleonToolbox-derived parsers."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from types import MappingProxyType
from typing import Any

from .generated_definitions import TOOLBOX_PARSER_DEFINITIONS
from .models import ToolboxParsedSection, ToolboxParserDefinition


def list_toolbox_parsers() -> tuple[ToolboxParserDefinition, ...]:
    """Return all known Toolbox parser definitions."""
    return _parser_definitions()


def get_toolbox_parser(parser_id: str) -> ToolboxParserDefinition:
    """Return a parser definition by id."""
    for definition in _parser_definitions():
        if definition.parser_id == parser_id:
            return definition
    msg = f"Unknown IdleonToolbox parser: {parser_id}"
    raise KeyError(msg)


def parse_all_toolbox_sections(
    raw_data: Mapping[str, Any],
    *,
    parser_ids: tuple[str, ...] | None = None,
) -> MappingProxyType[str, ToolboxParsedSection]:
    """Run every known Toolbox parser in metadata mode.

    The TypeScript project has many cross-dependent calculations. This Python
    pass creates the complete section surface first: every parser gets a stable
    section with the raw fields it can currently see and the websiteData keys it
    depends on. Detailed per-section calculations can then be ported behind this
    API without changing callers.
    """
    fields = _indexed_export_fields(raw_data)
    definitions = _selected_definitions(parser_ids)
    sections = {
        definition.parser_id: _parse_section(definition, fields)
        for definition in definitions
    }
    return MappingProxyType(sections)


@lru_cache(maxsize=1)
def _parser_definitions() -> tuple[ToolboxParserDefinition, ...]:
    """Return generated parser definitions as typed models."""
    return tuple(
        ToolboxParserDefinition(
            parser_id=str(definition["parser_id"]),
            source_path=str(definition["source_path"]),
            functions=tuple(str(value) for value in definition["functions"]),
            website_data=tuple(str(value) for value in definition["website_data"]),
            raw_fields=tuple(str(value) for value in definition["raw_fields"]),
        )
        for definition in TOOLBOX_PARSER_DEFINITIONS
    )


def _selected_definitions(
    parser_ids: tuple[str, ...] | None,
) -> tuple[ToolboxParserDefinition, ...]:
    """Return all requested parser definitions."""
    definitions = _parser_definitions()
    if parser_ids is None:
        return definitions
    requested = set(parser_ids)
    selected = tuple(
        definition for definition in definitions if definition.parser_id in requested
    )
    missing = requested - {definition.parser_id for definition in selected}
    if missing:
        msg = f"Unknown IdleonToolbox parser(s): {', '.join(sorted(missing))}"
        raise KeyError(msg)
    return selected


def _parse_section(
    definition: ToolboxParserDefinition,
    raw_data: Mapping[str, Any],
) -> ToolboxParsedSection:
    """Parse one Toolbox section in metadata mode."""
    found_fields: dict[str, Any] = {}
    missing_fields: list[str] = []
    for field in definition.raw_fields:
        value = _raw_field_value(raw_data, field)
        if value is _MISSING:
            missing_fields.append(field)
        else:
            found_fields[field] = value

    return ToolboxParsedSection(
        parser_id=definition.parser_id,
        source_path=definition.source_path,
        status="metadata_only",
        functions=definition.functions,
        website_data=definition.website_data,
        raw_fields=MappingProxyType(found_fields),
        missing_raw_fields=tuple(missing_fields),
    )


def _indexed_export_fields(raw_data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the field mapping from flat or wrapped Idleon exports."""
    save_data = raw_data.get("saveData")
    if isinstance(save_data, Mapping):
        return save_data
    return raw_data


def _raw_field_value(raw_data: Mapping[str, Any], field: str) -> Any:
    """Return a raw field by exact key or indexed-prefix key."""
    if field in raw_data:
        return raw_data[field]
    prefix = f"{field}_"
    indexed_values = {
        key: value for key, value in raw_data.items() if str(key).startswith(prefix)
    }
    if indexed_values:
        return MappingProxyType(indexed_values)
    return _MISSING


_MISSING = object()
