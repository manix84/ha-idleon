"""Constants for HA Idleon."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "idleon"
NAME = "HA Idleon"
VERSION = "0.1.14"

PLATFORMS = (Platform.SENSOR, Platform.BINARY_SENSOR)

CONF_DATA_SOURCE_TYPE = "data_source_type"
CONF_LOCAL_FILE_PATH = "local_file_path"
CONF_REMOTE_URL = "remote_url"
CONF_SCAN_INTERVAL = "scan_interval"

DATA_SOURCE_LOCAL_FILE = "local_file"
DATA_SOURCE_REMOTE_URL = "remote_url"
DATA_SOURCE_TYPES = [DATA_SOURCE_LOCAL_FILE, DATA_SOURCE_REMOTE_URL]

DEFAULT_SCAN_INTERVAL = 3600
MIN_SCAN_INTERVAL = 300
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
