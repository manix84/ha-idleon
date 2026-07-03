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
from custom_components.idleon.idleon_data.website_data import WebsiteDataNotFoundError


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
    assert account.details["highest_character_level"] == 123
    assert account.details["highest_level_character"] == "Wizard One"
    assert account.details["class_counts"] == {
        "Elemental Sorcerer": 1,
        "Squire": 1,
    }
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
    assert account.details["highest_character_level"] == 1134
    assert account.details["highest_level_character"] == "Character 1"
    assert account.details["total_skill_level"] == 423
    assert account.details["class_counts"] == {
        "Death Bringer": 1,
        "Elemental Sorcerer": 1,
    }

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


def test_parser_labels_indexed_characters_from_cog_order() -> None:
    """Test flat indexed exports can infer useful character labels from CogO."""
    account = parse_idleon_account(
        {
            "CharacterClass_0": 14,
            "CharacterClass_1": 34,
            "CharacterClass_2": 22,
            "CharacterClass_3": 29,
            "CharacterClass_4": 12,
            "CurrentMap_0": 216,
            "CurrentMap_1": 325,
            "CurrentMap_2": 325,
            "CurrentMap_3": 325,
            "CurrentMap_4": 325,
            "Lv0_0": [1134],
            "Lv0_1": [1097],
            "Lv0_2": [1110],
            "Lv0_3": [1120],
            "Lv0_4": [1098],
            "CogO": json.dumps(
                [
                    "Player_ManLuck84",
                    "Player_ManWizard84",
                    "Player_WoManArch84",
                    "Player_Manix84_5",
                    "Player_Manix84",
                ]
            ),
        }
    )

    assert [character.name for character in account.characters] == [
        "Character 1 - Manix84",
        "Character 2 - ManWizard84",
        "Character 3 - WoManArch84",
        "Character 4 - ManLuck84",
        "Character 5 - Manix84_5",
    ]


def test_parser_normalizes_real_indexed_detail_values() -> None:
    """Test real indexed exports preserve AFK seconds and locked inventory slots."""
    account = parse_idleon_account(
        {
            "CharacterClass_0": 14,
            "CurrentMap_0": 325,
            "Lv0_0": [1103],
            "PTimeAway_0": 1782760.29,
            "MoneyBANK": 1000,
            "Money_0": 25,
            "GreenStacks": ["CraftMat1", "CraftMat2"],
            "Cards1": ["EquipmentHats1", "FoodHealth1"],
            "AchieveReg": [-1, 0, -1],
            "InventoryOrder_0": [
                "LockedInvSpace",
                "FoodHealth1",
                "Blank",
                "EquipmentHats1",
                "LockedInvSpace",
            ],
            "PVStatList_0": [10, 20, 30, 40, 1103],
            "EquipOrder_0": [
                {
                    "0": "EquipmentHats1",
                    "1": "EquipmentShirts1",
                    "2": "Blank",
                    "length": 3,
                },
                {"0": "EquipmentTools1", "1": "Blank", "length": 2},
                {"0": "FoodHealth1", "1": "Blank", "length": 2},
            ],
            "AttackLoadout_0": [[90, "Null"], [91]],
        }
    )

    character = account.characters[0]

    assert account.details["raw_money"] == 1025
    assert account.details["total_money"] == 1025
    assert account.details["money_breakdown"] == {
        "bank": 1000,
        "characters": 25,
    }
    assert account.details["green_stack_count"] == 2
    assert account.details["green_stack_sample"] == ["Thread", "Crimson String"]
    assert account.details["slab_items_obtained"] == 2
    assert account.details["achievements_completed"] == 2
    assert character.inventory_full is False
    assert character.needs_attention is False
    assert character.details["money"] == 25
    assert character.afk_hours == 495.21
    assert character.details["afk_seconds"] == 1782760.29
    assert "raw_afk_value" not in character.details
    assert character.details["inventory_slots_total"] == 5
    assert character.details["inventory_slots_usable"] == 3
    assert character.details["inventory_slots_used"] == 2
    assert character.details["inventory_slots_free"] == 1
    assert character.details["inventory_sample"] == ["Nomwich", "Farmer Brim"]
    assert character.details["stats"] == {
        "strength": 10,
        "agility": 20,
        "wisdom": 30,
        "luck": 40,
    }
    assert character.details["skill_levels"] == {"Character": 1103}
    assert character.details["total_skill_level"] == 0
    assert character.details["equipped_item_count"] == 2
    assert character.details["equipped_items"] == ["Farmer Brim", "Orange Tee"]
    assert character.details["equipped_tool_count"] == 1
    assert character.details["equipped_food_count"] == 1
    assert character.details["attack_loadout"] == ["90", "91"]


def test_parser_extracts_indexed_account_progress_groups() -> None:
    """Test indexed exports expose grouped account progress details."""
    account_options = [0] * 443
    account_options[99] = 86
    account_options[201] = 10
    account_options[242] = 14
    account_options[442] = 97

    account = parse_idleon_account(
        {
            "CharacterClass_0": 14,
            "Lv0_0": [1103],
            "CYWorldTeleports": 1700,
            "CYObolFragments": 31183,
            "CYColosseumTickets": 327,
            "CYSilverPens": 84579,
            "GemsOwned": 3469,
            "PVMinigamePlays_0": 21,
            "CYKeysAll": [2737, 14158, 27164, 13425, 542702],
            "ChestOrder": ["Timecandy1", "Timecandy2", "CraftMat1"],
            "ChestQuantity": [347, 86, 10],
            "Shrine": [
                [300, 0, -10, 27, 1, 0],
                [300, 0, 54, 27, 1, 0],
                [300, 0, 118, 26, 1, 0],
            ],
            "StatueLevels_0": [[284, 1], [292, 1], [272, 1]],
            "FamValColosseumHighscores": [
                0,
                400643.056,
                1349042.18,
                9163910.868,
                "7.999322637599999E7",
                "2.5077530872544438E7",
                "2.6685560833145946E8",
            ],
            "FamValMinigameHiscores": [93, 27, 23, 6],
            "OptLacc": account_options,
            "Gaming": [0] * 10 + [1471],
            "CauldronInfo": [
                {"0": 1000, "1": 10, "2": 20, "length": 3},
                {"0": 1000, "1": 30, "length": 2},
                {"length": 0},
                {"length": 0},
                {"0": 2, "1": 3, "length": 2},
                [],
                [12, 5],
            ],
            "CauldUpgLVs": [1, 2, 3, 4, 5, 6, 7, 8],
            "CauldUpgXPs": [10, 20, 30, 40, 50, 60, 70, 80],
            "CauldronP2W": [
                [1, 2, 3, 4, 5, 6],
                [7, 8, 9, 10],
                [11, 12],
                [13, 14],
                [100, 3, 50, 1],
                [2, 18],
            ],
            "serverVars": {
                "voteCategories": [1, 1, 3, 5],
                "votePercent": [42, 35, 23],
                "voteCat2": [2, 2, 4],
                "votePercent2": [60, 40],
            },
            "Refinery": [[], [], [100, 200, 300]],
            "Print": [0, "Fish1", 100, "Tree1", 200],
            "CYDeliveryBoxComplete": 2357,
            "AchieveReg": [-1, 0, 25, -1],
            "SteamAchieve": [-1, 100, 0],
            "TaskZZ0": [[5000, 40], [10]],
            "TaskZZ1": [[1, 2], [1]],
            "TaskZZ2": [[3, 5], [2]],
            "TaskZZ3": [[1, 0], [1]],
            "ForgeItemOrder": [
                "Copper",
                "OilBarrel1",
                "CopperBar",
                "Iron",
                "Blank",
                "IronBar",
            ],
            "ForgeItemQty": [100, 2, 30, 250, 0, 10],
            "ForgeLV": [16, 50, 12, 85, 75, 60],
            "BribeStatus": [1, 0],
            "StampLv": [{"0": 5, "length": 1}, {"0": 10, "length": 1}],
            "StampLvM": [{"0": 6, "length": 1}, {"0": 12, "length": 1}],
            "Cooking": [1, 0, 2],
            "Sailing": [1, 2],
            "Divinity": [1],
            "FarmCrop": [1, 2, 3],
            "Summon": [1, 0],
            "Holes": {"a": 1, "b": 0},
            "companions": {
                "l": [2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                "t": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            },
        }
    )

    assert account.details["currencies"]["World Teleports"] == 1700
    assert account.details["currencies"]["Candys"] == 433
    assert account.details["currencies"]["Kruk's Volcano Keys"] == 542702
    assert account.details["shrine_levels"]["Woodular Shrine"] == 27
    assert account.details["statue_levels"]["Power"] == 284
    assert account.details["colosseum_scores"]["Whimsical"] == 266855608.33
    assert account.details["minigame_scores"] == {
        "Poing": 1471,
        "Darts": 97,
        "Chopping": 93,
        "Pen pals": 86,
        "Fishing": 27,
        "Catching": 23,
        "Hoops": 14,
        "Spiketrap": 10,
        "Mining": 6,
    }
    assert account.details["progress_totals"]["Bubbles"] == 60
    assert account.details["progress_totals"]["Stamps"] == 15
    assert account.details["progress_totals"]["Statues"] == 848
    assert account.details["progress_totals"]["Shrines"] == 80
    assert account.details["progress_totals"]["PO Orders"] == 2357
    assert account.details["progress_totals"]["Refined Salts"] == 600
    assert account.details["progress_totals"]["Mats Printed"] == 300
    assert account.details["pets"]["Legacy Pets"]["King Doot"] == "1/2"
    assert account.details["pets"]["Fallen Spirits"]["Ancient Golem"] == "1/1"
    assert account.details["achievement_status"]["World 1"]["achieved"] == 2
    assert 25 in account.details["achievement_status"]["World 1"]["progress"].values()
    assert account.details["achievement_status"]["Steam"]["achieved"] == 1
    assert account.details["task_levels"]["World 1"]["Faceless Deathmachine"] == {
        "level": "1/10",
        "progress_percent": 37.5,
    }
    assert (
        account.details["taskboard_merits"]["World 1"][
            "Inventory Bag  is applied to everyone,"
        ]
        == "3/5"
    )
    assert account.details["taskboard_unlocks"]["Tab 1"] == {
        "Unlock 1": "Achieved",
        "Unlock 2": "Unavailable",
    }
    assert account.details["world_1_anvil"]["slots"]["Slot 1"]["ore"] == {
        "type": "Copper Ore",
        "count": 100,
    }
    assert (
        account.details["world_1_anvil"]["upgrades"]["New Forge Slot"][
            "cost_for_next_level"
        ]
        == "Maxed"
    )
    assert (
        account.details["world_1_anvil"]["upgrades"]["Forge Speed"][
            "cost_for_next_level"
        ]
        == "Unknown"
    )
    assert account.details["world_1_bribes"]["Insider Trading"]["price"] == "Purchased"
    assert account.details["world_1_bribes"]["Tracking Chips"]["price"] == 1800
    assert (
        account.details["world_1_stamps"]["Combat"]["Sword Stamp"]["current_level"] == 5
    )
    assert (
        "Spore Cap"
        in account.details["world_1_stamps"]["Combat"]["Sword Stamp"][
            "cost_to_level_up"
        ]
    )
    assert account.details["world_summaries"]["World 2"]["Alchemy bubble levels"] == 60
    assert account.details["world_summaries"]["World 4"]["Cooking"] == 2
    assert account.details["world_summaries"]["World 7"]["Holes"] == 1
    assert account.details["world_2_cauldron"]["upgrades"]["Power"]["Speed"] == {
        "level": 1,
        "progress": 10,
    }
    assert account.details["world_2_cauldron"]["liquids"]["Water Drops"] == 12
    assert account.details["world_2_cauldron"]["pay_to_win"]["vials"] == {
        "Attempts": 11,
        "RNG": 12,
    }
    assert account.details["world_2_vials"]["COPPER CORONA"]["level"] == 2
    assert account.details["world_2_sigils"]["BIG MUSCLE"]["state"] == "Ethereal"
    assert (
        account.details["world_2_vote_ballots"]["Bonus Ballot"]["selected_index"] == 1
    )
    assert account.details["killroy"]["rooms_available"] == 2


def test_parser_uses_packaged_item_label_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test core item labels work without ignored websiteData files."""
    from custom_components.idleon.idleon_data import parser

    def _raise_missing_website_data(key: str) -> None:
        raise WebsiteDataNotFoundError(key)

    monkeypatch.setattr(
        parser,
        "load_default_website_data_part",
        _raise_missing_website_data,
    )

    account = parse_idleon_account(
        {
            "CharacterClass_0": 14,
            "CurrentMap_0": 325,
            "Lv0_0": [1103],
            "InventoryOrder_0": ["FoodHealth1", "EquipmentHats1"],
            "InvBagsUsed_0": ["InvBag1", "InvBag100"],
        }
    )

    character = account.characters[0]

    assert character.details["inventory_sample"] == ["Nomwich", "Farmer Brim"]
    assert character.details["inventory_bags"] == [
        "Inventory Bag A",
        "Snakeskinventory Bag",
    ]


def test_parser_treats_inventory_as_full_when_all_usable_slots_are_occupied() -> None:
    """Test locked inventory slots do not prevent full usable inventory detection."""
    account = parse_idleon_account(
        {
            "CharacterClass_0": 14,
            "CurrentMap_0": 325,
            "Lv0_0": [1103],
            "InventoryOrder_0": [
                "LockedInvSpace",
                "FoodHealth1",
                "EquipmentHats1",
                "LockedInvSpace",
            ],
        }
    )

    character = account.characters[0]

    assert character.inventory_full is True
    assert character.needs_attention is True
    assert character.details["inventory_slots_total"] == 4
    assert character.details["inventory_slots_usable"] == 2
    assert character.details["inventory_slots_used"] == 2
    assert character.details["inventory_slots_free"] == 0


def test_parser_cleans_indexed_max_carry_capacity_categories() -> None:
    """Test raw carry capacity categories are compact and readable."""
    account = parse_idleon_account(
        {
            "CharacterClass_0": 14,
            "CurrentMap_0": 325,
            "Lv0_0": [1103],
            "MaxCarryCap_0": {
                "Mining": 10,
                "fillerz": 10,
                "bCraft": 100,
                "Foods": "25",
                "Invalid": "not-a-number",
            },
        }
    )

    assert account.characters[0].details["max_carry_capacity"] == {
        "Mining": 10,
        "Materials": 100,
        "Foods": "25",
    }


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
    assert first_character.name == "Character 1 - Alpha Archer"
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
    assert second_character.name == "Character 2 - Beta Mage"
    assert second_character.level == 202
    assert second_character.character_class == "Elemental Sorcerer"
    assert second_character.inventory_full is False
    assert second_character.needs_attention is False
