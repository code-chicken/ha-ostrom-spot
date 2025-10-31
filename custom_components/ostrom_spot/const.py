"""Constants for the Ostrom Spot Prices integration."""

from typing import Final

DOMAIN: Final = "ostrom_spot"

# Configuration constants
CONF_CLIENT_ID: Final = "client_id"
CONF_CLIENT_SECRET: Final = "client_secret"
CONF_ZIP_CODE: Final = "zip_code"

# API Endpoints
AUTH_URL: Final = "https://auth.production.ostrom-api.io/oauth2/token"
API_BASE_URL: Final = "https://production.ostrom-api.io"
