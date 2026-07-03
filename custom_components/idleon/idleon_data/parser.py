"""Flexible parser for early Idleon account JSON exports."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from ..models import IdleonAccount, IdleonCharacter
from .exceptions import IdleonInvalidSchema
from .game_maps import afk_activity_label, class_name_label, map_name_label
from .website_data import WebsiteDataNotFoundError, load_default_website_data_part

DETAIL_SAMPLE_LIMIT = 12
EMPTY_INVENTORY_SLOT_VALUES = {
    "",
    "0",
    "blank",
    "empty",
    "filler",
    "lockedinvspace",
    "none",
    "null",
}
MAX_CARRY_CAPACITY_IGNORED_KEYS = {"fillerz"}
MAX_CARRY_CAPACITY_LABELS = {
    "bCraft": "Materials",
}
FALLBACK_WEBSITE_LABELS = {
    "invBags": {
        "InvBag1": "Inventory Bag A",
        "InvBag100": "Snakeskinventory Bag",
    },
    "items": {
        "EquipmentHats1": "Farmer Brim",
        "EquipmentShirts1": "Orange Tee",
        "EquipmentTools1": "Copper Pickaxe",
        "FoodHealth1": "Nomwich",
    },
}
SKILL_LEVEL_LABELS = (
    "Character",
    "Mining",
    "Smithing",
    "Chopping",
    "Fishing",
    "Alchemy",
    "Catching",
    "Trapping",
    "Construction",
    "Worship",
    "Cooking",
    "Laboratory",
    "Breeding",
    "Sailing",
    "Gaming",
    "Divinity",
    "Sneaking",
    "Summoning",
)
CURRENCY_KEY_LABELS = (
    "Forest Villa Keys",
    "Efaunt's Tomb Keys",
    "Chizoar's Cavern Keys",
    "Troll's Enclave Keys",
    "Kruk's Volcano Keys",
)
CURRENCY_FIELD_LABELS = {
    "CYWorldTeleports": "World Teleports",
    "CYObolFragments": "Obol Fragments",
    "CYColosseumTickets": "Colosseum Tickets",
    "CYSilverPens": "Silver Pens",
}
SHRINE_LEVEL_LABELS = (
    "Woodular Shrine",
    "Isaccian Shrine",
    "Crystal Shrine",
    "Pantheon Shrine",
    "Clover Shrine",
    "Summereading Shrine",
    "Crescent Shrine",
    "Undead Shrine",
    "Primordial Shrine",
)
STATUE_LEVEL_LABELS = (
    "Power",
    "Speed",
    "Mining",
    "Feasty",
    "Health",
    "Kachow",
    "Lumberbob",
    "Thicc Skin",
    "Oceanman",
    "Ol Reliable",
    "Exp Book",
    "Anvil",
    "Cauldron",
    "Beholder",
    "Bullseye",
    "Box",
    "Twosoul",
    "EhExPee",
    "Seesaw",
    "Pecunia",
    "Mutton",
    "Egg",
    "Battleaxe",
    "Spiral",
    "Boat",
    "Compost",
    "Stealth",
    "Essence",
    "Villager",
    "Dragon Warrior",
    "Spelunky",
    "Reef Coral",
)
COLOSSEUM_SCORE_INDEXES = {
    "Whimsical": 6,
    "Astro": 4,
    "Molten": 5,
    "Chillsnap": 3,
    "Sandstone": 2,
    "Dewdrop": 1,
}
MINIGAME_SCORE_INDEXES = {
    "Chopping": 0,
    "Fishing": 1,
    "Catching": 2,
    "Mining": 3,
}
ACCOUNT_OPTION_SCORE_INDEXES = {
    "Pen pals": 99,
    "Hoops": 242,
    "Spiketrap": 201,
    "Darts": 442,
}


def parse_idleon_account(raw_data: Any) -> IdleonAccount:
    """Parse raw JSON into a normalized Idleon account model."""
    if not isinstance(raw_data, Mapping):
        raise IdleonInvalidSchema("Top-level Idleon data must be an object")

    if _looks_like_indexed_export(raw_data):
        return _parse_indexed_export(raw_data)

    account_data = (
        _first_mapping(raw_data, ("account", "profile", "player")) or raw_data
    )
    characters_raw = _first_value(
        account_data,
        ("characters", "chars", "players"),
    ) or _first_value(raw_data, ("characters", "chars", "players"))

    character_items = _normalize_characters(characters_raw)
    if not character_items:
        raise IdleonInvalidSchema("Idleon data must contain at least one character")

    characters = tuple(
        _parse_character(index, character_id, character_data)
        for index, (character_id, character_data) in enumerate(character_items)
    )

    explicit_total_level = _first_int(
        account_data,
        ("total_level", "totalLevel", "account_level", "accountLevel"),
    )
    total_level = explicit_total_level
    if total_level is None:
        total_level = sum(character.level for character in characters)

    account_id = str(
        _first_value(account_data, ("account_id", "accountId", "id", "player_id"))
        or "idleon_account"
    )
    account_name = str(
        _first_value(account_data, ("name", "account_name", "accountName"))
        or "Legends of Idleon Account"
    )

    return IdleonAccount(
        account_id=account_id,
        name=account_name,
        total_level=total_level,
        gems=_first_int(account_data, ("gems", "gem_count", "gemCount")) or 0,
        characters=characters,
        source_updated_at=_parse_datetime(
            _first_value(
                account_data,
                ("last_updated", "lastUpdated", "updated_at", "updatedAt"),
            )
        ),
        details=_account_details(account_data, characters),
    )


def _looks_like_indexed_export(raw_data: Mapping[str, Any]) -> bool:
    """Return whether data looks like an indexed raw Idleon export."""
    fields = _indexed_export_fields(raw_data)
    return any(
        key.startswith(("CharacterClass_", "PVStatList_", "Lv0_", "CurrentMap_"))
        for key in fields
    )


def _parse_indexed_export(raw_data: Mapping[str, Any]) -> IdleonAccount:
    """Parse indexed raw Idleon export data."""
    fields = _indexed_export_fields(raw_data)
    character_indexes = _indexed_character_ids(fields)
    if not character_indexes:
        raise IdleonInvalidSchema("Indexed Idleon data must contain characters")
    character_names = _indexed_character_names(raw_data, fields, character_indexes)

    characters = tuple(
        _parse_indexed_character(fields, character_index, character_names)
        for character_index in character_indexes
    )

    source_updated_at = _parse_indexed_source_updated_at(fields)

    return IdleonAccount(
        account_id="idleon_account",
        name="Legends of Idleon Account",
        total_level=sum(character.level for character in characters),
        gems=_coerce_int(fields.get("GemsOwned")) or 0,
        characters=characters,
        source_updated_at=source_updated_at,
        details=_indexed_account_details(fields, characters),
    )


def _indexed_export_fields(raw_data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the field mapping from flat or wrapped Idleon exports."""
    save_data = raw_data.get("saveData")
    if isinstance(save_data, Mapping):
        return save_data
    return raw_data


def _indexed_character_names(
    raw_data: Mapping[str, Any],
    fields: Mapping[str, Any],
    character_indexes: tuple[int, ...],
) -> Mapping[int, str]:
    """Return character names from wrapped or flat Idleon exports."""
    char_name_data = raw_data.get("charNameData")
    if isinstance(char_name_data, Iterable) and not isinstance(
        char_name_data,
        str | bytes,
    ):
        return {
            index: str(name).strip()
            for index, name in enumerate(char_name_data)
            if str(name).strip()
        }

    return _indexed_character_names_from_cog_order(fields, character_indexes)


def _indexed_character_names_from_cog_order(
    raw_data: Mapping[str, Any],
    character_indexes: tuple[int, ...],
) -> Mapping[int, str]:
    """Return likely character names from CogO placement data."""
    names = _player_names_from_cog_order(raw_data)
    if not names:
        return {}

    mapped: dict[int, str] = {}
    remaining: list[str] = []
    for name in names:
        suffix_index = _name_suffix_character_index(name)
        if suffix_index is not None and suffix_index in character_indexes:
            mapped.setdefault(suffix_index, name)
        else:
            remaining.append(name)

    _map_primary_character_name(mapped, remaining)
    _map_class_hinted_character_names(raw_data, character_indexes, mapped, remaining)
    return mapped


def _player_names_from_cog_order(raw_data: Mapping[str, Any]) -> tuple[str, ...]:
    """Return unique player names found in CogO data in first-seen order."""
    cog_order = _maybe_json(raw_data.get("CogO"))
    if not isinstance(cog_order, Iterable) or isinstance(cog_order, str | bytes):
        return ()

    names: list[str] = []
    for value in cog_order:
        if not isinstance(value, str) or not value.startswith("Player_"):
            continue
        name = value.removeprefix("Player_").strip()
        if name and name not in names:
            names.append(name)
    return tuple(names)


def _name_suffix_character_index(name: str) -> int | None:
    """Return a zero-based character index from a trailing name suffix."""
    match = re.search(r"_(\d+)$", name)
    if not match:
        return None
    suffix = _coerce_int(match.group(1))
    if suffix is None or suffix <= 0:
        return None
    return suffix - 1


def _map_primary_character_name(
    mapped: dict[int, str],
    remaining: list[str],
) -> None:
    """Map an unsuffixed main name to character 0 when suffixes reveal a base."""
    if 0 in mapped:
        return

    suffixed_bases = {
        re.sub(r"_\d+$", "", name)
        for name in mapped.values()
        if re.search(r"_\d+$", name)
    }
    for name in tuple(remaining):
        if name in suffixed_bases:
            mapped[0] = name
            remaining.remove(name)
            return


def _map_class_hinted_character_names(
    raw_data: Mapping[str, Any],
    character_indexes: tuple[int, ...],
    mapped: dict[int, str],
    remaining: list[str],
) -> None:
    """Map remaining names when their text clearly hints at a class family."""
    for name in tuple(remaining):
        hinted_index = _class_hint_index_for_name(
            name,
            raw_data,
            character_indexes,
            mapped,
        )
        if hinted_index is not None:
            mapped[hinted_index] = name
            remaining.remove(name)


def _class_hint_index_for_name(
    name: str,
    raw_data: Mapping[str, Any],
    character_indexes: tuple[int, ...],
    mapped: Mapping[int, str],
) -> int | None:
    """Return a likely index when a name clearly identifies a class family."""
    name_tokens = name.lower()
    for index in character_indexes:
        if index in mapped:
            continue
        class_name = _class_name(raw_data.get(f"CharacterClass_{index}")).lower()
        if _name_matches_class_hint(name_tokens, class_name):
            return index
    return None


def _name_matches_class_hint(name: str, class_name: str) -> bool:
    """Return whether a character name hints at a parsed class name."""
    hint_groups = (
        (
            ("wizard", "mage", "sorc"),
            ("wizard", "mage", "sorcerer", "shaman", "conjuror", "cultist"),
        ),
        (
            ("arch", "bow", "hunter"),
            ("archer", "bowman", "hunter", "siege", "breaker", "beast", "sniper"),
        ),
        (
            ("luck", "luk", "journey"),
            ("journeyman", "maestro", "voidwalker", "wind walker", "walker"),
        ),
    )
    return any(
        any(token in name for token in name_hints)
        and any(token in class_name for token in class_hints)
        for name_hints, class_hints in hint_groups
    )


def _indexed_character_ids(raw_data: Mapping[str, Any]) -> tuple[int, ...]:
    """Return sorted character indexes from raw export fields."""
    indexes: set[int] = set()
    for key in raw_data:
        for prefix in (
            "CharacterClass_",
            "PVStatList_",
            "Lv0_",
            "CurrentMap_",
            "AFKtarget_",
        ):
            if key.startswith(prefix):
                with suppress(ValueError):
                    indexes.add(int(key.removeprefix(prefix)))
    return tuple(sorted(indexes))


def _parse_indexed_character(
    raw_data: Mapping[str, Any],
    character_index: int,
    character_names: Mapping[int, str] | None = None,
) -> IdleonCharacter:
    """Parse one indexed raw export character."""
    level = _indexed_character_level(raw_data, character_index)
    class_value = raw_data.get(f"CharacterClass_{character_index}")
    current_map = raw_data.get(f"CurrentMap_{character_index}")
    afk_target = raw_data.get(f"AFKtarget_{character_index}")
    raw_afk_seconds = _coerce_float(raw_data.get(f"PTimeAway_{character_index}")) or 0.0
    afk_seconds = _normalized_afk_seconds(raw_afk_seconds)
    inventory_full = _indexed_inventory_full(raw_data, character_index)
    character_name = _indexed_character_name(character_index, character_names)
    details = _indexed_character_details(
        raw_data,
        character_index,
        class_value=class_value,
        current_map=current_map,
        afk_target=afk_target,
        afk_seconds=afk_seconds,
        raw_afk_value=raw_afk_seconds,
    )

    return IdleonCharacter(
        character_id=f"character_{character_index}",
        name=character_name,
        level=level or 0,
        character_class=_class_name(class_value),
        current_map=_map_name(current_map),
        current_activity=_afk_activity(afk_target),
        afk_hours=round(afk_seconds / 3600, 2),
        inventory_full=inventory_full,
        needs_attention=inventory_full,
        details=details,
    )


def _indexed_character_level(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> int | None:
    """Return character level from raw Idleon character stats."""
    stat_data = _maybe_json(raw_data.get(f"PVStatList_{character_index}"))
    if isinstance(stat_data, list) and len(stat_data) > 4:
        level = _coerce_int(stat_data[4])
        if level is not None:
            return level

    skill_level_data = _maybe_json(raw_data.get(f"Lv0_{character_index}"))
    if isinstance(skill_level_data, list) and skill_level_data:
        return _coerce_int(skill_level_data[0])

    return None


def _indexed_character_name(
    character_index: int,
    character_names: Mapping[int, str] | None,
) -> str:
    """Return character name from export metadata or a stable fallback."""
    fallback = f"Character {character_index + 1}"
    if not character_names:
        return fallback

    name = character_names.get(character_index, "").strip()
    if not name:
        return fallback
    return f"{fallback} - {name}"


def _indexed_inventory_full(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> bool:
    """Return whether a character's inventory appears full."""
    inventory = _maybe_json(raw_data.get(f"InventoryOrder_{character_index}"))
    if not isinstance(inventory, list) or not inventory:
        return False
    usable_slots = [slot for slot in inventory if not _inventory_slot_is_locked(slot)]
    return bool(usable_slots) and all(
        _inventory_slot_has_item(slot) for slot in usable_slots
    )


def _indexed_character_details(
    raw_data: Mapping[str, Any],
    character_index: int,
    *,
    class_value: Any,
    current_map: Any,
    afk_target: Any,
    afk_seconds: float,
    raw_afk_value: float,
) -> dict[str, Any]:
    """Return compact detailed attributes for an indexed character."""
    details: dict[str, Any] = {
        "raw_class_id": class_value,
        "raw_map_id": current_map,
        "afk_target": afk_target,
        "afk_seconds": round(afk_seconds, 2),
    }
    character_money = _coerce_float(raw_data.get(f"Money_{character_index}"))
    if character_money is not None:
        details["money"] = _compact_number(character_money)
    if raw_afk_value != afk_seconds:
        details["raw_afk_value"] = round(raw_afk_value, 2)
    details.update(_indexed_stat_details(raw_data, character_index))
    details.update(_indexed_skill_level_details(raw_data, character_index))
    details.update(_indexed_inventory_details(raw_data, character_index))
    details.update(_indexed_inventory_bag_details(raw_data, character_index))
    details.update(_indexed_max_carry_capacity_details(raw_data, character_index))
    details.update(_indexed_loadout_details(raw_data, character_index))
    return _remove_empty_detail_values(details)


def _indexed_stat_details(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> dict[str, Any]:
    """Return compact primary stat attributes for an indexed character."""
    stat_data = _maybe_json(raw_data.get(f"PVStatList_{character_index}"))
    if not isinstance(stat_data, list):
        return {}

    labels = ("strength", "agility", "wisdom", "luck")
    stats = {
        label: stat_value
        for label, value in zip(labels, stat_data, strict=False)
        if (stat_value := _coerce_int(value)) is not None
    }
    if not stats:
        return {}
    return {"stats": stats}


def _indexed_skill_level_details(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> dict[str, Any]:
    """Return compact skill level attributes for an indexed character."""
    skill_data = _maybe_json(raw_data.get(f"Lv0_{character_index}"))
    if not isinstance(skill_data, list):
        return {}

    skill_levels = {
        _skill_level_label(index): level
        for index, value in enumerate(skill_data)
        if (level := _coerce_int(value)) is not None and level >= 0
    }
    if not skill_levels:
        return {}

    non_character_levels = {
        skill: level for skill, level in skill_levels.items() if skill != "Character"
    }
    highest_skill = None
    if non_character_levels:
        skill_name, skill_level = max(
            non_character_levels.items(),
            key=lambda item: item[1],
        )
        highest_skill = {
            "name": skill_name,
            "level": skill_level,
        }

    details: dict[str, Any] = {
        "skill_levels": skill_levels,
        "total_skill_level": sum(non_character_levels.values()),
    }
    if highest_skill:
        details["highest_skill"] = highest_skill
    return details


def _skill_level_label(index: int) -> str:
    """Return a readable skill label for an Lv0 index."""
    if index < len(SKILL_LEVEL_LABELS):
        return SKILL_LEVEL_LABELS[index]
    return f"Skill {index}"


def _indexed_inventory_details(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> dict[str, Any]:
    """Return compact inventory slot attributes for an indexed character."""
    inventory = _maybe_json(raw_data.get(f"InventoryOrder_{character_index}"))
    if not isinstance(inventory, list):
        return {}

    total_slots = len(inventory)
    usable_slots = sum(1 for item in inventory if not _inventory_slot_is_locked(item))
    used_items = [item for item in inventory if _inventory_slot_has_item(item)]
    used_slots = len(used_items)
    return {
        "inventory_slots_total": total_slots,
        "inventory_slots_usable": usable_slots,
        "inventory_slots_used": used_slots,
        "inventory_slots_free": max(usable_slots - used_slots, 0),
        "inventory_sample": _limited_labels(used_items),
    }


def _indexed_inventory_bag_details(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> dict[str, Any]:
    """Return compact inventory bag attributes for an indexed character."""
    inventory_bags = _maybe_json(raw_data.get(f"InvBagsUsed_{character_index}"))
    if not isinstance(inventory_bags, list):
        return {}

    used_bags = [bag for bag in inventory_bags if _inventory_slot_has_item(bag)]
    return {
        "inventory_bag_count": len(used_bags),
        "inventory_bags": _limited_labels(used_bags, website_data_key="invBags"),
    }


def _indexed_max_carry_capacity_details(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> dict[str, Any]:
    """Return compact max carry capacity attributes for an indexed character."""
    max_carry_capacity = _maybe_json(raw_data.get(f"MaxCarryCap_{character_index}"))
    if not isinstance(max_carry_capacity, Mapping):
        return {}

    normalized_capacity = {
        _max_carry_capacity_label(key): value
        for key, value in max_carry_capacity.items()
        if (
            isinstance(key, str)
            and key not in MAX_CARRY_CAPACITY_IGNORED_KEYS
            and _coerce_int(value) is not None
        )
    }
    if not normalized_capacity:
        return {}

    return {
        "max_carry_capacity": normalized_capacity,
    }


def _max_carry_capacity_label(key: str) -> str:
    """Return a Home Assistant friendly carry capacity category label."""
    return MAX_CARRY_CAPACITY_LABELS.get(key, key)


def _indexed_loadout_details(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> dict[str, Any]:
    """Return compact equipment and loadout attributes for an indexed character."""
    details: dict[str, Any] = {}
    equipment = _maybe_json(raw_data.get(f"EquipOrder_{character_index}"))
    if isinstance(equipment, list):
        equipment_labels = _equipment_group_labels(equipment, 0)
        tool_labels = _equipment_group_labels(equipment, 1)
        food_labels = _equipment_group_labels(equipment, 2)
        details.update(
            {
                "equipped_item_count": len(equipment_labels),
                "equipped_items": equipment_labels[:DETAIL_SAMPLE_LIMIT],
                "equipped_tool_count": len(tool_labels),
                "equipped_tools": tool_labels[:DETAIL_SAMPLE_LIMIT],
                "equipped_food_count": len(food_labels),
                "equipped_food": food_labels[:DETAIL_SAMPLE_LIMIT],
            }
        )

    attack_loadout = _attack_loadout_labels(raw_data, character_index)
    if attack_loadout:
        details["attack_loadout"] = attack_loadout[:DETAIL_SAMPLE_LIMIT]

    return details


def _indexed_account_details(
    raw_data: Mapping[str, Any],
    characters: tuple[IdleonCharacter, ...],
) -> dict[str, Any]:
    """Return compact account-wide attributes for indexed exports."""
    details = _computed_account_details(characters)

    bank_money = _coerce_float(raw_data.get("MoneyBANK")) or 0.0
    character_money = sum(
        _coerce_float(raw_data.get(f"Money_{index}")) or 0.0
        for index, _character in enumerate(characters)
    )
    raw_money = bank_money + character_money
    if raw_money:
        details["total_money"] = _compact_number(raw_money)
        details["raw_money"] = _compact_number(raw_money)
        details["money_breakdown"] = {
            "bank": _compact_number(bank_money),
            "characters": _compact_number(character_money),
        }

    green_stacks = _maybe_json(raw_data.get("GreenStacks"))
    if isinstance(green_stacks, list):
        details["green_stack_count"] = len(green_stacks)
        details["green_stack_sample"] = _limited_labels(green_stacks)

    looty_raw = _indexed_looty_raw(raw_data)
    if isinstance(looty_raw, list):
        details["slab_items_obtained"] = len(looty_raw)

    achievements = _maybe_json(raw_data.get("AchieveReg"))
    if isinstance(achievements, list):
        details["achievements_completed"] = sum(
            1 for value in achievements if value == -1
        )

    details.update(_indexed_account_progress_details(raw_data, characters))

    return _remove_empty_detail_values(details)


def _indexed_account_progress_details(
    raw_data: Mapping[str, Any],
    characters: tuple[IdleonCharacter, ...],
) -> dict[str, Any]:
    """Return grouped account progression details for indexed exports."""
    details: dict[str, Any] = {}

    currencies = _indexed_currencies(raw_data, characters)
    if currencies:
        details["currencies"] = currencies

    shrine_levels = _indexed_shrine_levels(raw_data)
    if shrine_levels:
        details["shrine_levels"] = shrine_levels

    statue_levels = _indexed_statue_levels(raw_data)
    if statue_levels:
        details["statue_levels"] = statue_levels

    colosseum_scores = _indexed_colosseum_scores(raw_data)
    if colosseum_scores:
        details["colosseum_scores"] = colosseum_scores

    minigame_scores = _indexed_minigame_scores(raw_data)
    if minigame_scores:
        details["minigame_scores"] = minigame_scores

    progress_totals = _indexed_progress_totals(
        raw_data,
        shrine_levels=shrine_levels,
        statue_levels=statue_levels,
    )
    if progress_totals:
        details["progress_totals"] = progress_totals

    return details


def _indexed_currencies(
    raw_data: Mapping[str, Any],
    characters: tuple[IdleonCharacter, ...],
) -> dict[str, Any]:
    """Return named account currency values from indexed exports."""
    currencies = {
        label: _compact_number(value)
        for raw_key, label in CURRENCY_FIELD_LABELS.items()
        if (value := _coerce_float(raw_data.get(raw_key))) is not None
    }

    gems = _coerce_float(raw_data.get("GemsOwned"))
    if gems is not None:
        currencies["Gems"] = _compact_number(gems)

    minigame_plays = [
        _coerce_float(raw_data.get(f"PVMinigamePlays_{index}"))
        for index, _character in enumerate(characters)
    ]
    minigame_plays = [value for value in minigame_plays if value is not None]
    if minigame_plays:
        currencies["Mini-Game Plays remaining"] = _compact_number(max(minigame_plays))

    keys_all = _maybe_json(raw_data.get("CYKeysAll"))
    if isinstance(keys_all, list):
        for index, label in enumerate(CURRENCY_KEY_LABELS):
            value = _coerce_float(_list_value(keys_all, index))
            if value is not None:
                currencies[label] = _compact_number(value)

    candy_total = _storage_item_prefix_total(raw_data, "Timecandy")
    if candy_total:
        currencies["Candys"] = _compact_number(candy_total)

    return currencies


def _indexed_shrine_levels(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return named shrine levels from indexed exports."""
    shrines = _maybe_json(raw_data.get("ShrineInfo")) or _maybe_json(
        raw_data.get("Shrine")
    )
    if not isinstance(shrines, list):
        return {}

    levels: dict[str, Any] = {}
    for index, label in enumerate(SHRINE_LEVEL_LABELS):
        shrine = _list_value(shrines, index)
        if not isinstance(shrine, list):
            continue
        value = _coerce_float(_list_value(shrine, 3))
        if value is not None:
            levels[label] = _compact_number(value)
    return levels


def _indexed_statue_levels(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return named account-wide statue levels from indexed exports."""
    statue_data = _maybe_json(raw_data.get("StatueLevels_0"))
    if not isinstance(statue_data, list):
        for key, value in raw_data.items():
            if key.startswith("StatueLevels_"):
                statue_data = _maybe_json(value)
                if isinstance(statue_data, list):
                    break
    if not isinstance(statue_data, list):
        return {}

    levels: dict[str, Any] = {}
    for index, label in enumerate(STATUE_LEVEL_LABELS):
        statue = _list_value(statue_data, index)
        if not isinstance(statue, list):
            continue
        value = _coerce_float(_list_value(statue, 0))
        if value is not None:
            levels[label] = _compact_number(value)
    return levels


def _indexed_colosseum_scores(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return named colosseum high scores from indexed exports."""
    scores = _maybe_json(raw_data.get("FamValColosseumHighscores"))
    if not isinstance(scores, list):
        family_values = _maybe_json(raw_data.get("FamilyValuesMap"))
        if isinstance(family_values, Mapping):
            scores = _maybe_json(family_values.get("ColosseumHighscores"))
    if not isinstance(scores, list):
        return {}

    return {
        label: _compact_number(value)
        for label, index in COLOSSEUM_SCORE_INDEXES.items()
        if (value := _coerce_float(_list_value(scores, index))) is not None
    }


def _indexed_minigame_scores(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return named minigame high scores from indexed exports."""
    raw_scores = _maybe_json(raw_data.get("FamValMinigameHiscores"))
    if not isinstance(raw_scores, list):
        family_values = _maybe_json(raw_data.get("FamilyValuesMap"))
        if isinstance(family_values, Mapping):
            raw_scores = _maybe_json(family_values.get("MinigameHiscores"))
    scores: dict[str, Any] = {}
    if isinstance(raw_scores, list):
        scores.update(
            {
                label: _compact_number(value)
                for label, index in MINIGAME_SCORE_INDEXES.items()
                if (value := _coerce_float(_list_value(raw_scores, index))) is not None
            }
        )

    account_options = _maybe_json(raw_data.get("accountOptions")) or _maybe_json(
        raw_data.get("OptLacc")
    )
    if isinstance(account_options, list):
        for label, index in ACCOUNT_OPTION_SCORE_INDEXES.items():
            value = _coerce_float(_list_value(account_options, index))
            if value is not None:
                scores[label] = _compact_number(value)

    gaming = _maybe_json(raw_data.get("Gaming"))
    if isinstance(gaming, list):
        poing_score = _coerce_float(_list_value(gaming, 10))
        if poing_score is not None:
            scores["Poing"] = _compact_number(poing_score)

    ordered_labels = (
        "Poing",
        "Darts",
        "Chopping",
        "Pen pals",
        "Fishing",
        "Catching",
        "Hoops",
        "Spiketrap",
        "Mining",
    )
    return {label: scores[label] for label in ordered_labels if label in scores}


def _indexed_progress_totals(
    raw_data: Mapping[str, Any],
    *,
    shrine_levels: Mapping[str, Any],
    statue_levels: Mapping[str, Any],
) -> dict[str, Any]:
    """Return compact account progress totals from indexed exports."""
    totals: dict[str, Any] = {}

    bubbles = _cauldron_bubble_total(raw_data)
    if bubbles:
        totals["Bubbles"] = _compact_number(bubbles)

    stamp_total = _stamp_level_total(raw_data)
    if stamp_total:
        totals["Stamps"] = _compact_number(stamp_total)

    if statue_levels:
        totals["Statues"] = _compact_number(_sum_mapping_numbers(statue_levels))
    if shrine_levels:
        totals["Shrines"] = _compact_number(_sum_mapping_numbers(shrine_levels))

    po_orders = _coerce_float(raw_data.get("CYDeliveryBoxComplete"))
    if po_orders is not None:
        totals["PO Orders"] = _compact_number(po_orders)

    refined_salts = _refined_salt_total(raw_data)
    if refined_salts:
        totals["Refined Salts"] = _compact_number(refined_salts)

    mats_printed = _printer_total(raw_data)
    if mats_printed:
        totals["Mats Printed"] = _compact_number(mats_printed)

    return totals


def _indexed_looty_raw(raw_data: Mapping[str, Any]) -> Any:
    """Return raw slab/looty item list from known export shapes."""
    cards = _maybe_json(raw_data.get("Cards"))
    if isinstance(cards, list) and len(cards) > 1:
        return cards[1]
    return _maybe_json(raw_data.get("Cards1"))


def _equipment_group_labels(
    equipment: list[Any],
    group_index: int,
) -> list[str]:
    """Return display labels for one EquipOrder group."""
    if group_index >= len(equipment):
        return []
    group = equipment[group_index]
    if not isinstance(group, Mapping):
        return []

    labels: list[str] = []
    for key, value in sorted(group.items(), key=lambda item: _slot_sort_key(item[0])):
        if key == "length" or not _inventory_slot_has_item(value):
            continue
        labels.append(_display_label(value, website_data_key="items"))
    return labels


def _slot_sort_key(value: Any) -> int:
    """Return a numeric sort key for indexed object slots."""
    return _coerce_int(value) or 0


def _attack_loadout_labels(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> list[str]:
    """Return labels for assigned attack loadout talents."""
    attack_loadout = _maybe_json(raw_data.get(f"AttackLoadout_{character_index}"))
    if not isinstance(attack_loadout, Iterable) or isinstance(
        attack_loadout,
        str | bytes,
    ):
        return []

    labels: list[str] = []
    for page in attack_loadout:
        if not isinstance(page, Iterable) or isinstance(page, str | bytes):
            continue
        for talent_id in page:
            if not _inventory_slot_has_item(talent_id):
                continue
            label = _talent_label(talent_id)
            if label not in labels:
                labels.append(label)
    return labels


def _talent_label(value: Any) -> str:
    """Return a readable talent label for an attack loadout value."""
    raw_value = str(value)
    with suppress(WebsiteDataNotFoundError):
        talents = load_default_website_data_part("talents")
        if isinstance(talents, Mapping):
            for talent_group in talents.values():
                if not isinstance(talent_group, Mapping):
                    continue
                for talent in talent_group.values():
                    if not isinstance(talent, Mapping):
                        continue
                    if str(talent.get("talentId")) != raw_value:
                        continue
                    talent_name = talent.get("name")
                    if isinstance(talent_name, str) and talent_name:
                        return _clean_display_text(talent_name)
    return _clean_display_text(raw_value)


def _inventory_slot_has_item(value: Any) -> bool:
    """Return whether an inventory slot value looks occupied."""
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized not in EMPTY_INVENTORY_SLOT_VALUES
    return bool(value)


def _inventory_slot_is_locked(value: Any) -> bool:
    """Return whether an inventory slot is not currently usable."""
    return isinstance(value, str) and value.strip().lower() == "lockedinvspace"


def _normalized_afk_seconds(value: float) -> float:
    """Return AFK time normalized to seconds from known export units."""
    return value


def _parse_indexed_source_updated_at(raw_data: Mapping[str, Any]) -> datetime | None:
    """Parse source update time from raw export time fields."""
    time_away = _maybe_json(raw_data.get("TimeAway"))
    if isinstance(time_away, Mapping):
        return _parse_datetime(time_away.get("GlobalTime"))
    return None


def _parse_character(
    index: int,
    fallback_id: str | None,
    character_data: Mapping[str, Any],
) -> IdleonCharacter:
    """Parse a single character mapping."""
    name = str(
        _first_value(character_data, ("name", "character_name", "characterName"))
        or fallback_id
        or f"Character {index + 1}"
    )
    character_id = str(
        _first_value(character_data, ("id", "character_id", "characterId"))
        or fallback_id
        or _slugify(name)
        or f"character_{index + 1}"
    )

    inventory_full = _first_bool(
        character_data,
        ("inventory_full", "inventoryFull", "is_inventory_full", "isInventoryFull"),
    )
    needs_attention = _first_bool(
        character_data,
        ("needs_attention", "needsAttention", "requires_attention"),
    )

    if needs_attention is None:
        needs_attention = bool(inventory_full)

    details = _character_details(character_data)

    return IdleonCharacter(
        character_id=character_id,
        name=name,
        level=_first_int(character_data, ("level", "lvl")) or 0,
        character_class=str(
            _first_value(character_data, ("class", "character_class", "className"))
            or "Unknown"
        ),
        current_map=str(
            _first_value(character_data, ("current_map", "currentMap", "map"))
            or "Unknown"
        ),
        current_activity=str(
            _first_value(
                character_data,
                ("current_activity", "currentActivity", "activity"),
            )
            or "Unknown"
        ),
        afk_hours=_first_float(character_data, ("afk_hours", "afkHours")) or 0.0,
        inventory_full=bool(inventory_full),
        needs_attention=needs_attention,
        details=details,
    )


def _character_details(character_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return compact detailed attributes for flexible character mappings."""
    details = _first_mapping(character_data, ("details", "attributes")) or {}
    parsed_details = dict(details)
    money = _first_float(character_data, ("money", "coins", "raw_money", "rawMoney"))
    if money is not None:
        parsed_details["money"] = _compact_number(money)
    inventory = _first_value(character_data, ("inventory", "inventory_order"))
    if isinstance(inventory, list):
        usable_slots = sum(
            1 for item in inventory if not _inventory_slot_is_locked(item)
        )
        used_items = [item for item in inventory if _inventory_slot_has_item(item)]
        parsed_details.update(
            {
                "inventory_slots_total": len(inventory),
                "inventory_slots_usable": usable_slots,
                "inventory_slots_used": len(used_items),
                "inventory_slots_free": max(usable_slots - len(used_items), 0),
                "inventory_sample": _limited_labels(used_items),
            }
        )
    return _remove_empty_detail_values(parsed_details)


def _account_details(
    account_data: Mapping[str, Any],
    characters: tuple[IdleonCharacter, ...],
) -> dict[str, Any]:
    """Return compact account-wide attributes for flexible mappings."""
    details = dict(_first_mapping(account_data, ("details", "attributes")) or {})
    details.update(_computed_account_details(characters))
    if "total_money" not in details and "raw_money" in details:
        details["total_money"] = details["raw_money"]
    for detail_key, aliases in (
        ("currencies", ("currencies", "currency")),
        ("shrine_levels", ("shrine_levels", "shrineLevels", "shrines")),
        ("statue_levels", ("statue_levels", "statueLevels", "statues")),
        ("colosseum_scores", ("colosseum_scores", "colosseumScores")),
        ("minigame_scores", ("minigame_scores", "minigameScores")),
        ("progress_totals", ("progress_totals", "progressTotals", "totals")),
    ):
        if detail_key not in details:
            value = _first_mapping(account_data, aliases)
            if value:
                details[detail_key] = dict(value)
    return _remove_empty_detail_values(details)


def _computed_account_details(
    characters: tuple[IdleonCharacter, ...],
) -> dict[str, Any]:
    """Return account details computed from parsed character models."""
    details: dict[str, Any] = {}
    if not characters:
        return details

    highest_level_character = max(characters, key=lambda character: character.level)
    details["highest_character_level"] = highest_level_character.level
    details["highest_level_character"] = highest_level_character.name

    total_skill_level = sum(
        _coerce_int(character.details.get("total_skill_level")) or 0
        for character in characters
    )
    if total_skill_level:
        details["total_skill_level"] = total_skill_level

    class_counts: dict[str, int] = {}
    for character in characters:
        class_counts[character.character_class] = (
            class_counts.get(character.character_class, 0) + 1
        )
    if class_counts:
        details["class_counts"] = dict(sorted(class_counts.items()))

    return details


def _normalize_characters(value: Any) -> list[tuple[str | None, Mapping[str, Any]]]:
    """Normalize list or mapping character collections."""
    if isinstance(value, Mapping):
        return [
            (str(character_id), character_data)
            for character_id, character_data in value.items()
            if isinstance(character_data, Mapping)
        ]

    if isinstance(value, Iterable) and not isinstance(value, str | bytes):
        return [
            (None, character_data)
            for character_data in value
            if isinstance(character_data, Mapping)
        ]

    return []


def _first_mapping(
    data: Mapping[str, Any],
    keys: tuple[str, ...],
) -> Mapping[str, Any] | None:
    """Return the first mapping value for any key."""
    value = _first_value(data, keys)
    if isinstance(value, Mapping):
        return value
    return None


def _first_value(data: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first present value for any key."""
    for key in keys:
        if key in data:
            return data[key]
    return None


def _first_int(data: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    """Return the first value coerced to an integer."""
    return _coerce_int(_first_value(data, keys))


def _first_float(data: Mapping[str, Any], keys: tuple[str, ...]) -> float | None:
    """Return the first value coerced to a float."""
    return _coerce_float(_first_value(data, keys))


def _coerce_int(value: Any) -> int | None:
    """Return a value coerced to an integer."""
    if value is None:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _coerce_float(value: Any) -> float | None:
    """Return a value coerced to a float."""
    if value is None:
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _compact_number(value: float) -> int | float:
    """Return an int when a float has no fractional value."""
    if value.is_integer():
        return int(value)
    return round(value, 2)


def _list_value(values: list[Any], index: int) -> Any:
    """Return a list value if the index exists."""
    if index < 0 or index >= len(values):
        return None
    return values[index]


def _sum_mapping_numbers(values: Mapping[str, Any]) -> float:
    """Return the sum of numeric mapping values."""
    return sum(
        number
        for value in values.values()
        if (number := _coerce_float(value)) is not None
    )


def _mapping_numeric_values(value: Any) -> Iterable[float]:
    """Yield numeric values from lists or indexed object maps."""
    parsed = _maybe_json(value)
    if isinstance(parsed, Mapping):
        iterable = parsed.items()
        for key, item_value in iterable:
            if key == "length":
                continue
            number = _coerce_float(item_value)
            if number is not None:
                yield number
    elif isinstance(parsed, list):
        for item_value in parsed:
            number = _coerce_float(item_value)
            if number is not None:
                yield number


def _storage_item_prefix_total(raw_data: Mapping[str, Any], prefix: str) -> float:
    """Return total storage quantity for item IDs that start with a prefix."""
    order = _maybe_json(raw_data.get("ChestOrder"))
    quantities = _maybe_json(raw_data.get("ChestQuantity"))
    if not isinstance(order, list) or not isinstance(quantities, list):
        return 0.0

    total = 0.0
    for index, item in enumerate(order):
        if not isinstance(item, str) or not item.startswith(prefix):
            continue
        total += _coerce_float(_list_value(quantities, index)) or 0.0
    return total


def _cauldron_bubble_total(raw_data: Mapping[str, Any]) -> float:
    """Return a rough total of alchemy bubble levels."""
    cauldron_info = _maybe_json(raw_data.get("CauldronInfo"))
    if not isinstance(cauldron_info, list):
        return 0.0

    total = 0.0
    for cauldron in cauldron_info[:4]:
        levels = list(_mapping_numeric_values(cauldron))
        if len(levels) > 1:
            total += sum(levels[1:])
    return total


def _stamp_level_total(raw_data: Mapping[str, Any]) -> float:
    """Return total stamp levels from raw stamp level groups."""
    stamp_levels = _maybe_json(raw_data.get("StampLv")) or _maybe_json(
        raw_data.get("StampLevel")
    )
    if not isinstance(stamp_levels, list):
        return 0.0
    return sum(sum(_mapping_numeric_values(group)) for group in stamp_levels)


def _refined_salt_total(raw_data: Mapping[str, Any]) -> float:
    """Return total stored refined salts from raw refinery data."""
    refinery = _maybe_json(raw_data.get("Refinery"))
    if not isinstance(refinery, list):
        return 0.0
    return sum(_mapping_numeric_values(_list_value(refinery, 2)))


def _printer_total(raw_data: Mapping[str, Any]) -> float:
    """Return total sampled material print amounts from raw printer data."""
    printer = _maybe_json(raw_data.get("Print")) or _maybe_json(raw_data.get("Printer"))
    if not isinstance(printer, list):
        return 0.0

    total = 0.0
    for value in printer:
        if isinstance(value, str) and not _looks_numeric(value):
            continue
        total += _coerce_float(value) or 0.0
    return total


def _looks_numeric(value: str) -> bool:
    """Return whether a string looks numeric."""
    return _coerce_float(value) is not None


def _first_bool(data: Mapping[str, Any], keys: tuple[str, ...]) -> bool | None:
    """Return the first value coerced to a boolean."""
    value = _first_value(data, keys)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return None


def _limited_labels(
    values: Iterable[Any],
    *,
    website_data_key: str = "items",
) -> list[str]:
    """Return a small display-label sample for raw item identifiers."""
    labels: list[str] = []
    for value in values:
        if len(labels) >= DETAIL_SAMPLE_LIMIT:
            break
        labels.append(_display_label(value, website_data_key=website_data_key))
    return labels


def _display_label(value: Any, *, website_data_key: str) -> str:
    """Return a normalized display label for a raw websiteData key."""
    raw_value = str(value)
    with suppress(WebsiteDataNotFoundError):
        data = load_default_website_data_part(website_data_key)
        if isinstance(data, Mapping):
            item = data.get(raw_value)
            if isinstance(item, Mapping):
                display_name = item.get("displayName")
                if isinstance(display_name, str) and display_name:
                    return _clean_display_text(display_name)
    fallback = FALLBACK_WEBSITE_LABELS.get(website_data_key, {}).get(raw_value)
    if fallback:
        return fallback
    return _clean_display_text(raw_value)


def _clean_display_text(value: str) -> str:
    """Return websiteData display text in a Home Assistant friendly form."""
    return value.replace("_", " ").strip()


def _remove_empty_detail_values(details: Mapping[str, Any]) -> dict[str, Any]:
    """Drop empty detail values so entity attributes stay compact."""
    return {
        str(key): value
        for key, value in details.items()
        if value not in (None, "", [], {})
    }


def _parse_json_string(value: str) -> Any:
    """Parse a JSON string field from raw Idleon exports."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _maybe_json(value: Any) -> Any:
    """Parse a JSON string value when needed."""
    if isinstance(value, str):
        parsed = _parse_json_string(value)
        if parsed is not None:
            return parsed
    return value


def _map_name(value: Any) -> str:
    """Return a display name for a raw Idleon map identifier."""
    return map_name_label(value)


def _afk_activity(value: Any) -> str:
    """Return a display activity for a raw Idleon AFK target."""
    return afk_activity_label(value)


def _class_name(value: Any) -> str:
    """Return an Idleon class name from a raw class identifier."""
    return class_name_label(value)


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a timestamp from common JSON representations."""
    if value is None:
        return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _slugify(value: str) -> str:
    """Create a stable simple identifier from a character name."""
    slug = "".join(
        character.lower() if character.isalnum() else "_" for character in value
    )
    return "_".join(part for part in slug.split("_") if part)
