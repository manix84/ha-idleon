"""Static Idleon game data maps used by the parser."""

from __future__ import annotations

# Source: https://github.com/Corbeno/idleon-data/blob/main/maps/classNames.json
# License: MIT, package metadata at https://github.com/Corbeno/idleon-data
CLASS_NAMES: dict[int, str] = {
    1: "Beginner",
    2: "Journeyman",
    3: "Maestro",
    4: "Virtuoso",
    5: "Infinilyte",
    6: "Rage Basics",
    7: "Warrior",
    8: "Barbarian",
    9: "Squire",
    10: "Blood Berserker",
    11: "Death Bringer",
    12: "Divine Knight",
    13: "Royal Guardian",
    14: "Filler",
    15: "Filler",
    16: "Filler",
    17: "Filler",
    18: "Calm Basics",
    19: "Archer",
    20: "Bowman",
    21: "Hunter",
    22: "Siege Breaker",
    23: "Mayheim",
    24: "Wind Walker",
    25: "Beast Master",
    26: "Filler",
    27: "Filler",
    28: "Filler",
    29: "Filler",
    30: "Savvy Basics",
    31: "Mage",
    32: "Wizard",
    33: "Shaman",
    34: "Elemental Sorcerer",
    35: "Spiritual Monk",
    36: "Bubonic Conjuror",
    37: "Arcane Cultist",
    38: "Filler",
    39: "Filler",
    40: "Filler",
    41: "Filler",
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
