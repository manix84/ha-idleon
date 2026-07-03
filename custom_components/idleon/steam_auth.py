"""Steam OpenID helpers for the Idleon config flow."""

from __future__ import annotations

from http import HTTPStatus

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import UnknownFlow
from homeassistant.helpers.http import KEY_HASS
from homeassistant.helpers.network import NoURLAvailableError, get_url
from yarl import URL

from .const import CONF_STEAM_CALLBACK_STATE, CONF_STEAM_OPENID_RESPONSE_URL, DOMAIN

STEAM_AUTH_CALLBACK_PATH = "/api/idleon/steam/auth/callback"
STEAM_AUTH_CALLBACK_VIEW_NAME = "api:idleon:steam_auth_callback"


def async_register_steam_auth_callback_view(hass: HomeAssistant) -> None:
    """Register the Steam auth callback view once."""
    if hass.http is None:
        return
    registered_key = f"{DOMAIN}_steam_auth_callback_registered"
    if hass.data.get(registered_key):
        return
    hass.http.register_view(IdleonSteamAuthCallbackView)
    hass.data[registered_key] = True


def steam_callback_url(hass: HomeAssistant, flow_id: str, state: str) -> str:
    """Return the Home Assistant Steam auth callback URL for this flow."""
    base_url = get_url(
        hass,
        require_current_request=True,
        require_ssl=True,
        allow_internal=False,
        allow_external=True,
        allow_cloud=True,
        prefer_external=True,
    )
    return str(
        URL(f"{base_url.rstrip('/')}{STEAM_AUTH_CALLBACK_PATH}").with_query(
            {
                "flow_id": flow_id,
                CONF_STEAM_CALLBACK_STATE: state,
            }
        )
    )


class IdleonSteamAuthCallbackView(HomeAssistantView):
    """Receive Steam OpenID callbacks and resume the Idleon config flow."""

    requires_auth = False
    url = STEAM_AUTH_CALLBACK_PATH
    name = STEAM_AUTH_CALLBACK_VIEW_NAME

    async def get(self, request: web.Request) -> web.Response:
        """Handle a Steam OpenID redirect."""
        flow_id = request.query.get("flow_id")
        state = request.query.get(CONF_STEAM_CALLBACK_STATE)
        if not flow_id or not state:
            return web.Response(
                text="Missing Idleon Steam flow state",
                status=HTTPStatus.BAD_REQUEST,
            )

        hass: HomeAssistant = request.app[KEY_HASS]
        try:
            await hass.config_entries.flow.async_configure(
                flow_id=flow_id,
                user_input={
                    CONF_STEAM_CALLBACK_STATE: state,
                    CONF_STEAM_OPENID_RESPONSE_URL: str(request.url),
                },
            )
        except UnknownFlow:
            return web.Response(
                text="Idleon Steam flow was not found",
                status=HTTPStatus.BAD_REQUEST,
            )

        return web.Response(
            headers={"content-type": "text/html"},
            text=(
                "<!doctype html><html><body>"
                "<p>Steam sign-in complete. You can close this window.</p>"
                "<script>window.close()</script>"
                "</body></html>"
            ),
        )


__all__ = [
    "NoURLAvailableError",
    "async_register_steam_auth_callback_view",
    "steam_callback_url",
]
