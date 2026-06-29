"""Flexible parser for early Idleon account JSON exports."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from ..models import IdleonAccount, IdleonCharacter
from .exceptions import IdleonInvalidSchema


def parse_idleon_account(raw_data: Any) -> IdleonAccount:
    """Parse raw JSON into a normalized Idleon account model."""
    if not isinstance(raw_data, Mapping):
        raise IdleonInvalidSchema("Top-level Idleon data must be an object")

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
    )


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
    )


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
    value = _first_value(data, keys)
    if value is None:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _first_float(data: Mapping[str, Any], keys: tuple[str, ...]) -> float | None:
    """Return the first value coerced to a float."""
    value = _first_value(data, keys)
    if value is None:
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


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
