"""Static Idleon game data maps used by the parser."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from contextlib import suppress
from functools import lru_cache
from typing import Any

from .website_data import WebsiteDataNotFoundError, load_default_website_data_part

# Source: examples/websiteData.json, classes[index].
# Placeholder values such as "Nope" and "Filler" are omitted.
CLASS_NAMES: dict[int, str] = {
    1: "Beginner",
    2: "Journeyman",
    3: "Maestro",
    4: "Voidwalker",
    5: "Infinilyte",
    6: "Rage_Basics",
    7: "Warrior",
    8: "Barbarian",
    9: "Squire",
    10: "Blood_Berserker",
    12: "Divine_Knight",
    14: "Death_Bringer",
    16: "Royal_Guardian",
    18: "Calm_Basics",
    19: "Archer",
    20: "Bowman",
    21: "Hunter",
    22: "Siege_Breaker",
    25: "Beast_Master",
    29: "Wind_Walker",
    30: "Savvy_Basics",
    31: "Mage",
    32: "Wizard",
    33: "Shaman",
    34: "Elemental_Sorcerer",
    35: "Spiritual_Monk",
    36: "Bubonic_Conjuror",
    40: "Arcane_Cultist",
    42: "Mining",
    43: "Smithing",
    44: "Chopping",
    45: "Fishing",
    46: "Alchemy",
    47: "Bug Catching",
    48: "Trapping",
    49: "Construction",
    50: "Worship",
    51: "Cooking",
    52: "Breeding",
    53: "Laboratory",
    54: "Sailing",
    55: "Divinity",
    56: "Gaming",
    57: "Farming",
    58: "Sneaking",
    59: "Summoning",
    60: "Spelunking",
    61: "Research",
    62: "Skill_3_Lol",
}

# Source: https://github.com/Morta1/IdleonToolbox/blob/main/data/website-data.json
# License: GPL-3.0, see https://github.com/Morta1/IdleonToolbox/blob/main/LICENSE
MAP_NAMES: dict[int, str] = {
    7: "Freefall_Caverns",
    216: "The_Hole",
    312: "Coralcave_Perimeter",
    325: "Pirate_Mess_Hall",
}

MONSTERS: dict[str, dict[str, str]] = {
    "AlienTree": {"name": "Alien_Tree", "afk_type": "CHOPPIN"},
    "BirchTree": {"name": "Birch_Tree", "afk_type": "CHOPPIN"},
    "Bravery_Monument": {"name": "Bravery", "afk_type": "Paying_Respect"},
    "Bug1": {"name": "Flies", "afk_type": "CATCHING"},
    "Bug10": {"name": "Dust_Mote", "afk_type": "CATCHING"},
    "Bug11": {"name": "Dream_Particulate", "afk_type": "CATCHING"},
    "Bug12": {"name": "Ladybug", "afk_type": "CATCHING"},
    "Bug13": {"name": "Firefly", "afk_type": "CATCHING"},
    "Bug14": {"name": "Fractalfly", "afk_type": "CATCHING"},
    "Bug15": {"name": "Litterbug", "afk_type": "CATCHING"},
    "Bug2": {"name": "Butterflies", "afk_type": "CATCHING"},
    "Bug3": {"name": "Sentient_Cereal", "afk_type": "CATCHING"},
    "Bug4": {"name": "Fruitflies", "afk_type": "CATCHING"},
    "Bug5": {"name": "Mosquisnow", "afk_type": "CATCHING"},
    "Bug6": {"name": "Flycicle", "afk_type": "CATCHING"},
    "Bug7": {"name": "Bumble_Bee", "afk_type": "CATCHING"},
    "Bug8": {"name": "Fairy", "afk_type": "CATCHING"},
    "Bug9": {"name": "Scarab", "afk_type": "CATCHING"},
    "Cooking": {"name": "Cooking", "afk_type": "COOKING"},
    "Copper": {"name": "Copper", "afk_type": "MINING"},
    "Dementia": {"name": "Dementia", "afk_type": "MINING"},
    "Divinity": {"name": "Divinity", "afk_type": "DIVINITY"},
    "Dreadlo": {"name": "Dreadlo", "afk_type": "MINING"},
    "FishBig": {"name": "Large_Fish", "afk_type": "FISHING"},
    "FishEquinox": {"name": "Equinox_Fish", "afk_type": "FISHING"},
    "FishMed": {"name": "Medium_Fish", "afk_type": "FISHING"},
    "FishSmall": {"name": "Small_Fish", "afk_type": "FISHING"},
    "ForestTree": {"name": "Forest_Tree", "afk_type": "CHOPPIN"},
    "Godshard": {"name": "Godshard", "afk_type": "MINING"},
    "Gold": {"name": "Gold", "afk_type": "MINING"},
    "Iron": {"name": "Iron", "afk_type": "MINING"},
    "JungleTree": {"name": "Jungle_Tree", "afk_type": "CHOPPIN"},
    "Justice_Monument": {"name": "Justice", "afk_type": "Paying_Respect"},
    "Laboratory": {"name": "Laboratory", "afk_type": "LABORATORY"},
    "Lustre": {"name": "Lustre", "afk_type": "MINING"},
    "Marble": {"name": "Marble", "afk_type": "MINING"},
    "Motherlode": {"name": "Motherlode", "afk_type": "MINING"},
    "MotherlodeFISH": {"name": "Trench_Fish", "afk_type": "FISHING"},
    "MotherlodeTREE": {"name": "Evertree", "afk_type": "CHOPPIN"},
    "Nothing": {"name": "_", "afk_type": "Nothing"},
    "OakTree": {"name": "Oak_Tree", "afk_type": "CHOPPIN"},
    "PalmTree": {"name": "Palm_Tree", "afk_type": "CHOPPIN"},
    "Plat": {"name": "Plat", "afk_type": "MINING"},
    "Prehistrium": {"name": "Prehistrium", "afk_type": "MINING"},
    "SaharanFoal": {"name": "Saharan_Foal", "afk_type": "CHOPPIN"},
    "Spelunking0": {"name": "Fearful_Tunnel", "afk_type": "SPELUNKING"},
    "Spelunking1": {"name": "Decaying_Crevasse", "afk_type": "SPELUNKING"},
    "Spelunking2": {"name": "Buried_Church", "afk_type": "SPELUNKING"},
    "Spelunking3": {"name": "One_Way_Opening", "afk_type": "SPELUNKING"},
    "Spelunking4": {"name": "Plunder_Cranny", "afk_type": "SPELUNKING"},
    "Spelunking5": {"name": "Kelp_Forest", "afk_type": "SPELUNKING"},
    "Starfire": {"name": "Starfire", "afk_type": "MINING"},
    "StumpTree": {"name": "Stump_Tree", "afk_type": "CHOPPIN"},
    "ToiletTree": {"name": "Toilet_Tree", "afk_type": "CHOPPIN"},
    "Tree10": {"name": "Dandelioli_Tree", "afk_type": "CHOPPIN"},
    "Tree11": {"name": "Equinox_Willow", "afk_type": "CHOPPIN"},
    "Tree12": {"name": "Bamboo", "afk_type": "CHOPPIN"},
    "Tree13": {"name": "Effervescent_Eucalyptus", "afk_type": "CHOPPIN"},
    "Tree14": {"name": "Ancient_Seaweed", "afk_type": "CHOPPIN"},
    "Tree7": {"name": "Wispy_Tree", "afk_type": "CHOPPIN"},
    "Tree8": {"name": "Cubed_Tree", "afk_type": "CHOPPIN"},
    "Tree9": {"name": "Maple_Tree", "afk_type": "CHOPPIN"},
    "Void": {"name": "Void", "afk_type": "MINING"},
    "Wisdom_Monument": {"name": "Wisdom", "afk_type": "Paying_Respect"},
    "caveB": {
        "name": "Gloomie_Mushroom",
        "afk_type": "FIGHTING",
    },
    "mushG": {
        "name": "Green_Mushroom",
        "afk_type": "FIGHTING",
    },
    "w7a12": {
        "name": "Coralcave_Guardian",
        "afk_type": "FIGHTING",
    },
    "w7b11": {
        "name": "Pirate_Deckhand",
        "afk_type": "FIGHTING",
    },
}

PLACEHOLDER_LABELS = {"", "0", "_", "error", "filler", "nope", "z"}
AFK_TYPE_SKILL_SLUGS = {
    "catching": "catching",
    "choppin": "choppin",
    "cooking": "cooking",
    "divinity": "divinity",
    "fishing": "fishing",
    "laboratory": "laboratory",
    "mining": "mining",
    "spelunking": "spelunking",
}
AFK_TYPE_ACTIVITY_FOLDERS = {
    "catching": "catching",
    "choppin": "chopping",
    "fishing": "fishing",
    "mining": "mining",
    "paying_respect": "monuments",
    "spelunking": "spelunking",
}
AFK_TARGET_ACTIVITY_ICON_ALIASES = {
    ("mining", "plat"): "platinum",
    ("paying_respect", "bravery"): "paying_respect",
    ("paying_respect", "justice"): "paying_respect",
    ("paying_respect", "wisdom"): "paying_respect",
}


def class_name_label(value: Any) -> str:
    """Return an Idleon class display label from a raw class identifier."""
    class_id = _coerce_int(value)
    if class_id is None:
        return "Unknown"

    class_name = _website_class_name(class_id) or CLASS_NAMES.get(class_id)
    if not _is_real_label(class_name):
        return f"Class {class_id}"
    return display_name(str(class_name))


def map_name_label(value: Any) -> str:
    """Return an Idleon map display label from a raw map identifier."""
    map_id = _coerce_int(value)
    if map_id is None:
        return "Unknown"

    map_name = _website_map_name(map_id) or MAP_NAMES.get(map_id)
    if not _is_real_label(map_name):
        return f"Map {map_id}"
    return display_name(str(map_name))


def afk_activity_label(value: Any) -> str:
    """Return a display activity for a raw Idleon AFK target."""
    if afk_target_is_idle(value):
        return "Nothing"

    monster = _afk_target_data(value)
    if not isinstance(monster, Mapping):
        return f"AFK target {value}"

    monster_name = monster.get("Name") or monster.get("name")
    afk_type = monster.get("AFKtype") or monster.get("afk_type")
    if _afk_type_is_idle(afk_type):
        return "Nothing"
    if not _is_real_label(afk_type):
        return (
            display_name(str(monster_name))
            if _is_real_label(monster_name)
            else (f"AFK target {value}")
        )
    if not _is_real_label(monster_name):
        return display_name(str(afk_type))

    return f"{display_name(str(afk_type))}: {display_name(str(monster_name))}"


def afk_target_monster(value: Any) -> Mapping[str, Any] | None:
    """Return monster data for an AFK target when the target is fighting."""
    monster = _afk_target_data(value)
    if not isinstance(monster, Mapping):
        return None

    afk_type = monster.get("AFKtype") or monster.get("afk_type")
    if _is_real_label(afk_type) and normalize_slug(str(afk_type)) != "fighting":
        return None
    return monster


def _afk_target_data(value: Any) -> Mapping[str, Any] | None:
    """Return raw websiteData or fallback data for an AFK target."""
    if value is None:
        return None

    target = str(value)
    monster = _website_monster(target) or MONSTERS.get(target)
    if not isinstance(monster, Mapping):
        return None
    return monster


def afk_target_monster_slug(value: Any) -> str | None:
    """Return the canonical monster name slug for a fighting AFK target."""
    monster = afk_target_monster(value)
    if not isinstance(monster, Mapping):
        return None

    monster_name = monster.get("Name") or monster.get("name")
    if not _is_real_label(monster_name):
        return None
    return normalize_slug(str(monster_name))


def afk_target_skill_slug(value: Any) -> str | None:
    """Return the canonical skill slug for a non-fighting AFK target."""
    monster = _afk_target_data(value)
    if not isinstance(monster, Mapping):
        return None

    afk_type = monster.get("AFKtype") or monster.get("afk_type")
    if not _is_real_label(afk_type):
        return None
    return AFK_TYPE_SKILL_SLUGS.get(normalize_slug(str(afk_type)))


def afk_target_activity_icon(value: Any) -> tuple[str, str] | None:
    """Return the activity asset folder and slug for a non-fighting AFK target."""
    monster = _afk_target_data(value)
    if not isinstance(monster, Mapping):
        return None

    afk_type = monster.get("AFKtype") or monster.get("afk_type")
    monster_name = monster.get("Name") or monster.get("name")
    if not _is_real_label(afk_type) or not _is_real_label(monster_name):
        return None

    afk_type_slug = normalize_slug(str(afk_type))
    folder = AFK_TYPE_ACTIVITY_FOLDERS.get(afk_type_slug)
    if not folder:
        return None

    target_slug = normalize_slug(str(monster_name))
    return folder, AFK_TARGET_ACTIVITY_ICON_ALIASES.get(
        (afk_type_slug, target_slug),
        target_slug,
    )


def afk_target_is_idle(value: Any) -> bool:
    """Return whether an AFK target represents no current activity."""
    if value is None:
        return True
    return normalize_slug(str(value)) in {"", "0", "nothing", "none", "idle"}


def display_name(value: str) -> str:
    """Return a user-facing label from an Idleon data key."""
    return value.replace("_", " ").title()


def normalize_slug(value: str) -> str:
    """Return a filesystem-safe canonical Idleon data slug."""
    normalized = re.sub(r"[\s_-]+", "_", value.lower())
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


@lru_cache(maxsize=1)
def _website_classes() -> Sequence[Any]:
    """Return split websiteData classes when available."""
    with suppress(WebsiteDataNotFoundError, OSError, ValueError, TypeError):
        classes = load_default_website_data_part("classes")
        if isinstance(classes, Sequence) and not isinstance(classes, str):
            return classes
    return ()


@lru_cache(maxsize=1)
def _website_map_names() -> Mapping[str, Any]:
    """Return split websiteData map names when available."""
    with suppress(WebsiteDataNotFoundError, OSError, ValueError, TypeError):
        map_names = load_default_website_data_part("mapNames")
        if isinstance(map_names, Mapping):
            return map_names
    return {}


@lru_cache(maxsize=1)
def _website_monsters() -> Mapping[str, Any]:
    """Return split websiteData monsters when available."""
    with suppress(WebsiteDataNotFoundError, OSError, ValueError, TypeError):
        monsters = load_default_website_data_part("monsters")
        if isinstance(monsters, Mapping):
            return monsters
    return {}


def _website_class_name(class_id: int) -> Any:
    """Return a raw class name from split websiteData."""
    classes = _website_classes()
    with suppress(IndexError):
        return classes[class_id]
    return None


def _website_map_name(map_id: int) -> Any:
    """Return a raw map name from split websiteData."""
    return _website_map_names().get(str(map_id))


def _website_monster(target: str) -> Any:
    """Return raw monster data from split websiteData."""
    return _website_monsters().get(target)


def _coerce_int(value: Any) -> int | None:
    """Coerce a raw value into an integer."""
    if isinstance(value, bool) or value is None:
        return None
    with suppress(TypeError, ValueError):
        return int(float(value))
    return None


def _is_real_label(value: Any) -> bool:
    """Return whether a websiteData label is usable."""
    if value is None:
        return False
    return str(value).strip().lower() not in PLACEHOLDER_LABELS


def _afk_type_is_idle(value: Any) -> bool:
    """Return whether an AFK type represents no current activity."""
    if value is None:
        return False
    return normalize_slug(str(value)) in {"nothing", "none", "idle"}
