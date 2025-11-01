"""The Ostrom Spot Prices integration."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import OstromApiClient
from .const import CONF_ZIP_CODE, DOMAIN
from .coordinator import OstromDataUpdateCoordinator
# KEIN Import von options_flow mehr

_LOGGER = logging.getLogger(__name__)

# Wir laden NUR noch die SENSOR-Plattform als String
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ostrom Spot Prices from a config entry."""

    client = OstromApiClient(
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
        zip_code=entry.data[CONF_ZIP_CODE],
    )

    coordinator = OstromDataUpdateCoordinator(hass, client, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed as err:
        _LOGGER.warning("Authentication failed: %s. Starting re-auth flow.", err)
        hass.config_entries.async_start_re_auth_flow(entry.entry_id) # Name korrigiert
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # KEIN Options-Listener mehr
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    if unload_ok := await hass.config_entries.async_forward_entry_unloads(
        entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok