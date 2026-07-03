"""Tests for Steam auth callback helpers."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from homeassistant.core import HomeAssistant

from custom_components.idleon.const import CONF_STEAM_CALLBACK_STATE
from custom_components.idleon.steam_auth import (
    STEAM_AUTH_CALLBACK_PATH,
    async_register_steam_auth_callback_view,
    steam_callback_url,
)


def test_register_steam_auth_callback_without_http(hass: HomeAssistant) -> None:
    """Test callback view registration is a no-op when HTTP is unavailable."""
    assert hass.http is None

    async_register_steam_auth_callback_view(hass)


def test_steam_callback_url(hass: HomeAssistant, monkeypatch) -> None:
    """Test callback URL includes the flow id and CSRF state."""
    monkeypatch.setattr(
        "custom_components.idleon.steam_auth.get_url",
        lambda *_args, **_kwargs: "https://ha.example.com",
    )

    callback_url = steam_callback_url(hass, "flow-123", "state-abc")

    parsed = urlsplit(callback_url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "ha.example.com"
    assert parsed.path == STEAM_AUTH_CALLBACK_PATH
    query = parse_qs(parsed.query)
    assert query["flow_id"] == ["flow-123"]
    assert query[CONF_STEAM_CALLBACK_STATE] == ["state-abc"]
