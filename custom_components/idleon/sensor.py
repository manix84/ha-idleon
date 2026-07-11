"""Sensor entities for HA Idleon."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import STATIC_URL_PATH, IdleonRuntimeData
from .const import DOMAIN, NAME
from .coordinator import IdleonDataUpdateCoordinator
from .idleon_data.equipment import (
    MAIN_EQUIPMENT_SLOTS,
    TOOL_EQUIPMENT_SLOTS,
    equipment_display_label,
)
from .idleon_data.equipment import (
    equipment_asset_path as equipment_asset_relative_path,
)
from .idleon_data.game_maps import (
    afk_target_activity_icon,
    afk_target_is_idle,
    afk_target_monster_slug,
    afk_target_skill_slug,
)
from .models import IdleonCharacter
from .utils.number_format import (
    decimal_to_ha_number,
    format_decimal_grouped,
    format_decimal_scientific,
    idleon_money_parts,
    idleon_number_parts,
    idleon_raw_value,
    parse_idleon_decimal,
)

ASSETS_PATH = Path(__file__).with_name("assets")
CHARACTER_STAT_SENSOR_KEYS = {
    "character_strength": "strength",
    "character_agility": "agility",
    "character_wisdom": "wisdom",
    "character_luck": "luck",
}
SKILL_ASSET_ALIASES = {
    "chopping": "choppin",
}
EXCLUDED_STORAGE_CAPACITY_ENTITIES = frozenset({"Quests", "Statues"})
TROPHY_DISPLAY_LABELS = {
    "Trophy1": "King of Food",
    "Trophy10": "Critter Baron",
    "Trophy11": "YumYum Sheriff",
    "Trophy12": "Megalodon",
    "Trophy13": "Club Maestro",
    "Trophy14": "Beach Bro",
    "Trophy15": "Frost Prince",
    "Trophy16": "Idle Skiller",
    "Trophy17": "One of the Divine",
    "Trophy18": "Master of Nothing",
    "Trophy19": "Nebula Royal",
    "Trophy2": "Lucky Lad",
    "Trophy20": "Luckier Lad",
    "Trophy21": "Baller",
    "Trophy22": "Gladiator",
    "Trophy23": "Heroic Spirit",
    "Trophy24": "Nine Dart Finish",
    "Trophy25": "Luckiest Lad",
    "Trophy3": "Club Member",
    "Trophy4": "I Made This Game",
    "Trophy5": "Dice Dynamo",
    "Trophy6": "Blunder Hero",
    "Trophy7": "Original Gamer",
    "Trophy8": "Trailblazer",
    "Trophy9": "Ultra Unboxer",
    "TrophyReplica0": "Replica Trophy",
}
NAME_TAG_DISPLAY_LABELS = {
    "EquipmentNametag1": "Riftwalker Nametag",
    "EquipmentNametag10": "3rd Anniversary IdleOn Nametag",
    "EquipmentNametag11": "Nightshade Nametag",
    "EquipmentNametag12": "Megafeather Nametag",
    "EquipmentNametag13": "Timeless Nametag",
    "EquipmentNametag14": "Snowflake Nametag",
    "EquipmentNametag15": "Frostyman Nametag",
    "EquipmentNametag16": "Lovely Day Nametag",
    "EquipmentNametag17": "Spectacular 4th Year Nametag",
    "EquipmentNametag18": "4th Anniversary IdleOn Nametag",
    "EquipmentNametag19": "Aethermoon Nametag",
    "EquipmentNametag2": "Lava's Awesome Nametag",
    "EquipmentNametag20": "Deadbones Nametag",
    "EquipmentNametag21": "Treasure Nametag",
    "EquipmentNametag22": "Tome Apprentice Nametag",
    "EquipmentNametag23": "Tome Journeyman Nametag",
    "EquipmentNametag24": "Tome Expert Nametag",
    "EquipmentNametag25": "Tome Elite Nametag",
    "EquipmentNametag26": "Tome Pro Nametag",
    "EquipmentNametag27": "Tome Master Nametag",
    "EquipmentNametag28": "Tome Legend Nametag",
    "EquipmentNametag29": "Reliquarium Nametag",
    "EquipmentNametag3": "Balling Nametag",
    "EquipmentNametag30": "Cropfall Nametag",
    "EquipmentNametag31": "Gingerbread Nametag",
    "EquipmentNametag32": "Sweet Chocolate Nametag",
    "EquipmentNametag33": "Pot of Gold Nametag",
    "EquipmentNametag34": "Emerald Nametag",
    "EquipmentNametag35": "5th Anniversary IdleOn Nametag",
    "EquipmentNametag36": "Wonderful 5th Year Nametag",
    "EquipmentNametag37": "Grand Egg Nametag",
    "EquipmentNametag4": "Vman Nametag",
    "EquipmentNametag41": "All That Glitters Nametag",
    "EquipmentNametag5": "Spring Flowers Nametag",
    "EquipmentNametag6b": "Trash Tuna Nametag",
    "EquipmentNametag7": "Island Adventurer Nametag",
    "EquipmentNametag8": "Summer Shovel Nametag",
    "EquipmentNametag9": "Falloween Nametag",
}
TROPHY_ASSET_STEMS = {
    "Trophy1": "king_of_food",
    "Trophy10": "critter_baron",
    "Trophy11": "yumyum_sheriff",
    "Trophy12": "megalodon",
    "Trophy13": "club_maestro",
    "Trophy14": "beach_bro",
    "Trophy15": "frost_prince",
    "Trophy16": "idle_skiller",
    "Trophy17": "one_of_the_divine",
    "Trophy18": "master_of_nothing",
    "Trophy19": "nebula_royal",
    "Trophy2": "lucky_lad",
    "Trophy20": "luckier_lad",
    "Trophy21": "baller",
    "Trophy22": "gladiator",
    "Trophy23": "heroic_spirit",
    "Trophy24": "nine_dart_finish",
    "Trophy25": "luckiest_lad",
    "Trophy3": "club_member",
    "Trophy4": "i_made_this_game",
    "Trophy5": "dice_dynamo",
    "Trophy6": "blunder_hero",
    "Trophy7": "original_gamer",
    "Trophy8": "trailblazer",
    "Trophy9": "ultra_unboxer",
    "TrophyReplica0": "replica",
}
NAME_TAG_ASSET_STEMS = {
    "EquipmentNametag1": "riftwalker",
    "EquipmentNametag10": "3rd_anniversary_idleon",
    "EquipmentNametag11": "nightshade",
    "EquipmentNametag12": "megafeather",
    "EquipmentNametag13": "timeless",
    "EquipmentNametag14": "snowflake",
    "EquipmentNametag15": "frostyman",
    "EquipmentNametag16": "lovely_day",
    "EquipmentNametag17": "spectacular_4th_year",
    "EquipmentNametag18": "4th_anniversary_idleon",
    "EquipmentNametag19": "aethermoon",
    "EquipmentNametag2": "lavas_awesome",
    "EquipmentNametag20": "deadbones",
    "EquipmentNametag21": "treasure",
    "EquipmentNametag22": "tome_apprentice",
    "EquipmentNametag23": "tome_journeyman",
    "EquipmentNametag24": "tome_expert",
    "EquipmentNametag25": "tome_elite",
    "EquipmentNametag26": "tome_pro",
    "EquipmentNametag27": "tome_master",
    "EquipmentNametag28": "tome_legend",
    "EquipmentNametag29": "reliquarium",
    "EquipmentNametag3": "balling",
    "EquipmentNametag30": "cropfall",
    "EquipmentNametag31": "gingerbread",
    "EquipmentNametag32": "sweet_chocolate",
    "EquipmentNametag33": "pot_of_gold",
    "EquipmentNametag34": "emerald",
    "EquipmentNametag35": "5th_anniversary_idleon",
    "EquipmentNametag36": "wonderful_5th_year",
    "EquipmentNametag37": "grand_egg",
    "EquipmentNametag4": "vman",
    "EquipmentNametag41": "all_that_glitters",
    "EquipmentNametag5": "spring_flowers",
    "EquipmentNametag6b": "trash_tuna",
    "EquipmentNametag7": "island_adventurer",
    "EquipmentNametag8": "summer_shovel",
    "EquipmentNametag9": "falloween",
}


@dataclass(frozen=True, kw_only=True)
class IdleonAccountSensorEntityDescription(SensorEntityDescription):
    """Description for an account sensor."""

    value_fn: Callable[[IdleonDataUpdateCoordinator], Any]
    detail_keys: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class IdleonCharacterSensorEntityDescription(SensorEntityDescription):
    """Description for a character sensor."""

    value_fn: Callable[[IdleonCharacter], Any]
    detail_keys: tuple[str, ...] = ()
    equipment_raw_detail_key: str | None = None


LATER_WORLD_ACCOUNT_DETAIL_KEYS = (
    "world_4_cooking",
    "world_4_breeding",
    "world_4_laboratory",
    "world_4_rift",
    "world_4_tome",
    "world_5_sailing",
    "world_5_divinity",
    "world_5_gaming",
    "world_5_hole",
    "world_5_slab",
    "world_6_farming",
    "world_6_sneaking",
    "world_6_summoning",
    "world_6_beanstalk",
    "world_6_emperor",
    "world_7_spelunking",
    "world_7_research",
    "world_7_gallery",
    "world_7_legend_talents",
    "world_7_coral_reef",
    "world_7_zenith_market",
    "world_7_clam_work",
    "world_7_advice_fish",
    "world_7_minehead",
    "world_7_glimbo",
    "world_7_sushi_station",
    "world_7_the_button",
)


def _equipment_sensor_description(
    slot_key: str,
) -> IdleonCharacterSensorEntityDescription:
    """Return an entity description for one fixed equipment slot."""
    raw_key = f"{slot_key}_raw"
    return IdleonCharacterSensorEntityDescription(
        key=f"character_{slot_key}",
        translation_key=f"character_{slot_key}",
        value_fn=lambda character, label_key=slot_key, raw_detail_key=raw_key: (
            _equipment_detail_value(character, label_key, raw_detail_key, "None")
        ),
        detail_keys=(raw_key,),
        equipment_raw_detail_key=raw_key,
    )


EQUIPMENT_CHARACTER_SENSOR_DESCRIPTIONS = tuple(
    _equipment_sensor_description(slot.key)
    for slot in (*MAIN_EQUIPMENT_SLOTS, *TOOL_EQUIPMENT_SLOTS)
    if slot.key not in {"equipped_trophy", "equipped_name_tag"}
)

COLOSSEUM_SCORE_SENSORS = (
    ("whimsical", "Whimsical"),
    ("astro", "Astro"),
    ("molten", "Molten"),
    ("chillsnap", "Chillsnap"),
    ("sandstone", "Sandstone"),
    ("dewdrop", "Dewdrop"),
)
COLOSSEUM_SCORE_SENSOR_PICTURES = {
    f"account_colosseum_score_{slug}": f"{STATIC_URL_PATH}/colosseum/{slug}.png"
    for slug, _label in COLOSSEUM_SCORE_SENSORS
}

ACCOUNT_CURRENCY_SENSORS = (
    ("cluster", "Cluster"),
    ("event", "Event"),
    ("guild", "Guild"),
    ("shimmer", "Shimmer"),
    ("trash", "Trash"),
)
ACCOUNT_CURRENCY_SENSOR_PICTURES = {
    f"account_currency_{slug}": f"{STATIC_URL_PATH}/currency/{slug}.png"
    for slug, _label in ACCOUNT_CURRENCY_SENSORS
}

ACCOUNT_BOSS_KEY_SENSORS = (
    ("forest_villa", "Forest Villa Keys"),
    ("efaunts_tomb", "Efaunt's Tomb Keys"),
    ("chizoars_cavern", "Chizoar's Cavern Keys"),
    ("trolls_enclave", "Troll's Enclave Keys"),
    ("kruks_volcano", "Kruk's Volcano Keys"),
)
ACCOUNT_BOSS_KEY_SENSOR_PICTURES = {
    f"account_boss_key_{slug}": f"{STATIC_URL_PATH}/boss_keys/{slug}.png"
    for slug, _label in ACCOUNT_BOSS_KEY_SENSORS
}
ACCOUNT_STATUE_SENSORS = (
    ("power", "Power"),
    ("speed", "Speed"),
    ("mining", "Mining"),
    ("feasty", "Feasty"),
    ("health", "Health"),
    ("kachow", "Kachow"),
    ("lumberbob", "Lumberbob"),
    ("thicc_skin", "Thicc Skin"),
    ("oceanman", "Oceanman"),
    ("ol_reliable", "Ol Reliable"),
    ("exp_book", "Exp Book"),
    ("anvil", "Anvil"),
    ("cauldron", "Cauldron"),
    ("beholder", "Beholder"),
    ("bullseye", "Bullseye"),
    ("box", "Box"),
    ("twosoul", "Twosoul"),
    ("ehexpee", "EhExPee"),
    ("seesaw", "Seesaw"),
    ("pecunia", "Pecunia"),
    ("mutton", "Mutton"),
    ("egg", "Egg"),
    ("battleaxe", "Battleaxe"),
    ("spiral", "Spiral"),
    ("boat", "Boat"),
    ("compost", "Compost"),
    ("stealth", "Stealth"),
    ("essence", "Essence"),
    ("villager", "Villager"),
    ("dragon_warrior", "Dragon Warrior"),
    ("spelunky", "Spelunky"),
    ("reef_coral", "Reef Coral"),
)
ACCOUNT_STATUE_LABEL_BY_KEY = {
    f"account_statue_{slug}": label for slug, label in ACCOUNT_STATUE_SENSORS
}


def _colosseum_score_sensor_description(
    slug: str,
    label: str,
) -> IdleonAccountSensorEntityDescription:
    """Return an account sensor description for one colosseum score."""
    return IdleonAccountSensorEntityDescription(
        key=f"account_colosseum_score_{slug}",
        translation_key=f"account_colosseum_score_{slug}",
        value_fn=lambda coordinator, score_label=label: (
            _account_detail_value_from_mapping(
                coordinator,
                "colosseum_scores",
                score_label,
                0,
            )
        ),
    )


def _currency_sensor_description(
    slug: str,
    label: str,
) -> IdleonAccountSensorEntityDescription:
    """Return an account sensor description for one currency value."""
    return IdleonAccountSensorEntityDescription(
        key=f"account_currency_{slug}",
        translation_key=f"account_currency_{slug}",
        value_fn=lambda coordinator, currency_label=label: (
            _account_detail_value_from_mapping(
                coordinator,
                "currencies",
                currency_label,
                0,
            )
        ),
    )


def _boss_key_sensor_description(
    slug: str,
    label: str,
) -> IdleonAccountSensorEntityDescription:
    """Return an account sensor description for one boss key value."""
    return IdleonAccountSensorEntityDescription(
        key=f"account_boss_key_{slug}",
        translation_key=f"account_boss_key_{slug}",
        value_fn=lambda coordinator, key_label=label: (
            _account_detail_value_from_mapping(
                coordinator,
                "currencies",
                key_label,
                0,
            )
        ),
    )


def _statue_sensor_description(
    slug: str,
    label: str,
) -> IdleonAccountSensorEntityDescription:
    """Return an account sensor description for one statue level."""
    return IdleonAccountSensorEntityDescription(
        key=f"account_statue_{slug}",
        translation_key=f"account_statue_{slug}",
        value_fn=lambda coordinator, statue_label=label: _account_statue_level(
            coordinator, statue_label
        ),
    )


ACCOUNT_SENSOR_DESCRIPTIONS = (
    IdleonAccountSensorEntityDescription(
        key="account_total_level",
        translation_key="account_total_level",
        value_fn=lambda coordinator: coordinator.data.total_level,
    ),
    IdleonAccountSensorEntityDescription(
        key="account_character_count",
        translation_key="account_character_count",
        value_fn=lambda coordinator: coordinator.data.character_count,
    ),
    IdleonAccountSensorEntityDescription(
        key="account_gems",
        translation_key="account_gems",
        value_fn=lambda coordinator: coordinator.data.gems,
    ),
    IdleonAccountSensorEntityDescription(
        key="account_pet_crystals",
        translation_key="account_pet_crystals",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "pet_crystals",
            0,
        ),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_jade",
        translation_key="account_jade",
        value_fn=lambda coordinator: _account_large_number_scaled_state(
            coordinator,
            "jade",
        ),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_tome_points",
        translation_key="account_tome_points",
        value_fn=lambda coordinator: _account_detail_value_from_mapping(
            coordinator,
            "world_4_tome",
            "score",
            0,
        ),
        detail_keys=("world_4_tome",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_last_updated",
        translation_key="account_last_updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: coordinator.last_successful_update,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    IdleonAccountSensorEntityDescription(
        key="account_highest_character_level",
        translation_key="account_highest_character_level",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "highest_character_level",
            0,
        ),
        detail_keys=("highest_level_character", "class_counts"),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_total_skill_level",
        translation_key="account_total_skill_level",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "total_skill_level",
            0,
        ),
        detail_keys=("class_counts",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_max_damage",
        translation_key="account_max_damage",
        value_fn=lambda coordinator: _account_max_damage_state(coordinator),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_money",
        translation_key="account_money",
        value_fn=lambda coordinator: _account_money_state(coordinator),
        detail_keys=("money_breakdown",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_green_stacks",
        translation_key="account_green_stacks",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "green_stack_count",
            0,
        ),
        detail_keys=("green_stack_sample",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_slab_items_obtained",
        translation_key="account_slab_items_obtained",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "slab_items_obtained",
            0,
        ),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_achievements_completed",
        translation_key="account_achievements_completed",
        value_fn=lambda coordinator: _account_detail_value(
            coordinator,
            "achievements_completed",
            0,
        ),
        detail_keys=("achievement_status",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_currencies",
        translation_key="account_currencies",
        value_fn=lambda coordinator: _account_detail_count(coordinator, "currencies"),
        detail_keys=("currencies",),
    ),
    *(
        _currency_sensor_description(slug, label)
        for slug, label in ACCOUNT_CURRENCY_SENSORS
    ),
    *(
        _boss_key_sensor_description(slug, label)
        for slug, label in ACCOUNT_BOSS_KEY_SENSORS
    ),
    IdleonAccountSensorEntityDescription(
        key="account_shrine_levels",
        translation_key="account_shrine_levels",
        value_fn=lambda coordinator: _account_detail_sum(
            coordinator,
            "shrine_levels",
        ),
        detail_keys=("shrine_levels",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_statue_levels",
        translation_key="account_statue_levels",
        value_fn=lambda coordinator: _account_detail_sum(
            coordinator,
            "statue_levels",
        ),
        detail_keys=("statue_levels",),
    ),
    *(
        _statue_sensor_description(slug, label)
        for slug, label in ACCOUNT_STATUE_SENSORS
    ),
    IdleonAccountSensorEntityDescription(
        key="account_colosseum_scores",
        translation_key="account_colosseum_scores",
        value_fn=lambda coordinator: _account_detail_sum(
            coordinator,
            "colosseum_scores",
        ),
        detail_keys=("colosseum_scores",),
    ),
    *(
        _colosseum_score_sensor_description(slug, label)
        for slug, label in COLOSSEUM_SCORE_SENSORS
    ),
    IdleonAccountSensorEntityDescription(
        key="account_minigame_scores",
        translation_key="account_minigame_scores",
        value_fn=lambda coordinator: _account_detail_sum(
            coordinator,
            "minigame_scores",
        ),
        detail_keys=("minigame_scores",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_progress_totals",
        translation_key="account_progress_totals",
        value_fn=lambda coordinator: _account_progress_metric_count(
            coordinator,
        ),
        detail_keys=("progress_totals",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_pets",
        translation_key="account_pets",
        value_fn=lambda coordinator: _account_companion_pet_owned_count(
            coordinator,
        ),
        detail_keys=("pets",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_task_levels",
        translation_key="account_task_levels",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "task_levels",
        ),
        detail_keys=("task_levels",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_taskboard_merits",
        translation_key="account_taskboard_merits",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "taskboard_merits",
        ),
        detail_keys=("taskboard_merits",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_taskboard_unlocks",
        translation_key="account_taskboard_unlocks",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "taskboard_unlocks",
        ),
        detail_keys=("taskboard_unlocks",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_1_anvil",
        translation_key="account_world_1_anvil",
        value_fn=lambda coordinator: _account_world_1_forge_slot_count(
            coordinator,
        ),
        detail_keys=("world_1_anvil",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_1_bribes",
        translation_key="account_world_1_bribes",
        value_fn=lambda coordinator: _account_world_1_bribes_purchased_count(
            coordinator,
        ),
        detail_keys=("world_1_bribes",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_1_stamps",
        translation_key="account_world_1_stamps",
        value_fn=lambda coordinator: _account_world_1_stamp_level_total(
            coordinator,
        ),
        detail_keys=("world_1_stamps",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_summaries",
        translation_key="account_world_summaries",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_summaries",
        ),
        detail_keys=("world_summaries",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_cauldron",
        translation_key="account_world_2_cauldron",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_2_cauldron",
        ),
        detail_keys=("world_2_cauldron",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_vials",
        translation_key="account_world_2_vials",
        value_fn=lambda coordinator: _account_detail_count(
            coordinator,
            "world_2_vials",
        ),
        detail_keys=("world_2_vials",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_bubbles",
        translation_key="account_world_2_bubbles",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_2_bubbles",
        ),
        detail_keys=("world_2_bubbles",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_sigils",
        translation_key="account_world_2_sigils",
        value_fn=lambda coordinator: _account_detail_count(
            coordinator,
            "world_2_sigils",
        ),
        detail_keys=("world_2_sigils",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_vote_ballots",
        translation_key="account_world_2_vote_ballots",
        value_fn=lambda coordinator: _account_detail_count(
            coordinator,
            "world_2_vote_ballots",
        ),
        detail_keys=("world_2_vote_ballots",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_2_killroy",
        translation_key="account_world_2_killroy",
        value_fn=lambda coordinator: _account_world_2_killroy_rooms_available(
            coordinator
        ),
        detail_keys=("world_2_killroy",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_printer",
        translation_key="account_world_3_printer",
        value_fn=lambda coordinator: _account_detail_value_from_mapping(
            coordinator,
            "world_3_printer",
            "total_printed",
        ),
        detail_keys=("world_3_printer",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_refinery",
        translation_key="account_world_3_refinery",
        value_fn=lambda coordinator: _account_detail_value_from_mapping(
            coordinator,
            "world_3_refinery",
            "refined_salt_total",
        ),
        detail_keys=("world_3_refinery",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_atom_collider",
        translation_key="account_world_3_atom_collider",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_atom_collider",
        ),
        detail_keys=("world_3_atom_collider",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_equinox",
        translation_key="account_world_3_equinox",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_equinox",
        ),
        detail_keys=("world_3_equinox",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_buildings",
        translation_key="account_world_3_buildings",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_buildings",
        ),
        detail_keys=("world_3_buildings",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_death_note",
        translation_key="account_world_3_death_note",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_death_note",
        ),
        detail_keys=("world_3_death_note",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_worship",
        translation_key="account_world_3_worship",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_worship",
        ),
        detail_keys=("world_3_worship",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_prayers",
        translation_key="account_world_3_prayers",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_prayers",
        ),
        detail_keys=("world_3_prayers",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_traps",
        translation_key="account_world_3_traps",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_traps",
        ),
        detail_keys=("world_3_traps",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_salt_lick",
        translation_key="account_world_3_salt_lick",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_salt_lick",
        ),
        detail_keys=("world_3_salt_lick",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_construction",
        translation_key="account_world_3_construction",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_construction",
        ),
        detail_keys=("world_3_construction",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_armor_smithy",
        translation_key="account_world_3_armor_smithy",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_armor_smithy",
        ),
        detail_keys=("world_3_armor_smithy",),
    ),
    IdleonAccountSensorEntityDescription(
        key="account_world_3_hat_rack",
        translation_key="account_world_3_hat_rack",
        value_fn=lambda coordinator: _account_detail_nested_count(
            coordinator,
            "world_3_hat_rack",
        ),
        detail_keys=("world_3_hat_rack",),
    ),
    *(
        IdleonAccountSensorEntityDescription(
            key=f"account_{detail_key}",
            translation_key=f"account_{detail_key}",
            value_fn=lambda coordinator, detail_key=detail_key: (
                _account_detail_nested_count(coordinator, detail_key)
            ),
            detail_keys=(detail_key,),
        )
        for detail_key in LATER_WORLD_ACCOUNT_DETAIL_KEYS
    ),
)

CHARACTER_SENSOR_DESCRIPTIONS = (
    IdleonCharacterSensorEntityDescription(
        key="character_level",
        translation_key="character_level",
        value_fn=lambda character: character.level,
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_class",
        translation_key="character_class",
        value_fn=lambda character: character.character_class,
        detail_keys=("raw_class_id",),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_current_map",
        translation_key="character_current_map",
        value_fn=lambda character: character.current_map,
        detail_keys=("raw_map_id",),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_current_activity",
        translation_key="character_current_activity",
        value_fn=lambda character: character.current_activity,
        detail_keys=("afk_target",),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_afk_hours",
        translation_key="character_afk_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda character: character.afk_hours,
        detail_keys=("afk_seconds", "raw_afk_value", "afk_reference_timestamp"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_inventory_slots_used",
        translation_key="character_inventory_slots_used",
        value_fn=lambda character: _detail_value(
            character,
            "inventory_slots_used",
            0,
        ),
        detail_keys=(
            "inventory_slots_total",
            "inventory_slots_usable",
            "inventory_slots_free",
            "inventory_sample",
        ),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_inventory_slots_free",
        translation_key="character_inventory_slots_free",
        value_fn=lambda character: _detail_value(
            character,
            "inventory_slots_free",
            0,
        ),
        detail_keys=(
            "inventory_slots_total",
            "inventory_slots_usable",
            "inventory_slots_used",
            "inventory_sample",
        ),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_highest_skill",
        translation_key="character_highest_skill",
        value_fn=lambda character: _highest_skill_name(character),
        detail_keys=("highest_skill", "total_skill_level", "skill_levels", "stats"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_total_skill_level",
        translation_key="character_total_skill_level",
        value_fn=lambda character: _detail_value(
            character,
            "total_skill_level",
            0,
        ),
        detail_keys=("skill_levels", "highest_skill"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_money",
        translation_key="character_money",
        value_fn=lambda character: _character_money_state(character),
        detail_keys=("money",),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_selected_trophy",
        translation_key="character_selected_trophy",
        value_fn=lambda character: _cosmetic_detail_value(
            character,
            "selected_trophy",
            "selected_trophy_raw",
            "None",
        ),
        detail_keys=("selected_trophy_raw",),
        equipment_raw_detail_key="selected_trophy_raw",
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_selected_name_tag",
        translation_key="character_selected_name_tag",
        value_fn=lambda character: _cosmetic_detail_value(
            character,
            "selected_name_tag",
            "selected_name_tag_raw",
            "None",
        ),
        detail_keys=("selected_name_tag_raw",),
        equipment_raw_detail_key="selected_name_tag_raw",
    ),
    *EQUIPMENT_CHARACTER_SENSOR_DESCRIPTIONS,
    IdleonCharacterSensorEntityDescription(
        key="character_strength",
        translation_key="character_strength",
        value_fn=lambda character: _stat_value(character, "strength"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_agility",
        translation_key="character_agility",
        value_fn=lambda character: _stat_value(character, "agility"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_wisdom",
        translation_key="character_wisdom",
        value_fn=lambda character: _stat_value(character, "wisdom"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_luck",
        translation_key="character_luck",
        value_fn=lambda character: _stat_value(character, "luck"),
    ),
    IdleonCharacterSensorEntityDescription(
        key="character_equipped_items",
        translation_key="character_equipped_items",
        value_fn=lambda character: _detail_value(
            character,
            "equipped_item_count",
            0,
        ),
        detail_keys=(
            "equipped_items",
            "equipped_tool_count",
            "equipped_tools",
            "equipped_food_count",
            "equipped_food",
            "attack_loadout",
        ),
        entity_registry_enabled_default=False,
    ),
)

NUMERIC_ACCOUNT_SENSOR_KEYS = frozenset(
    description.key
    for description in ACCOUNT_SENSOR_DESCRIPTIONS
    if description.key
    not in {
        "account_last_updated",
    }
)
TEXT_CHARACTER_SENSOR_KEYS = {
    "character_class",
    "character_current_map",
    "character_current_activity",
    "character_highest_skill",
    "character_selected_trophy",
    "character_selected_name_tag",
    *(description.key for description in EQUIPMENT_CHARACTER_SENSOR_DESCRIPTIONS),
}
NUMERIC_CHARACTER_SENSOR_KEYS = frozenset(
    description.key
    for description in CHARACTER_SENSOR_DESCRIPTIONS
    if description.key not in TEXT_CHARACTER_SENSOR_KEYS
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[IdleonRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Idleon sensors for a config entry."""
    coordinator = entry.runtime_data.coordinator
    added_character_sensor_ids: set[str] = set()
    added_storage_sensor_ids: set[tuple[str, str]] = set()

    def _new_character_entities() -> list[SensorEntity]:
        entities: list[SensorEntity] = []
        for character in coordinator.data.characters:
            if character.character_id not in added_character_sensor_ids:
                added_character_sensor_ids.add(character.character_id)
                entities.extend(
                    IdleonCharacterSensor(entry, coordinator, character, description)
                    for description in CHARACTER_SENSOR_DESCRIPTIONS
                )

            for storage_type in _character_storage_capacities(character):
                sensor_id = (character.character_id, storage_type)
                if sensor_id in added_storage_sensor_ids:
                    continue
                added_storage_sensor_ids.add(sensor_id)
                entities.append(
                    IdleonCharacterStorageCapacitySensor(
                        entry,
                        coordinator,
                        character,
                        storage_type,
                    )
                )
        return entities

    def _add_new_character_entities() -> None:
        if entities := _new_character_entities():
            async_add_entities(entities)

    entities: list[SensorEntity] = [
        IdleonAccountSensor(entry, coordinator, description)
        for description in ACCOUNT_SENSOR_DESCRIPTIONS
    ]
    entities.extend(_new_character_entities())
    async_add_entities(entities)
    entry.async_on_unload(coordinator.async_add_listener(_add_new_character_entities))


class IdleonAccountSensor(CoordinatorEntity[IdleonDataUpdateCoordinator], SensorEntity):
    """Account-level Idleon sensor."""

    entity_description: IdleonAccountSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry[IdleonRuntimeData],
        coordinator: IdleonDataUpdateCoordinator,
        description: IdleonAccountSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _account_device_info(entry)
        if description.key in NUMERIC_ACCOUNT_SENSOR_KEYS:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return dynamic compact suffix units for large account numbers."""
        if self.entity_description.key == "account_money":
            return _large_number_unit(_account_money_raw(self.coordinator))
        if self.entity_description.key == "account_max_damage":
            return _large_number_unit(_account_max_damage_raw(self.coordinator))
        if self.entity_description.key == "account_jade":
            return _large_number_unit(_account_jade_raw(self.coordinator))
        return self.entity_description.native_unit_of_measurement

    @property
    def entity_picture(self) -> str | None:
        """Return an entity picture for account sensors with visual assets."""
        if self.entity_description.key == "account_character_count":
            return f"{STATIC_URL_PATH}/character.png"
        if self.entity_description.key == "account_highest_character_level":
            return f"{STATIC_URL_PATH}/highest_character_level.png"
        if self.entity_description.key == "account_green_stacks":
            return f"{STATIC_URL_PATH}/green_stack.png"
        if self.entity_description.key == "account_max_damage":
            return f"{STATIC_URL_PATH}/damage_indicators/damage_blue_m.png"
        if self.entity_description.key == "account_gems":
            return f"{STATIC_URL_PATH}/currency/gem.png"
        if self.entity_description.key == "account_pet_crystals":
            return f"{STATIC_URL_PATH}/pet_crystal.png"
        if self.entity_description.key == "account_jade":
            return f"{STATIC_URL_PATH}/currency/jade.png"
        if self.entity_description.key == "account_pets":
            return f"{STATIC_URL_PATH}/companions.png"
        if self.entity_description.key == "account_shrine_levels":
            return f"{STATIC_URL_PATH}/shrine.png"
        if self.entity_description.key == "account_statue_levels":
            return f"{STATIC_URL_PATH}/statue.png"
        if self.entity_description.key == "account_tome_points":
            return f"{STATIC_URL_PATH}/world/tome/tome.png"
        if picture := _account_statue_entity_picture(
            self.coordinator,
            self.entity_description.key,
        ):
            return picture
        if self.entity_description.key == "account_money":
            return _money_entity_picture(_account_money_raw(self.coordinator))
        if picture := COLOSSEUM_SCORE_SENSOR_PICTURES.get(
            self.entity_description.key,
        ):
            return picture
        if picture := ACCOUNT_CURRENCY_SENSOR_PICTURES.get(
            self.entity_description.key,
        ):
            return picture
        if picture := ACCOUNT_BOSS_KEY_SENSOR_PICTURES.get(
            self.entity_description.key,
        ):
            return picture
        return None

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return account timestamp details where useful."""
        if self.entity_description.key == "account_last_updated":
            attributes = {
                "source_updated_at": (
                    self.coordinator.data.source_updated_at.isoformat()
                    if self.coordinator.data.source_updated_at
                    else None
                ),
                "last_successful_update": (
                    self.coordinator.last_successful_update.isoformat()
                    if self.coordinator.last_successful_update
                    else None
                ),
            }
            return _remove_none_attributes(attributes)

        if self.entity_description.key == "account_money":
            attributes = _money_attributes(_account_money_raw(self.coordinator))
            money_breakdown = _money_breakdown_attributes(self.coordinator)
            if money_breakdown:
                attributes["money_breakdown"] = money_breakdown
            return attributes

        if self.entity_description.key == "account_max_damage":
            return _number_attributes(_account_max_damage_raw(self.coordinator))

        if self.entity_description.key == "account_jade":
            return _number_attributes(_account_jade_raw(self.coordinator))

        if self.entity_description.key in ACCOUNT_STATUE_LABEL_BY_KEY:
            return _account_statue_attributes(
                self.coordinator,
                self.entity_description.key,
            )

        if not self.entity_description.detail_keys or not self.coordinator.data.details:
            return None
        attributes = {
            key: _normalize_attribute_value(self.coordinator.data.details[key])
            for key in self.entity_description.detail_keys
            if key in self.coordinator.data.details
        }
        return _normalize_attribute_value(attributes) or None


class IdleonCharacterSensor(
    CoordinatorEntity[IdleonDataUpdateCoordinator],
    SensorEntity,
):
    """Character-level Idleon sensor."""

    entity_description: IdleonCharacterSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry[IdleonRuntimeData],
        coordinator: IdleonDataUpdateCoordinator,
        character: IdleonCharacter,
        description: IdleonCharacterSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._character_id = character.character_id
        self._attr_unique_id = (
            f"{entry.entry_id}_{_slugify(character.character_id)}_{description.key}"
        )
        self._attr_device_info = _character_device_info(entry, character)
        if description.key in NUMERIC_CHARACTER_SENSOR_KEYS:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self._character is not None

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        character = self._character
        if character is None:
            return None
        value = self.entity_description.value_fn(character)
        if isinstance(value, datetime):
            return value
        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return dynamic compact suffix units for large character numbers."""
        if self.entity_description.key == "character_money":
            character = self._character
            if character is None:
                return None
            return _large_number_unit(_character_money_raw(character))
        return self.entity_description.native_unit_of_measurement

    @property
    def entity_picture(self) -> str | None:
        """Return an entity picture for sensors with visual assets."""
        character = self._character
        if character is None:
            return None
        if self.entity_description.key == "character_class":
            return _class_entity_picture(character.character_class)
        if self.entity_description.key == "character_current_activity":
            return _activity_entity_picture(character)
        if self.entity_description.key == "character_highest_skill":
            return _highest_skill_entity_picture(character)
        if self.entity_description.equipment_raw_detail_key:
            return _equipment_entity_picture(
                character,
                self.entity_description.equipment_raw_detail_key,
            )
        if stat_key := CHARACTER_STAT_SENSOR_KEYS.get(self.entity_description.key):
            return _stat_entity_picture(stat_key)
        if self.entity_description.key != "character_money":
            return None
        return _money_entity_picture(_character_money_raw(character))

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return details relevant to this character sensor."""
        if not self.entity_description.detail_keys:
            return None
        character = self._character
        if character is None or not character.details:
            return None
        if self.entity_description.key == "character_money":
            return _money_attributes(_character_money_raw(character))
        attributes = _select_detail_attributes(
            character.details,
            self.entity_description.detail_keys,
        )
        return _normalize_attribute_value(attributes) or None

    @property
    def _character(self) -> IdleonCharacter | None:
        """Return the current character model."""
        return next(
            (
                character
                for character in self.coordinator.data.characters
                if character.character_id == self._character_id
            ),
            None,
        )


class IdleonCharacterStorageCapacitySensor(
    CoordinatorEntity[IdleonDataUpdateCoordinator],
    SensorEntity,
):
    """Character storage pouch capacity sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        entry: ConfigEntry[IdleonRuntimeData],
        coordinator: IdleonDataUpdateCoordinator,
        character: IdleonCharacter,
        storage_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._character_id = character.character_id
        self._storage_type = storage_type
        self._attr_name = f"{storage_type} storage capacity"
        self._attr_unique_id = (
            f"{entry.entry_id}_{_slugify(character.character_id)}_"
            f"character_storage_capacity_{_slugify(storage_type)}"
        )
        self._attr_device_info = _character_device_info(entry, character)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self._storage_capacity is not None

    @property
    def native_value(self) -> int | None:
        """Return the current maximum storage capacity."""
        details = self._storage_capacity
        if not details:
            return None
        value = details.get("maximum_capacity")
        return value if isinstance(value, int) else None

    @property
    def entity_picture(self) -> str | None:
        """Return the largest acquired pouch picture."""
        details = self._storage_capacity
        if not details:
            return None
        asset_name = details.get("largest_pouch_asset")
        if not isinstance(asset_name, str) or not asset_name:
            return None
        if not (ASSETS_PATH / asset_name).is_file():
            return None
        return f"{STATIC_URL_PATH}/{asset_name}"

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return capacity and pouch metadata."""
        details = self._storage_capacity
        if not details:
            return None
        return _normalize_attribute_value(details) or None

    @property
    def _character(self) -> IdleonCharacter | None:
        """Return the current character model."""
        return next(
            (
                character
                for character in self.coordinator.data.characters
                if character.character_id == self._character_id
            ),
            None,
        )

    @property
    def _storage_capacity(self) -> Mapping[str, Any] | None:
        """Return the current storage capacity details."""
        character = self._character
        if character is None:
            return None
        storage_capacities = _character_storage_capacities(character)
        details = storage_capacities.get(self._storage_type)
        return details if isinstance(details, Mapping) else None


def _account_device_info(entry: ConfigEntry[IdleonRuntimeData]) -> DeviceInfo:
    """Return account device information."""
    return DeviceInfo(
        identifiers={(DOMAIN, _account_device_identifier(entry))},
        name="Legends of Idleon Account",
        manufacturer="Legends of Idleon",
        model=NAME,
    )


def _character_device_info(
    entry: ConfigEntry[IdleonRuntimeData],
    character: IdleonCharacter,
) -> DeviceInfo:
    """Return character device information."""
    return DeviceInfo(
        identifiers={(DOMAIN, _character_device_identifier(entry, character))},
        name=_character_device_name(character),
        manufacturer="Legends of Idleon",
        model=character.character_class,
        via_device=(DOMAIN, _account_device_identifier(entry)),
    )


def _character_device_name(character: IdleonCharacter) -> str:
    """Return a readable character device name."""
    match = re.fullmatch(r"Character\s+(\d+)(?:\s+-\s+(.+))?", character.name)
    if match:
        character_number = match.group(1)
        character_name = match.group(2)
        if character_name:
            return f"Idleon Character {character_number} - {character_name}"
        return f"Idleon Character {character_number}"

    match = re.fullmatch(r"character_(\d+)", character.character_id)
    if match:
        character_number = int(match.group(1)) + 1
        return f"Idleon Character {character_number} - {character.name}"

    return f"Idleon Character - {character.name}"


def _account_device_identifier(entry: ConfigEntry[IdleonRuntimeData]) -> str:
    """Return the account device identifier."""
    return f"{entry.entry_id}_account"


def _character_device_identifier(
    entry: ConfigEntry[IdleonRuntimeData],
    character: IdleonCharacter,
) -> str:
    """Return a character device identifier."""
    return f"{entry.entry_id}_{_slugify(character.character_id)}"


def _slugify(value: str) -> str:
    """Create a stable entity-safe identifier."""
    slug = "".join(
        character.lower() if character.isalnum() else "_" for character in value
    )
    return "_".join(part for part in slug.split("_") if part)


def _select_detail_attributes(
    details: Mapping[str, Any],
    keys: tuple[str, ...],
) -> dict[str, Any]:
    """Return selected character detail attributes."""
    return {key: details[key] for key in keys if key in details}


def _remove_none_attributes(attributes: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return compact attributes without empty timestamp values."""
    compact_attributes = {
        key: value for key, value in attributes.items() if value is not None
    }
    return compact_attributes or None


def _detail_value(
    character: IdleonCharacter,
    key: str,
    default: Any = None,
) -> Any:
    """Return a single parsed character detail value."""
    return character.details.get(key, default)


def _cosmetic_detail_value(
    character: IdleonCharacter,
    label_key: str,
    raw_key: str,
    default: Any = None,
) -> Any:
    """Return a human-readable cosmetic label with raw-ID fallback support."""
    return _equipment_detail_value(character, label_key, raw_key, default)


def _equipment_detail_value(
    character: IdleonCharacter,
    label_key: str,
    raw_key: str,
    default: Any = None,
) -> Any:
    """Return a human-readable equipment label with raw-ID fallback support."""
    label = character.details.get(label_key)
    raw_value = character.details.get(raw_key)
    if isinstance(label, str) and label and label != raw_value:
        return label
    if isinstance(raw_value, str):
        return equipment_display_label(raw_value, default)
    if isinstance(label, str):
        return equipment_display_label(label, default)
    return default


def _cosmetic_display_label(raw_item: str, default: Any = None) -> Any:
    """Return a display label for a known cosmetic raw ID."""
    return equipment_display_label(raw_item, default)


def _character_storage_capacities(
    character: IdleonCharacter,
) -> Mapping[str, Any]:
    """Return parsed storage capacity details for a character."""
    value = character.details.get("storage_capacities")
    if not isinstance(value, Mapping):
        return {}
    return {
        storage_type: details
        for storage_type, details in value.items()
        if storage_type not in EXCLUDED_STORAGE_CAPACITY_ENTITIES
    }


def _account_detail_value(
    coordinator: IdleonDataUpdateCoordinator,
    key: str,
    default: Any = None,
) -> Any:
    """Return a single parsed account detail value."""
    return coordinator.data.details.get(key, default)


def _account_detail_count(
    coordinator: IdleonDataUpdateCoordinator,
    key: str,
) -> int:
    """Return the number of values in a grouped account detail."""
    value = coordinator.data.details.get(key)
    if isinstance(value, Mapping):
        return len(value)
    return 0


def _account_detail_nested_count(
    coordinator: IdleonDataUpdateCoordinator,
    key: str,
) -> int:
    """Return the number of nested values in a grouped account detail."""
    value = coordinator.data.details.get(key)
    if not isinstance(value, Mapping):
        return 0

    total = 0
    for detail_value in value.values():
        if isinstance(detail_value, Mapping):
            total += len(detail_value)
        else:
            total += 1
    return total


def _account_progress_metric_count(
    coordinator: IdleonDataUpdateCoordinator,
) -> int | None:
    """Return the number of account progress metrics currently parsed."""
    value = coordinator.data.details.get("progress_totals")
    if not isinstance(value, Mapping):
        return None
    return len(value)


def _account_companion_pet_owned_count(
    coordinator: IdleonDataUpdateCoordinator,
) -> int | None:
    """Return the total owned companion pet count."""
    value = coordinator.data.details.get("pets")
    if not isinstance(value, Mapping):
        return None

    total = 0
    found_pet = False
    for category in value.values():
        if not isinstance(category, Mapping):
            continue
        for pet_value in category.values():
            owned = _owned_count_from_pet_value(pet_value)
            if owned is None:
                continue
            found_pet = True
            total += owned
    return total if found_pet else None


def _owned_count_from_pet_value(value: Any) -> int | None:
    """Return owned count from a pet value like '<tradeable>/<owned>'."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        owned_text = value.rsplit("/", maxsplit=1)[-1].strip()
        try:
            return int(owned_text)
        except ValueError:
            return None
    if isinstance(value, Mapping):
        for key in ("owned", "count", "unlocked"):
            owned = value.get(key)
            if isinstance(owned, int):
                return owned
            if isinstance(owned, str):
                try:
                    return int(owned)
                except ValueError:
                    continue
    return None


def _account_world_1_forge_slot_count(
    coordinator: IdleonDataUpdateCoordinator,
) -> int | None:
    """Return the number of active World 1 forge slots."""
    anvil = coordinator.data.details.get("world_1_anvil")
    if not isinstance(anvil, Mapping):
        return None
    slots = anvil.get("slots")
    if not isinstance(slots, Mapping):
        return None
    return len(slots)


def _account_world_1_bribes_purchased_count(
    coordinator: IdleonDataUpdateCoordinator,
) -> int | None:
    """Return the number of purchased World 1 bribes."""
    bribes = coordinator.data.details.get("world_1_bribes")
    if not isinstance(bribes, Mapping):
        return None

    purchased_count = 0
    found_bribe = False
    for bribe in bribes.values():
        if not isinstance(bribe, Mapping):
            continue
        found_bribe = True
        if str(bribe.get("price")).lower() == "purchased":
            purchased_count += 1
    return purchased_count if found_bribe else None


def _account_world_1_stamp_level_total(
    coordinator: IdleonDataUpdateCoordinator,
) -> int | None:
    """Return the total level of all parsed World 1 stamps."""
    stamps = coordinator.data.details.get("world_1_stamps")
    if not isinstance(stamps, Mapping):
        return None

    total = 0
    found_stamp = False
    for category in stamps.values():
        if not isinstance(category, Mapping):
            continue
        for stamp in category.values():
            if not isinstance(stamp, Mapping):
                continue
            level = stamp.get("current_level")
            if not isinstance(level, int):
                continue
            found_stamp = True
            total += level
    return total if found_stamp else None


def _account_detail_value_from_mapping(
    coordinator: IdleonDataUpdateCoordinator,
    detail_key: str,
    value_key: str,
    default: Any = 0,
) -> Any:
    """Return a single value from a grouped account detail."""
    value = coordinator.data.details.get(detail_key)
    if not isinstance(value, Mapping):
        return default
    return value.get(value_key, default)


def _account_large_number_scaled_state(
    coordinator: IdleonDataUpdateCoordinator,
    detail_key: str,
) -> int | float | None:
    """Return an account detail as a graphable compact numeric mantissa."""
    raw_value = coordinator.data.details.get(detail_key)
    if raw_value is None:
        return None
    return _large_number_scaled_state(idleon_raw_value(raw_value))


def _account_detail_sum(
    coordinator: IdleonDataUpdateCoordinator,
    key: str,
) -> int | float:
    """Return the numeric sum of values in a grouped account detail."""
    value = coordinator.data.details.get(key)
    if not isinstance(value, Mapping):
        return 0

    total = 0.0
    for detail_value in value.values():
        if isinstance(detail_value, int | float):
            total += detail_value
            continue
        try:
            total += float(detail_value)
        except TypeError, ValueError:
            continue
    if total.is_integer():
        return int(total)
    return round(total, 2)


def _account_statue_level(
    coordinator: IdleonDataUpdateCoordinator,
    label: str,
) -> int | float:
    """Return the current account-wide statue level."""
    details = _account_statue_details(coordinator, label)
    if isinstance(details, Mapping):
        level = details.get("level")
        if isinstance(level, int | float):
            return level

    statue_levels = coordinator.data.details.get("statue_levels")
    if isinstance(statue_levels, Mapping):
        value = statue_levels.get(label)
        if isinstance(value, int | float):
            return value
        try:
            return int(value)
        except TypeError, ValueError:
            return 0
    return 0


def _account_statue_attributes(
    coordinator: IdleonDataUpdateCoordinator,
    entity_key: str,
) -> Mapping[str, Any] | None:
    """Return per-statue level progress attributes."""
    label = ACCOUNT_STATUE_LABEL_BY_KEY.get(entity_key)
    if label is None:
        return None

    details = _account_statue_details(coordinator, label)
    if not isinstance(details, Mapping):
        return None

    attributes = {
        "statues_banked": details.get("statues_banked"),
        "statues_needed_for_next_level": details.get("statues_needed_for_next_level"),
        "statue_version": details.get("statue_version"),
        "progress_to_next_level_percent": details.get("progress_to_next_level_percent"),
        "raw_statue_version_id": details.get("statue_version_id"),
    }
    return _remove_none_attributes(_normalize_attribute_value(attributes) or {})


def _account_statue_entity_picture(
    coordinator: IdleonDataUpdateCoordinator,
    entity_key: str,
) -> str | None:
    """Return the version-aware statue entity picture."""
    label = ACCOUNT_STATUE_LABEL_BY_KEY.get(entity_key)
    if label is None:
        return None

    details = _account_statue_details(coordinator, label)
    if isinstance(details, Mapping):
        asset_slug = details.get("asset_slug")
        if isinstance(asset_slug, str) and asset_slug:
            return f"{STATIC_URL_PATH}/statue/{asset_slug}.png"

    return f"{STATIC_URL_PATH}/statue/{_slugify(label)}.png"


def _account_statue_details(
    coordinator: IdleonDataUpdateCoordinator,
    label: str,
) -> Mapping[str, Any] | None:
    """Return detailed statue attributes for a label."""
    statue_details = coordinator.data.details.get("statue_details")
    if not isinstance(statue_details, Mapping):
        return None
    details = statue_details.get(label)
    return details if isinstance(details, Mapping) else None


def _account_money_state(
    coordinator: IdleonDataUpdateCoordinator,
) -> int | float | None:
    """Return account money as a graphable compact numeric mantissa."""
    return _large_number_scaled_state(_account_money_raw(coordinator))


def _account_money_raw(coordinator: IdleonDataUpdateCoordinator) -> str:
    """Return exact account money as a raw copper string."""
    value = coordinator.data.details.get("raw_money")
    if value is None:
        value = coordinator.data.details.get("total_money", 0)
    return idleon_raw_value(value)


def _account_max_damage_state(
    coordinator: IdleonDataUpdateCoordinator,
) -> int | float | None:
    """Return account max damage as a graphable compact numeric mantissa."""
    return _large_number_scaled_state(_account_max_damage_raw(coordinator))


def _account_max_damage_raw(coordinator: IdleonDataUpdateCoordinator) -> str:
    """Return exact account max damage as a raw value string."""
    progress_totals = coordinator.data.details.get("progress_totals")
    if not isinstance(progress_totals, Mapping):
        return "0"
    return idleon_raw_value(progress_totals.get("Highest Damage", 0))


def _character_money_state(character: IdleonCharacter) -> int | float | None:
    """Return character money as a graphable compact numeric mantissa."""
    return _large_number_scaled_state(_character_money_raw(character))


def _character_money_raw(character: IdleonCharacter) -> str:
    """Return exact character money as a raw copper string."""
    return idleon_raw_value(character.details.get("money", 0))


def _account_jade_raw(coordinator: IdleonDataUpdateCoordinator) -> str:
    """Return exact Jade as a raw string."""
    return idleon_raw_value(coordinator.data.details.get("jade", 0))


def _large_number_scaled_state(raw_value: str) -> int | float | None:
    """Return the compact mantissa as a Home Assistant numeric state."""
    decimal_value = parse_idleon_decimal(raw_value)
    if decimal_value is None:
        return None
    mantissa = parse_idleon_decimal(idleon_number_parts(raw_value).mantissa)
    if mantissa is None:
        return None
    return decimal_to_ha_number(mantissa)


def _large_number_unit(raw_value: str) -> str | None:
    """Return the compact suffix as a Home Assistant unit."""
    decimal_value = parse_idleon_decimal(raw_value)
    if decimal_value is None:
        return None
    return idleon_number_parts(raw_value).suffix or None


def _money_attributes(raw_value: str) -> dict[str, str]:
    """Return standard formatted money attributes."""
    formatted_money = idleon_money_parts(raw_value)
    formatted_number = idleon_number_parts(raw_value)
    source_raw_value = idleon_raw_value(raw_value)
    return _number_attributes(raw_value) | {
        "raw_value": source_raw_value,
        "coin_tier_formatted": formatted_money.formatted,
        "coin_tier": formatted_money.coin_tier,
        "coin_tier_value": formatted_money.coin_tier_value,
        "formatted_number": formatted_number.formatted,
    }


def _number_attributes(raw_value: str) -> dict[str, str]:
    """Return standard formatted number attributes."""
    formatted_number = idleon_number_parts(raw_value)
    source_raw_value = idleon_raw_value(raw_value)
    attributes = {
        "raw_value": source_raw_value,
        "formatted_number": formatted_number.formatted,
        "compact_value": formatted_number.formatted,
        "number_suffix": formatted_number.suffix,
        "number_mantissa": formatted_number.mantissa,
    }
    decimal_value = parse_idleon_decimal(raw_value)
    if decimal_value is not None:
        attributes["formatted_value"] = format_decimal_grouped(decimal_value)
        attributes["scientific_value"] = format_decimal_scientific(decimal_value)
    return attributes


def _money_entity_picture(raw_value: str) -> str:
    """Return the image URL for the current money coin tier."""
    formatted_money = idleon_money_parts(raw_value)
    coin_slug = formatted_money.coin_tier.lower().replace(" ", "_")
    return f"{STATIC_URL_PATH}/coins/{coin_slug}.png"


def _class_entity_picture(character_class: str) -> str | None:
    """Return the image URL for a character class icon."""
    class_slug = _slugify(character_class)
    if not class_slug:
        return None
    class_icons = sorted((ASSETS_PATH / "classes").glob(f"*/{class_slug}_icon.png"))
    if not class_icons:
        return None
    class_icon = class_icons[0]
    return f"{STATIC_URL_PATH}/{class_icon.relative_to(ASSETS_PATH).as_posix()}"


def _stat_entity_picture(stat_key: str) -> str | None:
    """Return the image URL for a character stat icon."""
    stat_icon = ASSETS_PATH / "stats" / f"{stat_key}.png"
    if not stat_icon.is_file():
        return None
    return f"{STATIC_URL_PATH}/{stat_icon.relative_to(ASSETS_PATH).as_posix()}"


def _highest_skill_entity_picture(character: IdleonCharacter) -> str | None:
    """Return the image URL for a character's highest skill icon."""
    highest_skill = character.details.get("highest_skill")
    if not isinstance(highest_skill, Mapping):
        return None
    skill_name = highest_skill.get("name")
    if not isinstance(skill_name, str):
        return None
    return _skill_entity_picture(skill_name)


def _skill_entity_picture(skill_name: str) -> str | None:
    """Return the image URL for a skill icon."""
    skill_slug = SKILL_ASSET_ALIASES.get(_slugify(skill_name), _slugify(skill_name))
    if not skill_slug:
        return None
    skill_icon = ASSETS_PATH / "skills" / f"{skill_slug}.png"
    if not skill_icon.is_file():
        return None
    return f"{STATIC_URL_PATH}/{skill_icon.relative_to(ASSETS_PATH).as_posix()}"


def _equipment_entity_picture(
    character: IdleonCharacter, raw_detail_key: str
) -> str | None:
    """Return the image URL for a selected equipment cosmetic."""
    raw_item = character.details.get(raw_detail_key)
    if not isinstance(raw_item, str):
        return None

    asset_path = _equipment_asset_path(raw_item)
    if asset_path is None:
        return None
    return f"{STATIC_URL_PATH}/{asset_path.relative_to(ASSETS_PATH).as_posix()}"


def _equipment_asset_path(raw_item: str) -> Path | None:
    """Return the asset path for a known equipped item raw ID."""
    relative_path = equipment_asset_relative_path(raw_item)
    if not relative_path:
        return None
    path = ASSETS_PATH / relative_path
    if path.is_file():
        return path
    return None


def _unique_strings(*values: str | None) -> tuple[str, ...]:
    """Return unique non-empty strings in insertion order."""
    return tuple(dict.fromkeys(value for value in values if value))


def _activity_entity_picture(character: IdleonCharacter) -> str | None:
    """Return the image URL for the current AFK activity."""
    afk_target = character.details.get("afk_target")
    monster_slug = afk_target_monster_slug(afk_target)
    if monster_slug:
        monster_icons = sorted(
            (ASSETS_PATH / "monsters").glob(f"???_{monster_slug}.png")
        )
    elif afk_target_is_idle(afk_target):
        monster_icons = [ASSETS_PATH / "monsters" / "000_nothing.png"]
    else:
        activity_picture = _activity_target_entity_picture(afk_target)
        if activity_picture:
            return activity_picture
        skill_slug = afk_target_skill_slug(afk_target)
        if skill_slug:
            return _skill_entity_picture(skill_slug)
        return None

    if not monster_icons:
        return None
    monster_icon = monster_icons[0]
    if not monster_icon.is_file():
        return None
    return f"{STATIC_URL_PATH}/{monster_icon.relative_to(ASSETS_PATH).as_posix()}"


def _activity_target_entity_picture(afk_target: Any) -> str | None:
    """Return the image URL for a specific non-fighting AFK target."""
    activity_icon = afk_target_activity_icon(afk_target)
    if activity_icon is None:
        return None
    folder, slug = activity_icon
    icon_path = ASSETS_PATH / "activity" / folder / f"{slug}.png"
    if not icon_path.is_file():
        return None
    return f"{STATIC_URL_PATH}/{icon_path.relative_to(ASSETS_PATH).as_posix()}"


def _money_breakdown_attributes(
    coordinator: IdleonDataUpdateCoordinator,
) -> dict[str, str] | None:
    """Return money breakdown values as exact raw-value strings."""
    money_breakdown = coordinator.data.details.get("money_breakdown")
    if not isinstance(money_breakdown, Mapping):
        return None
    return {str(key): idleon_raw_value(value) for key, value in money_breakdown.items()}


def _account_world_2_killroy_rooms_available(
    coordinator: IdleonDataUpdateCoordinator,
) -> int:
    """Return parsed Killroy room count for the World 2 Killroy sensor state."""
    value = coordinator.data.details.get("world_2_killroy")
    if not isinstance(value, Mapping):
        return 0
    rooms_available = value.get("rooms_available")
    if isinstance(rooms_available, int | float):
        return int(rooms_available)
    return 0


def _stat_value(character: IdleonCharacter, key: str) -> int:
    """Return a single parsed character stat value."""
    stats = character.details.get("stats")
    if not isinstance(stats, Mapping):
        return 0
    value = stats.get(key)
    if isinstance(value, int | float):
        return int(value)
    return 0


def _highest_skill_name(character: IdleonCharacter) -> str:
    """Return the character's highest parsed skill name."""
    highest_skill = character.details.get("highest_skill")
    if isinstance(highest_skill, Mapping):
        name = highest_skill.get("name")
        level = highest_skill.get("level")
        if name and level is not None:
            return f"{name} ({level})"
    return "Unknown"


def _normalize_attribute_value(value: Any) -> Any:
    """Return Home Assistant friendly attributes with integral floats compacted."""
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    if isinstance(value, Mapping):
        return {key: _normalize_attribute_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_attribute_value(item) for item in value]
    return value
