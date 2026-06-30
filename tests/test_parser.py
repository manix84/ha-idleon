"""Tests for Idleon JSON parsing."""

from __future__ import annotations

from datetime import UTC, datetime

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
