"""Constants for the Ostrom Spot Prices integration."""

from typing import Final

DOMAIN: Final = "ostrom_spot"

# Configuration constants
CONF_CLIENT_ID: Final = "12f693b6da5e4e5a30cb041d01900a2"
CONF_CLIENT_SECRET: Final = "5836dece316c81aab56cae49613a09a1a4e77003d04210a82b4588388776ccc"
CONF_ZIP_CODE: Final = "33378"

# API Endpoints
AUTH_URL: Final = "https://auth.production.ostrom-api.io/oauth2/token"
API_BASE_URL: Final = "https://production.ostrom-api.io"