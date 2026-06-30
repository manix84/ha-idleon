"""Static Idleon game data maps used by the parser."""

from __future__ import annotations

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
    216: "The_Hole",
    312: "Coralcave_Perimeter",
    325: "Pirate_Mess_Hall",
}

MONSTERS: dict[str, dict[str, str]] = {
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
