"""Tests for IdleonToolbox-derived parser definitions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.idleon.idleon_data import (
    get_toolbox_parser,
    list_toolbox_parsers,
    parse_all_toolbox_sections,
)


def test_toolbox_parser_definitions_cover_toolbox_sources() -> None:
    """Test generated parser definitions include the expected parser surface."""
    definitions = list_toolbox_parsers()
    parser_ids = {definition.parser_id for definition in definitions}

    assert len(definitions) == 97
    assert "character" in parser_ids
    assert "world-1.stamps" in parser_ids
    assert "world-7.sushiStation" in parser_ids
    assert "class-specific.grimoire" in parser_ids

    character = get_toolbox_parser("character")
    assert character.source_path == "character.ts"
    assert "classes" in character.website_data
    assert "mapNames" in character.website_data
    assert "monsters" in character.website_data
    assert "CharacterClass" in character.raw_fields
    assert "CurrentMap" in character.raw_fields


def test_toolbox_sections_parse_raw_fixture_metadata(fixture_path: Path) -> None:
    """Test metadata-mode sections expose raw fields for current user data."""
    raw_data = json.loads(
        (fixture_path / "indexed_idleon_export_sample.json").read_text()
    )

    sections = parse_all_toolbox_sections(raw_data, parser_ids=("character", "cards"))

    character = sections["character"]
    assert character.status == "metadata_only"
    assert character.source_path == "character.ts"
    assert "getCharacters" in character.functions
    assert set(character.raw_fields["CharacterClass"]) == {
        "CharacterClass_0",
        "CharacterClass_1",
    }
    assert set(character.raw_fields["CurrentMap"]) == {
        "CurrentMap_0",
        "CurrentMap_1",
    }
    assert "classes" in character.website_data

    cards = sections["cards"]
    assert cards.source_path == "cards.ts"
    assert "Cards0" in cards.missing_raw_fields


def test_toolbox_sections_reject_unknown_parser() -> None:
    """Test selected parser execution validates parser ids."""
    with pytest.raises(KeyError, match="Unknown IdleonToolbox parser"):
        parse_all_toolbox_sections({}, parser_ids=("missing",))
