"""Constants for HA Idleon."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "idleon"
NAME = "Legends of Idleon"
VERSION = "0.12.2"

PLATFORMS = (Platform.SENSOR, Platform.BINARY_SENSOR)

CONF_DATA_SOURCE_TYPE = "data_source_type"
CONF_LOCAL_FILE_PATH = "local_file_path"
CONF_REMOTE_URL = "remote_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_AUTH_PROVIDER = "auth_provider"
CONF_IDLEON_EMAIL = "idleon_email"
CONF_IDLEON_PASSWORD = "idleon_password"
CONF_STEAM_OPENID_RESPONSE_URL = "steam_openid_response_url"
CONF_STEAM_CALLBACK_STATE = "steam_callback_state"
CONF_IDLEON_USER_ID = "idleon_user_id"
CONF_IDLEON_REFRESH_TOKEN = "idleon_refresh_token"

DATA_SOURCE_IDLEON_CLOUD = "idleon_cloud"
DATA_SOURCE_LOCAL_FILE = "local_file"
DATA_SOURCE_REMOTE_URL = "remote_url"

AUTH_PROVIDER_APPLE = "apple"
AUTH_PROVIDER_EMAIL = "email"
AUTH_PROVIDER_GOOGLE = "google"
AUTH_PROVIDER_STEAM = "steam"
AUTH_PROVIDERS = [
    AUTH_PROVIDER_EMAIL,
    AUTH_PROVIDER_GOOGLE,
    AUTH_PROVIDER_STEAM,
    AUTH_PROVIDER_APPLE,
]
DATA_SOURCE_TYPES = [
    DATA_SOURCE_LOCAL_FILE,
    AUTH_PROVIDER_GOOGLE,
    AUTH_PROVIDER_APPLE,
    AUTH_PROVIDER_EMAIL,
    AUTH_PROVIDER_STEAM,
]

DEFAULT_SCAN_INTERVAL = 300
MIN_SCAN_INTERVAL = 300
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
