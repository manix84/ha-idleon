"""Constants for HA Idleon."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "idleon"
NAME = "HA Idleon"
VERSION = "0.1.18"

PLATFORMS = (Platform.SENSOR, Platform.BINARY_SENSOR)

CONF_DATA_SOURCE_TYPE = "data_source_type"
CONF_LOCAL_FILE_PATH = "local_file_path"
CONF_REMOTE_URL = "remote_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_AUTH_PROVIDER = "auth_provider"
CONF_IDLEON_EMAIL = "idleon_email"
CONF_IDLEON_USER_ID = "idleon_user_id"
CONF_IDLEON_REFRESH_TOKEN = "idleon_refresh_token"

DATA_SOURCE_IDLEON_CLOUD = "idleon_cloud"
DATA_SOURCE_LOCAL_FILE = "local_file"
DATA_SOURCE_REMOTE_URL = "remote_url"
DATA_SOURCE_TYPES = [DATA_SOURCE_LOCAL_FILE, DATA_SOURCE_REMOTE_URL]
FUTURE_DATA_SOURCE_TYPES = [DATA_SOURCE_IDLEON_CLOUD]

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

DEFAULT_SCAN_INTERVAL = 3600
MIN_SCAN_INTERVAL = 300
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
