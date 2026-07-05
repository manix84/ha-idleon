"""Diagnostics support for HA Idleon."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from homeassistant.core import HomeAssistant

from . import IdleonConfigEntry
from .const import DOMAIN, VERSION


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: IdleonConfigEntry,
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    runtime_data = entry.runtime_data
    data_source = runtime_data.data_source
    coordinator = runtime_data.coordinator
    account = coordinator.data
    last_updated = coordinator.last_successful_update

    return {
        "integration": {
            "domain": DOMAIN,
            "version": VERSION,
        },
        "data_source": {
            "type": data_source.source_type,
            "remote_url": _redact_remote_url(data_source.remote_url),
            "local_file_path": _redact_local_path(data_source.local_file_path),
            "auth_provider": data_source.auth_provider,
            "idleon_email": _redact_email(data_source.idleon_email),
            "idleon_user_id": _redact_optional_value(
                data_source.idleon_user_id,
                "idleon user id",
            ),
            "has_idleon_refresh_token": bool(data_source.idleon_refresh_token),
        },
        "account": {
            "character_count": account.character_count if account else 0,
            "last_updated": last_updated.isoformat() if last_updated else None,
            "source_updated_at": (
                account.source_updated_at.isoformat()
                if account and account.source_updated_at
                else None
            ),
        },
        "coordinator": {
            "last_successful_update": (
                coordinator.last_successful_update.isoformat()
                if coordinator.last_successful_update
                else None
            ),
            "last_error_type": coordinator.last_error_type,
            "last_error_message": coordinator.last_error_message,
        },
    }


def _redact_remote_url(remote_url: str | None) -> str | None:
    """Redact remote URL query strings and fragments."""
    if not remote_url:
        return None
    parts = urlsplit(remote_url)
    redacted = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    if parts.query or parts.fragment:
        return f"{redacted}?REDACTED"
    return redacted


def _redact_local_path(local_file_path: str | None) -> str | None:
    """Redact local paths that may contain user names."""
    if not local_file_path:
        return None
    return "<redacted local file path>"


def _redact_email(email: str | None) -> str | None:
    """Redact a configured account email address."""
    if not email:
        return None
    return "<redacted email>"


def _redact_optional_value(value: str | None, label: str) -> str | None:
    """Redact optional auth metadata while showing whether it exists."""
    if not value:
        return None
    return f"<redacted {label}>"
