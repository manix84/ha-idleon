"""Typed models for parsed Idleon account data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class IdleonDataSource:
    """Configuration for a read-only Idleon data source."""

    source_type: str
    local_file_path: str | None = None
    remote_url: str | None = None
    scan_interval: int = 3600


@dataclass(frozen=True, slots=True)
class IdleonCharacter:
    """Parsed Idleon character data used by entities."""

    character_id: str
    name: str
    level: int
    character_class: str
    current_map: str
    current_activity: str
    afk_hours: float
    inventory_full: bool
    needs_attention: bool


@dataclass(frozen=True, slots=True)
class IdleonAccount:
    """Parsed Idleon account data used by the coordinator and entities."""

    account_id: str
    name: str
    total_level: int
    gems: int
    characters: tuple[IdleonCharacter, ...]
    source_updated_at: datetime | None = None

    @property
    def character_count(self) -> int:
        """Return the number of parsed characters."""
        return len(self.characters)

