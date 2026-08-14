"""Constants for the Smart Solity integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "smart_solity"
PLATFORMS = [Platform.LOCK, Platform.SENSOR]

API_BASE_URL = "https://www.smartsolity.com"
APP_SOURCE = "0"
LANGUAGE = "1"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

CONF_TOKEN = "token"
CONF_TOKEN_PASSWORD = "token_password"
CONF_PHONE_TOKEN = "phone_token"
CONF_MEMBER_NAME = "member_name"
CONF_MEMBER_ID = "member_id"

STATUS_LOCKED = "0"
STATUS_UNLOCKED = "1"

COMMAND_LOCK = "close"
COMMAND_UNLOCK = "open"
COMMAND_STATUS = "get_status"
COMMAND_CONNECT_GATEWAY = "connect_gateway"
COMMAND_SET_ONE_TIME_PIN = "set_one_pwd"

SERVICE_GET_USERS = "get_users"
SERVICE_INVITE_USER = "invite_user"
SERVICE_CREATE_GUEST_PIN = "create_guest_pin"
SERVICE_GET_ACCESS_LOG = "get_access_log"
