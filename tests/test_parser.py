"""Tests for Idleon JSON parsing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from custom_components.idleon.idleon_data import (
    IdleonInvalidSchema,
    parse_idleon_account,
)


def test_parser_invalid_schema() -> None:
    """Test invalid data raises a schema error."""
    with pytest.raises(IdleonInvalidSchema):
        parse_idleon_account({"not_characters": []})


def test_parser_accepts_mapping_characters_and_aliases() -> None:
    """Test parser accepts mapping-style characters and common field aliases."""
    account = parse_idleon_account(
        {
            "profile": {
                "accountId": "account-123",
                "accountName": "Alias Account",
                "gemCount": "42",
                "updatedAt": "2026-06-29T12:00:00Z",
                "chars": {
                    "wizard_1": {
                        "characterName": "Wizard One",
                        "lvl": "123",
                        "className": "Elemental Sorcerer",
                        "currentMap": "Town",
                        "currentActivity": "Crafting",
                        "afkHours": "1.5",
                        "inventoryFull": "true",
                    },
                    "miner_2": {
                        "name": "Miner Two",
                        "level": 10,
                        "class": "Squire",
                        "map": "Mines",
                        "activity": "Mining",
                        "requires_attention": "false",
                    },
                },
            }
        }
    )

    assert account.account_id == "account-123"
    assert account.name == "Alias Account"
    assert account.gems == 42
    assert account.total_level == 133
    assert account.source_updated_at == datetime(2026, 6, 29, 12, tzinfo=UTC)
    assert account.characters[0].character_id == "wizard_1"
    assert account.characters[0].name == "Wizard One"
    assert account.characters[0].level == 123
    assert account.characters[0].afk_hours == 1.5
    assert account.characters[0].inventory_full is True
    assert account.characters[0].needs_attention is True
    assert account.characters[0].details == {}
    assert account.characters[1].needs_attention is False


def test_parser_defaults_invalid_numbers() -> None:
    """Test invalid numeric values do not crash flexible parsing."""
    account = parse_idleon_account(
        {
            "characters": [
                {
                    "name": "Bad Numbers",
                    "level": "not-a-number",
                    "afk_hours": "also-bad",
                }
            ],
            "gems": "invalid",
        }
    )

    assert account.total_level == 0
    assert account.gems == 0
    assert account.characters[0].level == 0
    assert account.characters[0].afk_hours == 0.0


def test_parser_accepts_indexed_idleon_export(fixture_path: Path) -> None:
    """Test parser accepts indexed raw Idleon export data."""
    raw_data = json.loads(
        (fixture_path / "indexed_idleon_export_sample.json").read_text()
    )

    account = parse_idleon_account(raw_data)

    assert account.account_id == "idleon_account"
    assert account.name == "Legends of Idleon Account"
    assert account.gems == 3467
    assert account.total_level == 2232
    assert account.character_count == 2
    assert account.source_updated_at == datetime.fromtimestamp(
        1782760865.1540005,
        tz=UTC,
    )

    first_character = account.characters[0]
    assert first_character.character_id == "character_0"
    assert first_character.name == "Character 1"
    assert first_character.level == 1134
    assert first_character.character_class == "Death Bringer"
    assert first_character.current_map == "The Hole"
    assert first_character.current_activity == "Fighting: Gloomie Mushroom"
    assert first_character.afk_hours == 2.0
    assert first_character.inventory_full is False
    assert first_character.needs_attention is False
    assert first_character.details["raw_class_id"] == 14
    assert first_character.details["raw_map_id"] == 216
    assert first_character.details["afk_target"] == "caveB"
    assert first_character.details["afk_seconds"] == 7200

    second_character = account.characters[1]
    assert second_character.character_id == "character_1"
    assert second_character.level == 1098
    assert second_character.character_class == "Elemental Sorcerer"
    assert second_character.current_map == "Pirate Mess Hall"
    assert second_character.current_activity == "Fighting: Pirate Deckhand"
    assert second_character.afk_hours == 0.5


def test_parser_accepts_wrapped_idleon_export(fixture_path: Path) -> None:
    """Test parser accepts wrapped exports from Idleon API Downloader."""
    raw_data = json.loads(
        (fixture_path / "wrapped_idleon_export_sample.json").read_text()
    )

    account = parse_idleon_account(raw_data)

    assert account.gems == 123
    assert account.total_level == 303
    assert account.character_count == 2
    assert account.source_updated_at == datetime.fromtimestamp(
        1782760865.1540005,
        tz=UTC,
    )

    first_character = account.characters[0]
    assert first_character.name == "Alpha Archer"
    assert first_character.level == 101
    assert first_character.character_class == "Bowman"
    assert first_character.current_map == "Freefall Caverns"
    assert first_character.current_activity == "Fighting: Green Mushroom"
    assert first_character.afk_hours == 1.0
    assert first_character.inventory_full is True
    assert first_character.needs_attention is True
    assert first_character.details["raw_class_id"] == 20
    assert first_character.details["inventory_slots_total"] == 2
    assert first_character.details["inventory_slots_used"] == 2
    assert first_character.details["inventory_bag_count"] == 2
    assert first_character.details["inventory_bags"] == [
        "Inventory Bag A",
        "Snakeskinventory Bag",
    ]
    assert first_character.details["max_carry_capacity"] == {
        "Copper": 250,
        "OakTree": "500",
    }

    second_character = account.characters[1]
    assert second_character.name == "Beta Mage"
    assert second_character.level == 202
    assert second_character.character_class == "Elemental Sorcerer"
    assert second_character.inventory_full is False
    assert second_character.needs_attention is False
