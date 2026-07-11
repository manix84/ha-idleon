"""Flexible parser for early Idleon account JSON exports."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ..models import IdleonAccount, IdleonCharacter
from ..utils.number_format import idleon_raw_value, parse_idleon_decimal
from .equipment import (
    MAIN_EQUIPMENT_SLOTS,
    TOOL_EQUIPMENT_SLOTS,
    equipment_display_label,
)
from .exceptions import IdleonInvalidSchema
from .game_maps import afk_activity_label, class_name_label, map_name_label
from .website_data import WebsiteDataNotFoundError, load_default_website_data_part

DETAIL_SAMPLE_LIMIT = 12
EQUIPMENT_MAIN_GROUP_INDEX = 0
EQUIPMENT_TROPHY_SLOT = 10
EQUIPMENT_NAME_TAG_SLOT = 14
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
MAX_SAFE_INTEGER_FLOAT = 9_007_199_254_740_991
MAX_CARRY_CAPACITY_IGNORED_KEYS = {"fillerz"}
MAX_CARRY_CAPACITY_LABELS = {
    "bCraft": "Materials",
}
MAX_CARRY_CAPACITY_STORAGE_KEY_ALIASES = {
    "Materials": "bCraft",
}
EMPTY_POUCH_CAPACITY_LIMIT = 25
EMPTY_POUCH_ASSET = "pouches/none.png"
POUCH_STORAGE_MINIMUM_CAPACITIES = {
    "Bugs": 50,
    "Critters": 50,
    "Fishing": 50,
    "Souls": 50,
}
POUCH_TIERS = (
    ("mini", 25),
    ("cramped", 50),
    ("small", 100),
    ("average", 250),
    ("sizable", 500),
    ("big", 1000),
    ("large", 2000),
    ("massive", 5000),
    ("volumetric", 10000),
    ("colossal", 20000),
    ("gargantuan", 25000),
    ("herculean", 30000),
    ("enormous", 35000),
)
POUCH_STORAGE_FOLDERS = {
    "Bugs": "bug",
    "Chopping": "chopping",
    "Critters": "critter",
    "Fishing": "fishing",
    "Foods": "food",
    "Materials": "material",
    "Mining": "mining",
    "Souls": "soul",
}
POUCH_STORAGE_DISPLAY_TYPES = {
    "Bugs": "Bug",
    "Chopping": "Chopping",
    "Critters": "Critter",
    "Fishing": "Fishing",
    "Foods": "Food",
    "Materials": "Material",
    "Mining": "Mining",
    "Souls": "Soul",
}
POUCH_STORAGE_TYPE_ALIASES = {
    "choppin": "chopping",
    "critta": "critter",
    "fish": "fishing",
    "materials": "material",
    "matty": "material",
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
STATUE_VERSION_LABELS = {
    0: "Normal",
    1: "Gold",
    2: "Obsidian",
    3: "Zenith",
}
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
FORGE_UPGRADES = (
    {
        "name": "New Forge Slot",
        "max_level": 16,
        "description": "Extra slots to smelt ores",
    },
    {
        "name": "Ore Capacity Boost",
        "max_level": 50,
        "description": "Increases max ores per slot",
    },
    {
        "name": "Forge Speed",
        "max_level": 90,
        "description": "Ores are turned into bars faster",
    },
    {
        "name": "Forge EXP Gain",
        "max_level": 85,
        "description": "Increased EXP gain from using the forge",
    },
    {
        "name": "Bar Bonanza",
        "max_level": 75,
        "description": "Increased chance to make an extra bar",
    },
    {
        "name": "Puff Puff Go",
        "max_level": 60,
        "description": "Increased chance for a card drop while AFK",
    },
)
STAMP_CATEGORY_LABELS = {
    0: "Combat",
    1: "Skills",
    2: "Misc",
}
STAMP_WEBSITE_CATEGORY_KEYS = {
    0: "combat",
    1: "skills",
    2: "misc",
}
CAULDRON_LABELS = {
    0: "Power",
    1: "Quicc",
    2: "High-IQ",
    3: "Kazam",
}
CAULDRON_WEBSITE_KEYS = {
    0: "power",
    1: "quicc",
    2: "high-iq",
    3: "kazam",
}
CAULDRON_BOOST_LABELS = {
    0: "Speed",
    1: "Luck",
    2: "Cost",
    3: "Extra",
}
LIQUID_LABELS = {
    0: "Water Drops",
    1: "Liquid N2",
    2: "Trench H2O",
    3: "Toxic Mercury",
}
SIGIL_UNLOCK_STATES = {
    -1: "Locked",
    0: "Unlocking",
    1: "Unlocked",
    2: "Jade",
    3: "Ethereal",
    4: "Eclectic",
}
COMPANION_PET_CATEGORIES = (
    "Legacy Pets",
    "Fallen Spirits",
    "Shallow Waters",
    "Exclusive Pets",
    "Special Pets",
)
COMPANION_PET_CATEGORY_SIZE = 12
TASK_WORLD_LABELS = (
    "World 1",
    "World 2",
    "World 3",
    "World 4",
    "World 5",
    "World 6",
)
WORLD_3_SYSTEM_RAW_FIELDS: Mapping[str, tuple[str, ...]] = {
    "world_3_atom_collider": ("Atoms", "Divinity"),
    "world_3_equinox": ("Dream", "WeeklyBoss"),
    "world_3_buildings": ("Tower", "TowerInfo", "TotemInfo"),
    "world_3_death_note": ("Ninja",),
    "world_3_worship": ("TotemInfo", "worship"),
    "world_3_prayers": ("PrayOwned", "PrayersUnlocked"),
    "world_3_traps": ("PldTraps",),
    "world_3_salt_lick": ("SaltLick",),
    "world_3_construction": (
        "CogM",
        "CogMap",
        "CogO",
        "CogOrder",
        "FlagP",
        "FlagU",
        "FlagUnlock",
        "FlagsPlaced",
        "Tower",
        "TowerInfo",
    ),
    "world_3_armor_smithy": ("ServerGemsReceived",),
    "world_3_hat_rack": ("Spelunk",),
}
WORLD_SYSTEM_RAW_FIELDS: Mapping[str, tuple[str, ...]] = {
    **WORLD_3_SYSTEM_RAW_FIELDS,
    "world_4_cooking": ("Cooking", "Meals", "CookMaster", "Territory"),
    "world_4_breeding": ("Breeding", "Cooking", "Pets", "PetsStored", "Territory"),
    "world_4_laboratory": ("Lab",),
    "world_4_rift": ("Rift",),
    "world_4_tome": ("tome", "Tome"),
    "world_5_sailing": ("Boats", "Captains", "SailChests", "Sailing"),
    "world_5_divinity": ("Divinity", "deityMinorBonus", "divinity"),
    "world_5_gaming": ("Gaming", "GamingSprout", "Research", "Spelunk"),
    "world_5_hole": ("Holes", "Jars"),
    "world_5_slab": ("Cards", "Cards1"),
    "world_6_farming": ("FarmCrop", "FarmPlot", "FarmRank", "FarmUpg"),
    "world_6_sneaking": ("Ninja", "Spelunk"),
    "world_6_summoning": ("KRbest", "Summon"),
    "world_6_beanstalk": ("Ninja",),
    "world_6_emperor": ("Emperor", "Emporium", "serverVars"),
    "world_7_spelunking": ("Spelunk", "Tower", "TowerInfo"),
    "world_7_research": ("Research",),
    "world_7_gallery": ("Spelunk", "gallery"),
    "world_7_legend_talents": ("level", "Lv0"),
    "world_7_coral_reef": ("Spelunk", "Tower", "TowerInfo"),
    "world_7_zenith_market": ("Research", "Spelunk"),
    "world_7_clam_work": ("Spelunk",),
    "world_7_advice_fish": ("Research", "Spelunk"),
    "world_7_minehead": ("Research",),
    "world_7_glimbo": ("Research",),
    "world_7_sushi_station": ("Sushi",),
    "world_7_the_button": ("stats",),
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
        fields = dict(save_data)
        companion_data = _maybe_json(
            _first_value(
                raw_data,
                (
                    "companion",
                    "Companion",
                    "companions",
                    "Companions",
                    "companionData",
                    "CompanionData",
                ),
            )
        )
        if companion_data:
            fields["Companions"] = companion_data
        return fields
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
    afk_seconds = _normalized_afk_seconds(raw_afk_seconds, raw_data)
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
    global_time = _indexed_global_time(raw_data)
    if global_time is not None:
        details["afk_reference_timestamp"] = round(global_time, 2)
    if f"Money_{character_index}" in raw_data:
        details["money"] = idleon_raw_value(raw_data.get(f"Money_{character_index}"))
    if raw_afk_value != afk_seconds:
        details["raw_afk_value"] = round(raw_afk_value, 2)
    details.update(_indexed_stat_details(raw_data, character_index))
    details.update(_indexed_skill_level_details(raw_data, character_index))
    details.update(_indexed_inventory_details(raw_data, character_index))
    details.update(_indexed_inventory_bag_details(raw_data, character_index))
    details.update(_indexed_max_carry_capacity_details(raw_data, character_index))
    details.update(_indexed_storage_capacity_details(raw_data, character_index))
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
        _max_carry_capacity_label(key): coerced_value
        for key, value in max_carry_capacity.items()
        if (coerced_value := _coerce_int(value)) is not None
        if (isinstance(key, str) and key not in MAX_CARRY_CAPACITY_IGNORED_KEYS)
    }
    if not normalized_capacity:
        return {}

    return {
        "max_carry_capacity": normalized_capacity,
    }


def _indexed_storage_capacity_details(
    raw_data: Mapping[str, Any],
    character_index: int,
) -> dict[str, Any]:
    """Return structured per-storage carry capacity details."""
    max_carry_capacity = _maybe_json(raw_data.get(f"MaxCarryCap_{character_index}"))
    if not isinstance(max_carry_capacity, Mapping):
        return {}

    carry_bags = _website_data_mapping("carryBags")
    storage_capacities: dict[str, Any] = {}
    for raw_key, raw_value in max_carry_capacity.items():
        if not isinstance(raw_key, str) or raw_key in MAX_CARRY_CAPACITY_IGNORED_KEYS:
            continue
        maximum_capacity = _coerce_int(raw_value)
        if maximum_capacity is None:
            continue

        label = _max_carry_capacity_label(raw_key)
        pouch_details = _pouch_details_for_capacity(label, maximum_capacity)
        if pouch_details is None:
            largest_pouch = _largest_carry_bag(carry_bags, raw_key, maximum_capacity)
            if largest_pouch:
                bag_capacity, display_name = largest_pouch
                pouch_details = {
                    "base_capacity": bag_capacity,
                    "largest_pouch": _clean_display_text(display_name),
                    "largest_pouch_asset": _carry_bag_asset_filename(display_name),
                    "largest_pouch_capacity": bag_capacity,
                }
            else:
                pouch_details = {
                    "base_capacity": maximum_capacity,
                    "largest_pouch": "Unknown",
                    "largest_pouch_asset": None,
                    "largest_pouch_capacity": None,
                }

        details = {
            "storage_type": label,
            "raw_storage_type": raw_key,
            "base_capacity": pouch_details["base_capacity"],
            "capacity_per_slot": pouch_details["base_capacity"],
            "maximum_capacity": maximum_capacity,
            "largest_pouch": pouch_details["largest_pouch"],
            "largest_pouch_asset": pouch_details["largest_pouch_asset"],
        }
        if pouch_details["largest_pouch_capacity"] is not None:
            details["largest_pouch_capacity"] = pouch_details["largest_pouch_capacity"]
        storage_capacities[label] = _remove_empty_detail_values(details)

    if not storage_capacities:
        return {}
    return {"storage_capacities": storage_capacities}


def _max_carry_capacity_label(key: str) -> str:
    """Return a Home Assistant friendly carry capacity category label."""
    return MAX_CARRY_CAPACITY_LABELS.get(key, key)


def _largest_carry_bag(
    carry_bags: Mapping[str, Any],
    raw_key: str,
    maximum_capacity: int,
) -> tuple[int, str] | None:
    """Return the largest known carry bag that fits the current max capacity."""
    category_key = MAX_CARRY_CAPACITY_STORAGE_KEY_ALIASES.get(raw_key, raw_key)
    category = carry_bags.get(category_key)
    if not isinstance(category, Mapping):
        return None

    selected: tuple[int, str] | None = None
    for bag in category.values():
        if not isinstance(bag, Mapping):
            continue
        capacity = _coerce_int(bag.get("capacity"))
        display_name = bag.get("displayName")
        if capacity is None or not isinstance(display_name, str):
            continue
        if capacity <= maximum_capacity and (
            selected is None or capacity > selected[0]
        ):
            selected = (capacity, display_name)
    return selected


def _pouch_details_for_capacity(
    storage_type: str,
    maximum_capacity: int,
) -> dict[str, Any] | None:
    """Return deterministic pouch details for supported storage categories."""
    folder = POUCH_STORAGE_FOLDERS.get(storage_type)
    display_type = POUCH_STORAGE_DISPLAY_TYPES.get(storage_type)
    if folder is None or display_type is None:
        return None

    minimum_capacity = POUCH_STORAGE_MINIMUM_CAPACITIES.get(
        storage_type,
        EMPTY_POUCH_CAPACITY_LIMIT,
    )

    if maximum_capacity < minimum_capacity:
        return {
            "base_capacity": 0,
            "largest_pouch": "Empty Pouch",
            "largest_pouch_asset": EMPTY_POUCH_ASSET,
            "largest_pouch_capacity": 0,
        }

    selected_slug = (
        "mini" if minimum_capacity == EMPTY_POUCH_CAPACITY_LIMIT else "cramped"
    )
    selected_capacity = minimum_capacity
    for slug, capacity in POUCH_TIERS:
        if capacity <= maximum_capacity and capacity >= minimum_capacity:
            selected_slug = slug
            selected_capacity = capacity

    return {
        "base_capacity": selected_capacity,
        "largest_pouch": (
            f"{selected_slug.replace('_', ' ').title()} {display_type} Pouch"
        ),
        "largest_pouch_asset": f"pouches/{folder}/{selected_slug}.png",
        "largest_pouch_capacity": selected_capacity,
    }


def _carry_bag_asset_filename(display_name: str) -> str:
    """Return the static asset filename for a carry bag display name."""
    parts = [part.lower() for part in re.split(r"[_\s]+", display_name.strip()) if part]
    if len(parts) < 3 or parts[-1] != "pouch":
        return f"pouches/{'_'.join(parts)}.png"

    storage_type = parts[-2]
    storage_type = POUCH_STORAGE_TYPE_ALIASES.get(storage_type, storage_type)
    prefix = "_".join(parts[:-2])
    if prefix in {"miniature", "miniscule"}:
        prefix = "mini"
    if not prefix:
        return f"pouches/{storage_type}.png"
    return f"pouches/{storage_type}/{prefix}.png"


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
        trophy = _equipment_group_raw_item(
            equipment,
            EQUIPMENT_MAIN_GROUP_INDEX,
            EQUIPMENT_TROPHY_SLOT,
        )
        name_tag = _equipment_group_raw_item(
            equipment,
            EQUIPMENT_MAIN_GROUP_INDEX,
            EQUIPMENT_NAME_TAG_SLOT,
        )
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
        for slot in (*MAIN_EQUIPMENT_SLOTS, *TOOL_EQUIPMENT_SLOTS):
            raw_item = _equipment_group_raw_item(
                equipment,
                slot.group_index,
                slot.slot_index,
            )
            if not raw_item:
                continue
            details[slot.key] = _display_label(raw_item, website_data_key="items")
            details[f"{slot.key}_raw"] = raw_item
        if trophy:
            details["selected_trophy"] = _display_label(
                trophy, website_data_key="items"
            )
            details["selected_trophy_raw"] = trophy
        if name_tag:
            details["selected_name_tag"] = _display_label(
                name_tag,
                website_data_key="items",
            )
            details["selected_name_tag_raw"] = name_tag

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

    bank_money = parse_idleon_decimal(raw_data.get("MoneyBANK")) or Decimal(0)
    character_money = sum(
        (
            parse_idleon_decimal(raw_data.get(f"Money_{index}")) or Decimal(0)
            for index, _character in enumerate(characters)
        ),
        Decimal(0),
    )
    raw_money = bank_money + character_money
    if raw_money:
        total_money = idleon_raw_value(raw_money)
        details["total_money"] = total_money
        details["raw_money"] = total_money
        details["money_breakdown"] = {
            "bank": idleon_raw_value(bank_money),
            "characters": idleon_raw_value(character_money),
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
    statue_details = _indexed_statue_details(raw_data)
    if statue_details:
        details["statue_details"] = statue_details

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

    pets = _indexed_companion_pets(raw_data)
    if pets:
        details["pets"] = pets

    pet_crystals = _indexed_pet_crystals(raw_data)
    if pet_crystals is not None:
        details["pet_crystals"] = pet_crystals

    jade = _indexed_jade(raw_data)
    if jade is not None:
        details["jade"] = jade

    achievement_status = _indexed_achievement_status(raw_data)
    if achievement_status:
        details["achievement_status"] = achievement_status

    task_levels = _indexed_task_levels(raw_data)
    if task_levels:
        details["task_levels"] = task_levels

    taskboard_merits = _indexed_taskboard_merits(raw_data)
    if taskboard_merits:
        details["taskboard_merits"] = taskboard_merits

    taskboard_unlocks = _indexed_taskboard_unlocks(raw_data)
    if taskboard_unlocks:
        details["taskboard_unlocks"] = taskboard_unlocks

    world_1_anvil = _indexed_world_1_anvil(raw_data)
    if world_1_anvil:
        details["world_1_anvil"] = world_1_anvil

    world_1_bribes = _indexed_world_1_bribes(raw_data)
    if world_1_bribes:
        details["world_1_bribes"] = world_1_bribes

    world_1_stamps = _indexed_world_1_stamps(raw_data)
    if world_1_stamps:
        details["world_1_stamps"] = world_1_stamps

    world_summaries = _indexed_world_summaries(raw_data)
    if world_summaries:
        details["world_summaries"] = world_summaries

    world_2_cauldron = _indexed_world_2_cauldron(raw_data)
    if world_2_cauldron:
        details["world_2_cauldron"] = world_2_cauldron

    world_2_vials = _indexed_world_2_vials(raw_data)
    if world_2_vials:
        details["world_2_vials"] = world_2_vials

    world_2_bubbles = _indexed_world_2_bubbles(raw_data)
    if world_2_bubbles:
        details["world_2_bubbles"] = world_2_bubbles

    world_2_sigils = _indexed_world_2_sigils(raw_data)
    if world_2_sigils:
        details["world_2_sigils"] = world_2_sigils

    world_2_vote_ballots = _indexed_world_2_vote_ballots(raw_data)
    if world_2_vote_ballots:
        details["world_2_vote_ballots"] = world_2_vote_ballots

    killroy = _indexed_killroy(raw_data)
    if killroy:
        details["world_2_killroy"] = killroy

    world_system_details = _indexed_world_system_details(raw_data)
    details.update(world_system_details)

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
    statue_data = _indexed_statue_data(raw_data)
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


def _indexed_statue_details(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return named account-wide statue level, progress, and version details."""
    statue_data = _indexed_statue_data(raw_data)
    if not isinstance(statue_data, list):
        return {}

    statue_versions = _maybe_json(raw_data.get("StuG")) or _maybe_json(
        raw_data.get("StatueG")
    )
    if not isinstance(statue_versions, list):
        statue_versions = []

    details: dict[str, Any] = {}
    for index, label in enumerate(STATUE_LEVEL_LABELS):
        statue = _list_value(statue_data, index)
        if not isinstance(statue, list):
            continue

        level = _coerce_float(_list_value(statue, 0))
        if level is None:
            continue

        version_id = _coerce_int(_list_value(statue_versions, index)) or 0
        version_id = min(max(version_id, 0), 3)
        version = STATUE_VERSION_LABELS[version_id]
        banked = _coerce_float(_list_value(statue, 1))
        needed = _coerce_float(_list_value(statue, 2))

        detail = {
            "level": _compact_number(level),
            "statues_banked": _compact_number(banked) if banked is not None else None,
            "statues_needed_for_next_level": (
                _compact_number(needed) if needed is not None else None
            ),
            "progress_to_next_level_percent": _progress_percent(banked, needed),
            "statue_version": version,
            "statue_version_id": version_id,
            "statue_index": index,
            "asset_slug": _statue_asset_slug(label, version_id),
        }
        details[label] = _remove_empty_detail_values(detail)
    return details


def _indexed_statue_data(raw_data: Mapping[str, Any]) -> list[Any] | None:
    """Return the first available per-character statue level table."""
    statue_data = _maybe_json(raw_data.get("StatueLevels_0"))
    if isinstance(statue_data, list):
        return statue_data

    for key, value in raw_data.items():
        if key.startswith("StatueLevels_"):
            statue_data = _maybe_json(value)
            if isinstance(statue_data, list):
                return statue_data
    return None


def _statue_asset_slug(label: str, version_id: int) -> str:
    """Return the runtime statue asset stem for a label and version."""
    slug = _slugify(label)
    if version_id == 1:
        return f"{slug}_gold"
    if version_id == 2:
        return f"{slug}_obsidian"
    if version_id >= 3:
        return f"{slug}_zenith"
    return slug


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


def _indexed_companion_pets(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return grouped companion pet ownership from cloud companion data."""
    companion_data = _indexed_companion_data(raw_data)
    if not isinstance(companion_data, Mapping):
        return {}

    explicit_pets = _first_mapping(
        companion_data,
        ("pets", "companions", "categories", "companion_pets", "companionPets"),
    )
    if explicit_pets:
        return {
            _clean_display_text(str(category)): dict(pets)
            for category, pets in explicit_pets.items()
            if isinstance(pets, Mapping)
        }

    owned_counts = companion_data.get("l")
    if not isinstance(owned_counts, list):
        owned_counts = companion_data.get("owned")
    if not isinstance(owned_counts, list):
        return {}

    tradeable_counts = companion_data.get("t")
    if not isinstance(tradeable_counts, list):
        tradeable_counts = companion_data.get("tradeable")

    pet_names = _companion_pet_names()
    if tradeable_counts is None and any(
        isinstance(value, str) and "," in value for value in owned_counts
    ):
        return _indexed_companion_pets_from_entries(owned_counts, pet_names)

    grouped: dict[str, dict[str, str]] = {}
    for index, owned_value in enumerate(owned_counts):
        owned = _coerce_int(owned_value) or 0
        tradeable = _coerce_int(_list_value(tradeable_counts, index)) or 0
        if owned == 0 and tradeable == 0:
            continue

        category = _companion_pet_category(index)
        pet_name = pet_names.get(index, f"Pet {index + 1}")
        grouped.setdefault(category, {})[pet_name] = f"{tradeable}/{owned}"

    return grouped


def _indexed_companion_pets_from_entries(
    entries: list[Any],
    pet_names: Mapping[int, str],
) -> dict[str, Any]:
    """Return companion pet ownership from comma-packed cloud entries."""
    counts: dict[int, dict[str, int]] = {}
    for entry in entries:
        if not isinstance(entry, str):
            continue
        parts = entry.split(",")
        companion_index = _coerce_int(_list_value(parts, 0))
        if companion_index is None:
            continue
        tradeable = _list_value(parts, 1) == "1"
        current = counts.setdefault(companion_index, {"owned": 0, "tradeable": 0})
        current["owned"] += 1
        if tradeable:
            current["tradeable"] += 1

    grouped: dict[str, dict[str, str]] = {}
    for companion_index, count in counts.items():
        category = _companion_pet_category(companion_index)
        pet_name = pet_names.get(companion_index, f"Pet {companion_index + 1}")
        grouped.setdefault(category, {})[pet_name] = (
            f"{count['tradeable']}/{count['owned']}"
        )
    return grouped


def _indexed_companion_data(raw_data: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return raw companion data from any supported field name."""
    companion_data = _maybe_json(
        _first_value(
            raw_data,
            (
                "companions",
                "Companions",
                "companion",
                "Companion",
                "companionData",
                "CompanionData",
            ),
        )
    )
    return companion_data if isinstance(companion_data, Mapping) else None


def _indexed_pet_crystals(raw_data: Mapping[str, Any]) -> int | None:
    """Return companion pet crystals from cloud companion data."""
    companion_data = _indexed_companion_data(raw_data)
    if not isinstance(companion_data, Mapping):
        return None
    return _first_int(
        companion_data,
        (
            "s",
            "pet_crystals",
            "petCrystals",
            "companion_crystals",
            "companionCrystals",
        ),
    )


def _indexed_jade(raw_data: Mapping[str, Any]) -> str | None:
    """Return W6 sneaking Jade from indexed cloud data."""
    ninja = _maybe_json(raw_data.get("Ninja"))
    if not isinstance(ninja, list):
        return None

    currency_block = _list_value(ninja, 102)
    if not isinstance(currency_block, list):
        return None

    jade = _list_value(currency_block, 1)
    if jade is None:
        return None
    return _jade_detail_value(jade)


def _indexed_achievement_status(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return achievement completion and progress grouped by world."""
    achievements = _maybe_json(raw_data.get("AchieveReg"))
    if not isinstance(achievements, list):
        return {}

    labels = _achievement_labels()
    status: dict[str, Any] = {}
    offset = 0
    for world_index, task_count in enumerate(_achievement_world_sizes()):
        world_values = achievements[offset : offset + task_count]
        offset += task_count
        group = _achievement_group_status(
            world_values,
            labels=labels,
            label_offset=offset - task_count,
        )
        if group:
            status[_world_label(world_index)] = group

    if offset < len(achievements):
        group = _achievement_group_status(
            achievements[offset:],
            labels=labels,
            label_offset=offset,
        )
        if group:
            status["Other"] = group

    steam_achievements = _maybe_json(raw_data.get("SteamAchieve"))
    if isinstance(steam_achievements, list):
        group = _achievement_group_status(
            steam_achievements,
            labels={},
            label_offset=0,
            fallback_prefix="Steam Achievement",
        )
        if group:
            status["Steam"] = group

    return status


def _indexed_task_levels(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return task levels and progress grouped by world."""
    task_progress = _maybe_json(raw_data.get("TaskZZ0"))
    task_levels = _maybe_json(raw_data.get("TaskZZ1"))
    if not isinstance(task_levels, list):
        return {}

    labels = _task_labels()
    grouped: dict[str, Any] = {}
    for world_index, level_row in enumerate(task_levels):
        if not isinstance(level_row, list):
            continue
        world_tasks: dict[str, Any] = {}
        progress_row = (
            _list_value(task_progress, world_index)
            if isinstance(task_progress, list)
            else None
        )
        breakpoints = _task_breakpoints_for_world(world_index)
        for task_index, level_value in enumerate(level_row):
            level = _coerce_int(level_value) or 0
            raw_progress = (
                _coerce_float(_list_value(progress_row, task_index))
                if isinstance(progress_row, list)
                else None
            )
            if level == 0 and not raw_progress:
                continue

            max_level = max(len(_list_value(breakpoints, task_index) or []), 10)
            task_label = labels.get((world_index, task_index), f"Task {task_index + 1}")
            entry: dict[str, Any] = {"level": f"{level}/{max_level}"}
            progress_percent = _task_progress_percent(
                level=level,
                raw_progress=raw_progress,
                breakpoints=_list_value(breakpoints, task_index),
            )
            if progress_percent is not None:
                entry["progress_percent"] = progress_percent
            elif raw_progress is not None:
                entry["progress"] = _compact_number(raw_progress)
            world_tasks[task_label] = entry

        if world_tasks:
            grouped[_world_label(world_index)] = world_tasks
    return grouped


def _indexed_taskboard_merits(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return taskboard merit levels grouped by world."""
    merit_levels = _maybe_json(raw_data.get("TaskZZ2"))
    if not isinstance(merit_levels, list):
        return {}

    labels, max_levels = _merit_metadata()
    grouped: dict[str, Any] = {}
    for world_index, level_row in enumerate(merit_levels):
        if not isinstance(level_row, list):
            continue
        world_merits: dict[str, str] = {}
        for merit_index, level_value in enumerate(level_row):
            level = _coerce_int(level_value) or 0
            if level == 0:
                continue
            merit_label = labels.get(
                (world_index, merit_index),
                f"Merit {merit_index + 1}",
            )
            max_level = max_levels.get((world_index, merit_index), "?")
            world_merits[merit_label] = f"{level}/{max_level}"
        if world_merits:
            grouped[_world_label(world_index)] = world_merits
    return grouped


def _indexed_taskboard_unlocks(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return taskboard unlock states grouped by tab."""
    unlock_rows = _maybe_json(raw_data.get("TaskZZ3"))
    if not isinstance(unlock_rows, list):
        return {}

    grouped: dict[str, Any] = {}
    for tab_index, unlock_row in enumerate(unlock_rows):
        if not isinstance(unlock_row, list):
            continue
        tab_unlocks: dict[str, str] = {}
        for unlock_index, raw_state in enumerate(unlock_row):
            state = _coerce_int(raw_state) or 0
            label = f"Unlock {unlock_index + 1}"
            tab_unlocks[label] = "Achieved" if state > 0 else "Unavailable"
        if tab_unlocks:
            grouped[f"Tab {tab_index + 1}"] = tab_unlocks
    return grouped


def _indexed_world_1_anvil(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return World 1 forge/anvil account details."""
    slots = _indexed_forge_slots(raw_data)
    upgrades = _indexed_forge_upgrades(raw_data)
    anvil: dict[str, Any] = {}
    if slots:
        anvil["slots"] = slots
    if upgrades:
        anvil["upgrades"] = upgrades
    return anvil


def _indexed_forge_slots(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return forge slot contents from raw order and quantity fields."""
    item_order = _maybe_json(raw_data.get("ForgeItemOrder"))
    quantities = _maybe_json(raw_data.get("ForgeItemQuantity")) or _maybe_json(
        raw_data.get("ForgeItemQty")
    )
    if not isinstance(item_order, list) or not isinstance(quantities, list):
        return {}

    forge_levels = _maybe_json(raw_data.get("FurnaceLevels")) or _maybe_json(
        raw_data.get("ForgeLV")
    )
    forge_speed = 100
    if isinstance(forge_levels, list):
        forge_speed += 5 * (_coerce_float(_list_value(forge_levels, 2)) or 0)

    slots: dict[str, Any] = {}
    for slot_index, row_start in enumerate(range(0, len(item_order), 3), start=1):
        ore_raw = _list_value(item_order, row_start)
        accelerant_raw = _list_value(item_order, row_start + 1)
        bar_raw = _list_value(item_order, row_start + 2)
        ore_count = _coerce_float(_list_value(quantities, row_start)) or 0
        accelerant_count = _coerce_float(_list_value(quantities, row_start + 1)) or 0
        bar_count = _coerce_float(_list_value(quantities, row_start + 2)) or 0

        if not any((ore_count, accelerant_count, bar_count)) and all(
            _is_blank_item(value) for value in (ore_raw, accelerant_raw, bar_raw)
        ):
            continue

        slots[f"Slot {slot_index}"] = {
            "ore": _forge_item_quantity(ore_raw, ore_count),
            "accelerant": _forge_item_quantity(accelerant_raw, accelerant_count),
            "bars": _forge_item_quantity(bar_raw, bar_count),
            "time_until_ore_depleted_seconds": _forge_time_until_empty_seconds(
                ore_raw=ore_raw,
                ore_count=ore_count,
                accelerant_raw=accelerant_raw,
                forge_speed=forge_speed,
            ),
        }
    return slots


def _indexed_forge_upgrades(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return forge upgrade levels and status."""
    forge_levels = _maybe_json(raw_data.get("FurnaceLevels")) or _maybe_json(
        raw_data.get("ForgeLV")
    )
    if not isinstance(forge_levels, list):
        return {}

    upgrades: dict[str, Any] = {}
    for index, upgrade in enumerate(FORGE_UPGRADES):
        level = _coerce_int(_list_value(forge_levels, index)) or 0
        max_level = int(upgrade["max_level"])
        upgrades[str(upgrade["name"])] = {
            "level": f"{level}/{max_level}",
            "description": upgrade["description"],
            "cost_for_next_level": "Maxed" if level >= max_level else "Unknown",
            "total_cost_to_max": "Maxed" if level >= max_level else "Unknown",
        }
    return upgrades


def _indexed_world_1_bribes(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return World 1 bribes with purchase status and price."""
    bribe_status = _maybe_json(raw_data.get("BribeStatus"))
    if not isinstance(bribe_status, list):
        return {}

    bribes = _website_data_list("bribes")
    if not bribes:
        return {}

    parsed: dict[str, Any] = {}
    for index, bribe in enumerate(bribes):
        if not isinstance(bribe, Mapping):
            continue
        name = _clean_display_text(str(bribe.get("name") or f"Bribe {index + 1}"))
        purchased = _coerce_int(_list_value(bribe_status, index)) == 1
        parsed[name] = {
            "description": _clean_display_text(str(bribe.get("desc") or "")),
            "price": "Purchased"
            if purchased
            else _compact_number(_coerce_float(bribe.get("price")) or 0),
        }
    return parsed


def _indexed_world_1_stamps(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return World 1 stamp levels, effects, and next cost estimates."""
    stamp_levels = _maybe_json(raw_data.get("StampLv")) or _maybe_json(
        raw_data.get("StampLevel")
    )
    stamp_max_levels = _maybe_json(raw_data.get("StampLvM")) or _maybe_json(
        raw_data.get("StampLevelMAX")
    )
    if not isinstance(stamp_levels, list):
        return {}

    stamps = _website_data_mapping("stamps")
    if not stamps:
        return {}

    parsed: dict[str, Any] = {}
    for category_index, category_levels in enumerate(stamp_levels):
        if not isinstance(category_levels, Mapping):
            continue
        website_category_key = STAMP_WEBSITE_CATEGORY_KEYS.get(category_index)
        category_label = STAMP_CATEGORY_LABELS.get(
            category_index,
            f"Category {category_index + 1}",
        )
        website_category = stamps.get(website_category_key)
        if not isinstance(website_category, Mapping):
            continue

        category_max_levels = _list_value(stamp_max_levels, category_index)
        category_stamps: dict[str, Any] = {}
        for key, level_value in category_levels.items():
            if key == "length":
                continue
            stamp = website_category.get(str(key))
            if not isinstance(stamp, Mapping):
                continue
            level = _coerce_int(level_value) or 0
            if level <= 0:
                continue
            max_level = (
                _coerce_int(category_max_levels.get(key))
                if isinstance(category_max_levels, Mapping)
                else None
            )
            name = _clean_display_text(str(stamp.get("displayName") or f"Stamp {key}"))
            category_stamps[name] = {
                "current_level": level,
                "maximum_level": max_level,
                "effect": _clean_display_text(str(stamp.get("effect") or "")),
                "cost_to_level_up": _stamp_cost_to_level(level, stamp),
            }

        if category_stamps:
            parsed[category_label] = category_stamps
    return parsed


def _indexed_world_summaries(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return compact per-world summaries for account-wide systems."""
    summaries: dict[str, Any] = {}

    cauldron_bubbles = _cauldron_bubble_total(raw_data)
    if cauldron_bubbles:
        summaries["World 2"] = {
            "Alchemy bubble levels": _compact_number(cauldron_bubbles)
        }

    world_3: dict[str, Any] = {}
    refined_salts = _refined_salt_total(raw_data)
    if refined_salts:
        world_3["Refined salts"] = _compact_number(refined_salts)
    printed = _printer_total(raw_data)
    if printed:
        world_3["Printer sample total"] = _compact_number(printed)
    if world_3:
        summaries["World 3"] = world_3

    for world_label, raw_keys in (
        ("World 4", ("Cooking", "Lab")),
        ("World 5", ("Sailing", "Gaming", "Divinity")),
        ("World 6", ("FarmCrop", "Summon")),
        ("World 7", ("Holes",)),
    ):
        summary = _raw_system_presence_summary(raw_data, raw_keys)
        if summary:
            summaries[world_label] = summary

    return summaries


def _indexed_world_2_cauldron(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return World 2 cauldron upgrade and liquid summaries."""
    cauldron: dict[str, Any] = {}
    levels = _maybe_json(raw_data.get("CauldUpgLVs"))
    xp_values = _maybe_json(raw_data.get("CauldUpgXPs"))
    if isinstance(levels, list):
        cauldron["upgrades"] = _cauldron_upgrade_summary(levels, xp_values)

    alchemy = _alchemy_rows(raw_data)
    liquids = _list_value(alchemy, 6) if isinstance(alchemy, list) else None
    if isinstance(liquids, list):
        cauldron["liquids"] = {
            LIQUID_LABELS.get(index, f"Liquid {index + 1}"): _compact_number(value)
            for index, raw_value in enumerate(liquids)
            if (value := _coerce_float(raw_value)) is not None
        }

    p2w = _maybe_json(raw_data.get("CauldronP2W"))
    if isinstance(p2w, list):
        cauldron["pay_to_win"] = _cauldron_p2w_summary(p2w)

    return cauldron


def _indexed_world_2_vials(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return unlocked World 2 vials."""
    alchemy = _alchemy_rows(raw_data)
    vial_levels = _list_value(alchemy, 4) if isinstance(alchemy, list) else None
    if not isinstance(vial_levels, Mapping):
        return {}

    vials = _website_data_mapping("vials")
    parsed: dict[str, Any] = {}
    for key, raw_level in vial_levels.items():
        if key == "length":
            continue
        level = _coerce_int(raw_level) or 0
        if level <= 0:
            continue
        vial = vials.get(str(key))
        name = f"Vial {int(key) + 1}" if str(key).isdigit() else f"Vial {key}"
        effect = ""
        material = ""
        if isinstance(vial, Mapping):
            name = _clean_display_text(str(vial.get("name") or name))
            effect = _clean_display_text(str(vial.get("desc") or ""))
            material = _clean_display_text(str(vial.get("mainItem") or ""))
        parsed[name] = {
            "level": level,
            "maximum_level": 13,
            "effect": effect,
            "material": material,
        }
    return parsed


def _indexed_world_2_bubbles(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return nonzero World 2 alchemy bubbles grouped by cauldron."""
    alchemy = _alchemy_rows(raw_data)
    if not isinstance(alchemy, list):
        return {}

    cauldrons = _website_data_mapping("cauldrons")
    parsed: dict[str, Any] = {}
    for cauldron_index in range(4):
        bubble_levels = _list_value(alchemy, cauldron_index)
        if not isinstance(bubble_levels, Mapping):
            continue
        website_key = CAULDRON_WEBSITE_KEYS[cauldron_index]
        website_bubbles = cauldrons.get(website_key)
        cauldron_bubbles: dict[str, Any] = {}
        for key, raw_level in bubble_levels.items():
            if key == "length":
                continue
            level = _coerce_int(raw_level) or 0
            if level <= 0:
                continue
            bubble = (
                _list_value(website_bubbles, _coerce_int(key) or 0)
                if isinstance(website_bubbles, list)
                else None
            )
            name = f"Bubble {int(key) + 1}" if str(key).isdigit() else f"Bubble {key}"
            description = ""
            if isinstance(bubble, Mapping):
                name = _clean_display_text(str(bubble.get("bubbleName") or name))
                description = _clean_display_text(str(bubble.get("desc") or ""))
            cauldron_bubbles[name] = {
                "level": level,
                "description": description,
            }
        if cauldron_bubbles:
            parsed[CAULDRON_LABELS[cauldron_index]] = cauldron_bubbles
    return parsed


def _indexed_world_2_sigils(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return World 2 sigil progress and unlock state."""
    p2w = _maybe_json(raw_data.get("CauldronP2W"))
    sigil_values = _list_value(p2w, 4) if isinstance(p2w, list) else None
    if not isinstance(sigil_values, list):
        return {}

    sigils = _website_data_list("sigils")
    parsed: dict[str, Any] = {}
    for index in range(0, len(sigil_values), 2):
        progress = _coerce_float(_list_value(sigil_values, index)) or 0
        raw_state = _coerce_int(_list_value(sigil_values, index + 1))
        sigil_index = index // 2
        sigil = _list_value(sigils, sigil_index)
        name = f"Sigil {sigil_index + 1}"
        effect = ""
        if isinstance(sigil, Mapping):
            name = _clean_display_text(str(sigil.get("name") or name))
            effect = _clean_display_text(str(sigil.get("effect") or ""))
        if raw_state is None and progress == 0:
            continue
        parsed[name] = {
            "state": SIGIL_UNLOCK_STATES.get(raw_state or 0, str(raw_state)),
            "progress": _compact_number(progress),
            "effect": effect,
        }
    return parsed


def _indexed_world_2_vote_ballots(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return World 2 vote ballot data when server variables are present."""
    server_vars = _maybe_json(raw_data.get("serverVars")) or _maybe_json(
        raw_data.get("ServerVars")
    )
    if not isinstance(server_vars, Mapping):
        explicit = _first_mapping(
            raw_data,
            ("vote_ballots", "voteBallots", "voteBallot", "ballots"),
        )
        return dict(explicit) if explicit else {}

    ballots: dict[str, Any] = {}
    vote_categories = _maybe_json(server_vars.get("voteCategories"))
    vote_percent = _maybe_json(server_vars.get("votePercent"))
    if isinstance(vote_categories, list):
        ballots["Bonus Ballot"] = _vote_ballot_summary(
            vote_categories,
            vote_percent if isinstance(vote_percent, list) else [],
        )

    merit_categories = _maybe_json(server_vars.get("voteCat2"))
    merit_percent = _maybe_json(server_vars.get("votePercent2"))
    if isinstance(merit_categories, list):
        ballots["Multi-Meritocracy"] = _vote_ballot_summary(
            merit_categories,
            merit_percent if isinstance(merit_percent, list) else [],
        )
    return ballots


def _indexed_killroy(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return Killroy details when raw or cleaned data is available."""
    explicit = _first_mapping(
        raw_data,
        ("killroy", "Killroy", "KillRoy", "killroy_data", "killroyData"),
    )
    if explicit:
        return dict(explicit)

    account_options = _maybe_json(raw_data.get("accountOptions")) or _maybe_json(
        raw_data.get("OptLacc")
    )
    if not isinstance(account_options, list):
        return {}

    rooms = 3 if _coerce_int(_list_value(account_options, 227)) == 1 else 2
    return {
        "rooms_available": rooms,
        "schedule": "Unavailable until server variables are present",
    }


def _indexed_world_system_details(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return compact account system summaries for later worlds."""
    details: dict[str, Any] = {}

    printer = _indexed_world_3_printer(raw_data)
    if printer:
        details["world_3_printer"] = printer

    refinery = _indexed_world_3_refinery(raw_data)
    if refinery:
        details["world_3_refinery"] = refinery

    for detail_key, raw_keys in WORLD_SYSTEM_RAW_FIELDS.items():
        if detail_key in details:
            continue
        summary = _raw_system_presence_summary(raw_data, raw_keys)
        if summary:
            details[detail_key] = summary

    return details


def _indexed_world_3_printer(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return World 3 3D printer summary details."""
    printer = _maybe_json(raw_data.get("Print")) or _maybe_json(raw_data.get("Printer"))
    if not isinstance(printer, list):
        return {}

    numeric_values = [
        value
        for raw_value in printer
        if not (isinstance(raw_value, str) and not _looks_numeric(raw_value))
        and (value := _coerce_float(raw_value)) is not None
    ]
    details: dict[str, Any] = {
        "sample_count": len([value for value in numeric_values if value > 0]),
        "total_printed": _compact_number(sum(numeric_values)),
    }

    printer_extra = _maybe_json(raw_data.get("PrinterXtra"))
    if isinstance(printer_extra, list):
        details["extra_count"] = len(
            [value for value in printer_extra if value not in (None, 0, "", [], {})]
        )

    return details


def _indexed_world_3_refinery(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return World 3 refinery summary details."""
    refinery = _maybe_json(raw_data.get("Refinery"))
    if not isinstance(refinery, list):
        return {}

    details: dict[str, Any] = {
        "refined_salt_total": _compact_number(_refined_salt_total(raw_data)),
        "sections": len([section for section in refinery if section not in ([], {})]),
    }

    salts = _list_value(refinery, 2)
    if isinstance(salts, Mapping):
        details["salt_count"] = len(
            [value for value in salts.values() if value not in (None, 0, "", [], {})]
        )
    elif isinstance(salts, list):
        details["salt_count"] = len(
            [value for value in salts if value not in (None, 0, "", [], {})]
        )

    return details


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


def _equipment_group_raw_item(
    equipment: list[Any],
    group_index: int,
    slot_index: int,
) -> str | None:
    """Return the raw item ID from one EquipOrder slot."""
    if group_index >= len(equipment):
        return None
    group = equipment[group_index]
    if not isinstance(group, Mapping):
        return None
    value = group.get(str(slot_index))
    if not _inventory_slot_has_item(value):
        return None
    return str(value)


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


def _normalized_afk_seconds(value: float, raw_data: Mapping[str, Any]) -> float:
    """Return AFK time normalized to seconds from known export units."""
    global_time = _indexed_global_time(raw_data)
    if value > 1_000_000_000 and global_time is not None and global_time >= value:
        return global_time - value
    timestamp_value = value * 1000
    if value > 1_000_000 and global_time is not None and global_time >= timestamp_value:
        return global_time - timestamp_value
    return value


def _indexed_global_time(raw_data: Mapping[str, Any]) -> float | None:
    """Return the indexed export global time value when available."""
    time_away = _maybe_json(raw_data.get("TimeAway"))
    if not isinstance(time_away, Mapping):
        return None
    return _coerce_float(time_away.get("GlobalTime"))


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
    money = _first_value(character_data, ("money", "coins", "raw_money", "rawMoney"))
    if money is not None:
        parsed_details["money"] = idleon_raw_value(money)
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
    total_money = _first_value(
        account_data,
        ("total_money", "totalMoney", "money", "coins"),
    )
    raw_money = _first_value(account_data, ("raw_money", "rawMoney"))
    if total_money is not None:
        details["total_money"] = idleon_raw_value(total_money)
    if raw_money is not None:
        details["raw_money"] = idleon_raw_value(raw_money)
    if "total_money" not in details and "raw_money" in details:
        details["total_money"] = details["raw_money"]
    if "raw_money" not in details and "total_money" in details:
        details["raw_money"] = details["total_money"]
    pet_crystals = _first_int(
        account_data,
        (
            "pet_crystals",
            "petCrystals",
            "companion_crystals",
            "companionCrystals",
        ),
    )
    if pet_crystals is None:
        companion_data = _indexed_companion_data(account_data)
        if isinstance(companion_data, Mapping):
            pet_crystals = _first_int(companion_data, ("s",))
    if pet_crystals is not None:
        details["pet_crystals"] = pet_crystals
    for detail_key, aliases in (
        ("currencies", ("currencies", "currency")),
        ("shrine_levels", ("shrine_levels", "shrineLevels", "shrines")),
        ("statue_levels", ("statue_levels", "statueLevels", "statues")),
        ("statue_details", ("statue_details", "statueDetails")),
        ("colosseum_scores", ("colosseum_scores", "colosseumScores")),
        ("minigame_scores", ("minigame_scores", "minigameScores")),
        ("progress_totals", ("progress_totals", "progressTotals", "totals")),
        ("pets", ("pets", "companions", "companion_pets", "companionPets")),
        (
            "achievement_status",
            (
                "achievement_status",
                "achievementStatus",
                "achievements_by_world",
                "achievementsByWorld",
            ),
        ),
        ("task_levels", ("task_levels", "taskLevels", "tasks")),
        ("taskboard_merits", ("taskboard_merits", "taskboardMerits", "merits")),
        (
            "taskboard_unlocks",
            ("taskboard_unlocks", "taskboardUnlocks", "task_unlocks", "taskUnlocks"),
        ),
        ("world_1_anvil", ("world_1_anvil", "world1Anvil", "anvil", "forge")),
        ("world_1_bribes", ("world_1_bribes", "world1Bribes", "bribes")),
        ("world_1_stamps", ("world_1_stamps", "world1Stamps", "stamps")),
        (
            "world_2_cauldron",
            ("world_2_cauldron", "world2Cauldron", "cauldron"),
        ),
        ("world_2_vials", ("world_2_vials", "world2Vials", "vials")),
        ("world_2_bubbles", ("world_2_bubbles", "world2Bubbles", "bubbles")),
        ("world_2_sigils", ("world_2_sigils", "world2Sigils", "sigils")),
        (
            "world_2_vote_ballots",
            ("world_2_vote_ballots", "world2VoteBallots", "vote_ballots"),
        ),
        (
            "world_2_killroy",
            ("world_2_killroy", "world2Killroy", "killroy", "Killroy", "KillRoy"),
        ),
        ("world_3_printer", ("world_3_printer", "world3Printer", "printer")),
        ("world_3_refinery", ("world_3_refinery", "world3Refinery", "refinery")),
        (
            "world_3_atom_collider",
            ("world_3_atom_collider", "world3AtomCollider", "atom_collider", "atoms"),
        ),
        ("world_3_equinox", ("world_3_equinox", "world3Equinox", "equinox")),
        ("world_3_buildings", ("world_3_buildings", "world3Buildings", "buildings")),
        (
            "world_3_death_note",
            ("world_3_death_note", "world3DeathNote", "death_note", "deathNote"),
        ),
        ("world_3_worship", ("world_3_worship", "world3Worship", "worship")),
        ("world_3_prayers", ("world_3_prayers", "world3Prayers", "prayers")),
        ("world_3_traps", ("world_3_traps", "world3Traps", "traps")),
        (
            "world_3_salt_lick",
            ("world_3_salt_lick", "world3SaltLick", "salt_lick", "saltLick"),
        ),
        (
            "world_3_construction",
            ("world_3_construction", "world3Construction", "construction"),
        ),
        (
            "world_3_armor_smithy",
            ("world_3_armor_smithy", "world3ArmorSmithy", "armor_smithy"),
        ),
        ("world_3_hat_rack", ("world_3_hat_rack", "world3HatRack", "hat_rack")),
        ("world_4_cooking", ("world_4_cooking", "world4Cooking", "cooking")),
        ("world_4_breeding", ("world_4_breeding", "world4Breeding", "breeding")),
        (
            "world_4_laboratory",
            ("world_4_laboratory", "world4Laboratory", "laboratory", "lab"),
        ),
        ("world_4_rift", ("world_4_rift", "world4Rift", "rift")),
        ("world_4_tome", ("world_4_tome", "world4Tome", "tome")),
        ("world_5_sailing", ("world_5_sailing", "world5Sailing", "sailing")),
        ("world_5_divinity", ("world_5_divinity", "world5Divinity", "divinity")),
        ("world_5_gaming", ("world_5_gaming", "world5Gaming", "gaming")),
        ("world_5_hole", ("world_5_hole", "world5Hole", "hole", "holes")),
        ("world_5_slab", ("world_5_slab", "world5Slab", "slab", "looty")),
        ("world_6_farming", ("world_6_farming", "world6Farming", "farming")),
        ("world_6_sneaking", ("world_6_sneaking", "world6Sneaking", "sneaking")),
        ("world_6_summoning", ("world_6_summoning", "world6Summoning", "summoning")),
        ("world_6_beanstalk", ("world_6_beanstalk", "world6Beanstalk", "beanstalk")),
        ("world_6_emperor", ("world_6_emperor", "world6Emperor", "emperor")),
        (
            "world_7_spelunking",
            ("world_7_spelunking", "world7Spelunking", "spelunking"),
        ),
        ("world_7_research", ("world_7_research", "world7Research", "research")),
        ("world_7_gallery", ("world_7_gallery", "world7Gallery", "gallery")),
        (
            "world_7_legend_talents",
            ("world_7_legend_talents", "world7LegendTalents", "legend_talents"),
        ),
        (
            "world_7_coral_reef",
            ("world_7_coral_reef", "world7CoralReef", "coral_reef"),
        ),
        (
            "world_7_zenith_market",
            ("world_7_zenith_market", "world7ZenithMarket", "zenith_market"),
        ),
        (
            "world_7_clam_work",
            ("world_7_clam_work", "world7ClamWork", "clam_work"),
        ),
        (
            "world_7_advice_fish",
            ("world_7_advice_fish", "world7AdviceFish", "advice_fish"),
        ),
        ("world_7_minehead", ("world_7_minehead", "world7Minehead", "minehead")),
        ("world_7_glimbo", ("world_7_glimbo", "world7Glimbo", "glimbo")),
        (
            "world_7_sushi_station",
            ("world_7_sushi_station", "world7SushiStation", "sushi_station"),
        ),
        (
            "world_7_the_button",
            ("world_7_the_button", "world7TheButton", "the_button"),
        ),
        (
            "world_summaries",
            (
                "world_summaries",
                "worldSummaries",
                "world_information",
                "worldInformation",
                "worlds",
            ),
        ),
    ):
        if detail_key not in details:
            value = _first_mapping(account_data, aliases)
            if value:
                details[detail_key] = dict(value)
    jade = _first_value(account_data, ("jade", "jade_count", "jadeCount"))
    if jade is None:
        sneaking = details.get("world_6_sneaking")
        if isinstance(sneaking, Mapping):
            jade = _first_value(sneaking, ("jade", "jade_count", "jadeCount"))
    if jade is not None:
        details["jade"] = _jade_detail_value(jade)
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
    if value.is_integer() and abs(value) <= MAX_SAFE_INTEGER_FLOAT:
        return int(value)
    return round(value, 2)


def _progress_percent(
    progress: float | None, needed: float | None
) -> int | float | None:
    """Return compact percent progress when both parts are known."""
    if progress is None or needed is None or needed <= 0:
        return None
    return _compact_number(min((progress / needed) * 100, 100))


def _jade_detail_value(value: Any) -> str | None:
    """Return Jade as a raw numeric string without expanding huge values."""
    if parse_idleon_decimal(value) is None:
        return None
    return idleon_raw_value(value)


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


def _forge_item_quantity(raw_item: Any, count: float) -> dict[str, Any]:
    """Return a forge slot item with a display label and count."""
    return {
        "type": _item_label(raw_item),
        "count": _compact_number(count),
    }


def _forge_time_until_empty_seconds(
    *,
    ore_raw: Any,
    ore_count: float,
    accelerant_raw: Any,
    forge_speed: float,
) -> int | float:
    """Return an estimated number of seconds until a forge slot runs out of ore."""
    if ore_count <= 0 or _is_blank_item(ore_raw):
        return 0

    ore = _item_data(ore_raw)
    ore_amount = _coerce_float(ore.get("Amount")) if isinstance(ore, Mapping) else None
    ore_cooldown = (
        _coerce_float(ore.get("Cooldown")) if isinstance(ore, Mapping) else None
    )
    if not ore_amount or not ore_cooldown:
        return 0

    accelerant = _item_data(accelerant_raw)
    speed_multiplier = 1.0
    if (
        isinstance(accelerant, Mapping)
        and accelerant.get("Effect") == "SpeedForge"
        and (amount := _coerce_float(accelerant.get("Amount")))
    ):
        speed_multiplier = amount

    slot_speed = (round(forge_speed) / 100) * speed_multiplier * 0.25
    if slot_speed <= 0:
        return 0
    seconds = round(ore_count / ore_amount) * (ore_cooldown / (4 * slot_speed))
    return _compact_number(seconds)


def _stamp_cost_to_level(level: int, stamp: Mapping[str, Any]) -> str:
    """Return a readable estimate of a stamp's next level cost."""
    material_cost = _stamp_material_cost(level, stamp)
    coin_cost = _stamp_coin_cost(level, stamp)
    item = _list_value(stamp.get("itemReq", []), 0)
    item_name = "Unknown item"
    if isinstance(item, Mapping):
        item_name = _clean_display_text(str(item.get("name") or item.get("rawName")))

    return (
        f"{_compact_number(material_cost)} {item_name}; "
        f"{_compact_number(coin_cost)} coins"
    )


def _stamp_material_cost(level: int, stamp: Mapping[str, Any]) -> float:
    """Return a no-discount estimate of the material cost for the next stamp level."""
    base_cost = _coerce_float(stamp.get("baseMatCost")) or 0
    pow_base = _coerce_float(stamp.get("powMatBase")) or 1
    req_level = _coerce_float(stamp.get("reqItemMultiplicationLevel")) or 1
    exponent = max(round(level / req_level) - 1, 0) ** 0.8
    return max(1.0, base_cost * pow(pow_base, exponent))


def _stamp_coin_cost(level: int, stamp: Mapping[str, Any]) -> float:
    """Return a no-discount estimate of the coin cost for the next stamp level."""
    base_cost = _coerce_float(stamp.get("baseCoinCost")) or 0
    pow_base = _coerce_float(stamp.get("powCoinBase")) or 1.05
    req_level = _coerce_float(stamp.get("reqItemMultiplicationLevel")) or 1
    ratio = level / (level + 5 * req_level) if level + 5 * req_level else 0
    adjusted_pow_base = max(1.05, pow_base - ratio * 0.25)
    return base_cost * pow(adjusted_pow_base, level * (10 / req_level))


def _alchemy_rows(raw_data: Mapping[str, Any]) -> list[Any]:
    """Return alchemy rows from raw CauldronInfo."""
    cauldron_info = _maybe_json(raw_data.get("CauldronInfo"))
    if isinstance(cauldron_info, list):
        return cauldron_info
    return []


def _cauldron_upgrade_summary(
    levels: list[Any],
    xp_values: Any,
) -> dict[str, Any]:
    """Return cauldron boost upgrade levels grouped by cauldron."""
    upgrades: dict[str, Any] = {}
    for cauldron_index, cauldron_label in CAULDRON_LABELS.items():
        start = cauldron_index * 4
        boosts: dict[str, Any] = {}
        for boost_offset, boost_label in CAULDRON_BOOST_LABELS.items():
            index = start + boost_offset
            level = _coerce_int(_list_value(levels, index))
            if level is None:
                continue
            progress = (
                _coerce_float(_list_value(xp_values, index))
                if isinstance(xp_values, list)
                else None
            )
            boost: dict[str, Any] = {"level": level}
            if progress is not None:
                boost["progress"] = _compact_number(progress)
            boosts[boost_label] = boost
        if boosts:
            upgrades[cauldron_label] = boosts
    return upgrades


def _cauldron_p2w_summary(p2w: list[Any]) -> dict[str, Any]:
    """Return compact cauldron pay-to-win levels."""
    summary: dict[str, Any] = {}
    cauldron_levels = _list_value(p2w, 0)
    if isinstance(cauldron_levels, list):
        summary["cauldrons"] = _chunked_upgrade_levels(
            cauldron_levels,
            ("Speed", "New bubble", "Boost requirement"),
            CAULDRON_LABELS,
        )

    liquid_levels = _list_value(p2w, 1)
    if isinstance(liquid_levels, list):
        summary["liquids"] = _chunked_upgrade_levels(
            liquid_levels,
            ("Regen", "Capacity"),
            LIQUID_LABELS,
        )

    vial_levels = _list_value(p2w, 2)
    if isinstance(vial_levels, list):
        summary["vials"] = {
            "Attempts": _coerce_int(_list_value(vial_levels, 0)) or 0,
            "RNG": _coerce_int(_list_value(vial_levels, 1)) or 0,
        }
    attempts = _list_value(p2w, 5)
    if isinstance(attempts, list):
        summary["vial_attempts"] = {
            "current": _coerce_int(_list_value(attempts, 0)) or 0,
            "maximum": _coerce_int(_list_value(attempts, 1)) or 0,
        }
    return summary


def _chunked_upgrade_levels(
    values: list[Any],
    labels: tuple[str, ...],
    group_labels: Mapping[int, str],
) -> dict[str, Any]:
    """Return grouped upgrade levels from a flat list."""
    grouped: dict[str, Any] = {}
    width = len(labels)
    for index in range(0, len(values), width):
        group_index = index // width
        group: dict[str, int] = {}
        for offset, label in enumerate(labels):
            level = _coerce_int(_list_value(values, index + offset))
            if level is not None:
                group[label] = level
        if group:
            grouped[group_labels.get(group_index, f"Group {group_index + 1}")] = group
    return grouped


def _vote_ballot_summary(
    categories: list[Any],
    percentages: list[Any],
) -> dict[str, Any]:
    """Return selected and active vote ballot indexes."""
    selected = _coerce_int(_list_value(categories, 0))
    active = categories[1:]
    return {
        "selected_index": selected,
        "active_indexes": [
            index for value in active if (index := _coerce_int(value)) is not None
        ],
        "percentages": [
            _compact_number(value)
            for raw_value in percentages
            if (value := _coerce_float(raw_value)) is not None
        ],
    }


def _raw_system_presence_summary(
    raw_data: Mapping[str, Any],
    keys: tuple[str, ...],
) -> dict[str, Any]:
    """Return compact counts for raw world system fields that are present."""
    summary: dict[str, Any] = {}
    for key in keys:
        value = _maybe_json(raw_data.get(key))
        if isinstance(value, Mapping):
            summary[_clean_display_text(key)] = len(
                [item for item in value.values() if item not in (None, 0, "", [])]
            )
        elif isinstance(value, list):
            summary[_clean_display_text(key)] = len(
                [item for item in value if item not in (None, 0, "", [], {})]
            )
        elif value not in (None, 0, ""):
            summary[_clean_display_text(key)] = 1
    return summary


def _website_data_list(key: str) -> list[Any]:
    """Return a websiteData part when it is a list."""
    with suppress(WebsiteDataNotFoundError):
        data = load_default_website_data_part(key)
        if isinstance(data, list):
            return data
    return []


def _website_data_mapping(key: str) -> Mapping[str, Any]:
    """Return a websiteData part when it is a mapping."""
    with suppress(WebsiteDataNotFoundError):
        data = load_default_website_data_part(key)
        if isinstance(data, Mapping):
            return data
    return {}


def _item_data(raw_item: Any) -> Mapping[str, Any]:
    """Return websiteData item metadata for a raw item name."""
    raw_value = str(raw_item)
    items = _website_data_mapping("items")
    item = items.get(raw_value)
    return item if isinstance(item, Mapping) else {}


def _item_label(raw_item: Any) -> str:
    """Return an item display label for a raw item name."""
    if _is_blank_item(raw_item):
        return "Empty"
    item = _item_data(raw_item)
    display_name = item.get("displayName")
    if isinstance(display_name, str) and display_name:
        return _clean_display_text(display_name)
    return _clean_display_text(str(raw_item))


def _is_blank_item(value: Any) -> bool:
    """Return whether a raw item value means an empty slot."""
    return str(value).strip().lower() in {"", "blank", "none", "null", "0"}


def _companion_pet_names() -> dict[int, str]:
    """Return companion pet display names by index."""
    with suppress(WebsiteDataNotFoundError):
        companions = load_default_website_data_part("companions")
        if isinstance(companions, list):
            names: dict[int, str] = {}
            for index, companion in enumerate(companions):
                if not isinstance(companion, Mapping):
                    continue
                name = companion.get("name")
                if isinstance(name, str) and name:
                    names[index] = _clean_display_text(name)
            return names
    return {}


def _companion_pet_category(index: int) -> str:
    """Return the companion pet category for a companion index."""
    category_index = min(
        index // COMPANION_PET_CATEGORY_SIZE,
        len(COMPANION_PET_CATEGORIES) - 1,
    )
    return COMPANION_PET_CATEGORIES[category_index]


def _achievement_world_sizes() -> tuple[int, ...]:
    """Return achievement counts per world from websiteData when available."""
    with suppress(WebsiteDataNotFoundError):
        achievements = load_default_website_data_part("achievements")
        if isinstance(achievements, list):
            sizes = tuple(
                len(world)
                for world in achievements
                if isinstance(world, list) and world
            )
            if sizes:
                return sizes
    return (70, 70, 70, 70, 70, 70)


def _achievement_labels() -> dict[int, str]:
    """Return achievement labels by global index."""
    labels: dict[int, str] = {}
    with suppress(WebsiteDataNotFoundError):
        achievements = load_default_website_data_part("achievements")
        if isinstance(achievements, list):
            if all(isinstance(achievement, Mapping) for achievement in achievements):
                for index, achievement in enumerate(achievements):
                    name = achievement.get("name")
                    if isinstance(name, str) and name:
                        labels[index] = _clean_display_text(name)
                return labels

            index = 0
            for world in achievements:
                if not isinstance(world, list):
                    continue
                for achievement in world:
                    if isinstance(achievement, Mapping):
                        name = achievement.get("name")
                        if isinstance(name, str) and name:
                            labels[index] = _clean_display_text(name)
                    index += 1
    return labels


def _achievement_group_status(
    values: list[Any],
    *,
    labels: Mapping[int, str],
    label_offset: int,
    fallback_prefix: str = "Achievement",
) -> dict[str, Any]:
    """Return a compact achieved/progress summary for achievement values."""
    achieved = 0
    not_started = 0
    progress: dict[str, Any] = {}

    for index, raw_value in enumerate(values):
        value = _coerce_float(raw_value)
        if value is None:
            continue
        if value == -1:
            achieved += 1
            continue
        if value == 0:
            not_started += 1
            continue

        global_index = label_offset + index
        label = labels.get(global_index, f"{fallback_prefix} {index + 1}")
        progress[label] = _compact_number(value)

    details: dict[str, Any] = {
        "achieved": achieved,
        "not_started": not_started,
    }
    if progress:
        details["progress"] = progress
    return details


def _task_labels() -> dict[tuple[int, int], str]:
    """Return task labels keyed by world and task index."""
    labels: dict[tuple[int, int], str] = {}
    with suppress(WebsiteDataNotFoundError):
        tasks = load_default_website_data_part("tasks")
        if isinstance(tasks, list):
            for world_index, world_tasks in enumerate(tasks):
                if not isinstance(world_tasks, list):
                    continue
                for task_index, task in enumerate(world_tasks):
                    if isinstance(task, Mapping):
                        name = task.get("name")
                        if isinstance(name, str) and name:
                            labels[(world_index, task_index)] = _clean_display_text(
                                name
                            )
    return labels


def _task_breakpoints_for_world(world_index: int) -> list[list[Any]]:
    """Return task breakpoints for one world."""
    with suppress(WebsiteDataNotFoundError):
        tasks = load_default_website_data_part("tasks")
        if isinstance(tasks, list):
            world_tasks = _list_value(tasks, world_index)
            if isinstance(world_tasks, list):
                return [
                    task.get("breakpoints", []) if isinstance(task, Mapping) else []
                    for task in world_tasks
                ]
    return []


def _task_progress_percent(
    *,
    level: int,
    raw_progress: float | None,
    breakpoints: Any,
) -> int | float | None:
    """Return progress towards the next task level when breakpoints are known."""
    if raw_progress is None or not isinstance(breakpoints, list):
        return None
    if level >= len(breakpoints):
        return 100

    current_required = _coerce_float(_list_value(breakpoints, level - 1)) or 0.0
    next_required = _coerce_float(_list_value(breakpoints, level))
    if next_required is None or next_required <= current_required:
        return None

    progress = max(raw_progress - current_required, 0)
    needed = next_required - current_required
    return _compact_number(min((progress / needed) * 100, 100))


def _merit_metadata() -> tuple[dict[tuple[int, int], str], dict[tuple[int, int], Any]]:
    """Return merit labels and max levels keyed by world and merit index."""
    labels: dict[tuple[int, int], str] = {}
    max_levels: dict[tuple[int, int], Any] = {}
    with suppress(WebsiteDataNotFoundError):
        merits = load_default_website_data_part("merits")
        if isinstance(merits, list):
            for world_index, world_merits in enumerate(merits):
                if not isinstance(world_merits, list):
                    continue
                for merit_index, merit in enumerate(world_merits):
                    if not isinstance(merit, Mapping):
                        continue
                    label = _merit_label(merit, fallback=f"Merit {merit_index + 1}")
                    labels[(world_index, merit_index)] = label
                    total_levels = _coerce_int(merit.get("totalLevels"))
                    if total_levels is not None:
                        max_levels[(world_index, merit_index)] = total_levels
    return labels, max_levels


def _merit_label(merit: Mapping[str, Any], *, fallback: str) -> str:
    """Return a readable label for a taskboard merit."""
    desc_line = merit.get("descLine1")
    if isinstance(desc_line, str) and desc_line:
        return _clean_display_text(desc_line.replace("{", "").replace("}", ""))
    return fallback


def _world_label(index: int) -> str:
    """Return a stable world label for a zero-based world index."""
    return _list_value(list(TASK_WORLD_LABELS), index) or f"World {index + 1}"


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
    if website_data_key == "items":
        equipment_label = equipment_display_label(raw_value)
        if equipment_label:
            return equipment_label
    return _clean_display_text(raw_value)


def _clean_display_text(value: str) -> str:
    """Return websiteData display text in a Home Assistant friendly form."""
    return value.replace("_", " ").strip()


def _remove_empty_detail_values(details: Mapping[str, Any]) -> dict[str, Any]:
    """Drop empty detail values so entity attributes stay compact."""
    return {
        str(key): _compact_detail_value(value)
        for key, value in details.items()
        if value not in (None, "", [], {})
    }


def _compact_detail_value(value: Any) -> Any:
    """Recursively compact whole-number floats in parsed detail values."""
    if isinstance(value, float):
        return _compact_number(value)
    if isinstance(value, Mapping):
        return {
            str(key): _compact_detail_value(item)
            for key, item in value.items()
            if item not in (None, "", [], {})
        }
    if isinstance(value, list):
        return [_compact_detail_value(item) for item in value]
    return value


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
