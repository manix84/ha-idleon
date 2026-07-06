"""Tests for websiteData-backed Idleon label lookups."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.idleon.idleon_data import game_maps
from custom_components.idleon.idleon_data.website_data import WebsiteDataNotFoundError


@pytest.fixture(autouse=True)
def clear_website_data_caches():
    """Clear websiteData lookup caches around each test."""
    game_maps._website_classes.cache_clear()
    game_maps._website_map_names.cache_clear()
    game_maps._website_monsters.cache_clear()
    yield
    game_maps._website_classes.cache_clear()
    game_maps._website_map_names.cache_clear()
    game_maps._website_monsters.cache_clear()


def test_game_maps_use_split_website_data_labels(monkeypatch) -> None:
    """Test label helpers use the same indexes as TypeScript @website-data."""

    def load_part(key: str) -> Any:
        if key == "classes":
            return ["0", "Beginner", "Journeyman", "Maestro", "Voidwalker"]
        if key == "mapNames":
            return {"7": "Freefall_Caverns", "216": "The_Hole"}
        if key == "monsters":
            return {
                "mushG": {
                    "AFKtype": "FIGHTING",
                    "Name": "Green_Mushroom",
                }
            }
        raise WebsiteDataNotFoundError(key)

    monkeypatch.setattr(game_maps, "load_default_website_data_part", load_part)

    assert game_maps.class_name_label(4) == "Voidwalker"
    assert game_maps.map_name_label(7) == "Freefall Caverns"
    assert game_maps.afk_activity_label("mushG") == "Fighting: Green Mushroom"
    assert game_maps.afk_target_monster_slug("mushG") == "green_mushroom"


def test_game_maps_fall_back_to_packaged_labels(monkeypatch) -> None:
    """Test lookup helpers still work without local split websiteData."""

    def load_part(key: str) -> Any:
        raise WebsiteDataNotFoundError(key)

    monkeypatch.setattr(game_maps, "load_default_website_data_part", load_part)

    assert game_maps.class_name_label(14) == "Death Bringer"
    assert game_maps.map_name_label(216) == "The Hole"
    assert game_maps.afk_activity_label("caveB") == "Fighting: Gloomie Mushroom"
    assert game_maps.afk_target_monster_slug("w7b11") == "pirate_deckhand"
    assert game_maps.afk_activity_label("0") == "Nothing"
    assert game_maps.afk_activity_label("_") == "Nothing"
    assert game_maps.afk_activity_label("Nothing") == "Nothing"
    assert game_maps.afk_activity_label("Copper") == "Mining: Copper"
    assert game_maps.afk_activity_label("OakTree") == "Choppin: Oak Tree"
    assert game_maps.afk_activity_label("FishSmall") == "Fishing: Small Fish"
    assert game_maps.afk_activity_label("Bug1") == "Catching: Flies"
    assert game_maps.afk_target_skill_slug("Copper") == "mining"
    assert game_maps.afk_target_skill_slug("OakTree") == "choppin"
    assert game_maps.afk_target_skill_slug("FishSmall") == "fishing"
    assert game_maps.afk_target_skill_slug("Bug1") == "catching"
    assert game_maps.afk_target_activity_icon("Copper") == ("mining", "copper")
    assert game_maps.afk_target_activity_icon("Plat") == ("mining", "platinum")
    assert game_maps.afk_target_activity_icon("OakTree") == ("chopping", "oak_tree")
    assert game_maps.afk_target_activity_icon("FishSmall") == (
        "fishing",
        "small_fish",
    )
    assert game_maps.afk_target_activity_icon("Bug1") == ("catching", "flies")
    assert game_maps.afk_target_activity_icon("Bravery_Monument") == (
        "monuments",
        "paying_respect",
    )
    assert game_maps.afk_target_is_idle("0")
    assert game_maps.afk_target_is_idle(None)
    assert not game_maps.afk_target_is_idle("w7b11")


def test_game_maps_only_return_monster_slug_for_fighting_targets(monkeypatch) -> None:
    """Test non-fighting AFK targets do not resolve to monster asset slugs."""

    def load_part(key: str) -> Any:
        if key == "monsters":
            return {
                "tree": {
                    "AFKtype": "CHOPPIN",
                    "Name": "Oak_Tree",
                }
            }
        raise WebsiteDataNotFoundError(key)

    monkeypatch.setattr(game_maps, "load_default_website_data_part", load_part)

    assert game_maps.afk_activity_label("tree") == "Choppin: Oak Tree"
    assert game_maps.afk_target_monster_slug("tree") is None
