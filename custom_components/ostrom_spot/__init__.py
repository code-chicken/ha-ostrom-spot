"""The Ostrom Spot Prices integration."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import OstromApiClient
from .const import CONF_ZIP_CODE, DOMAIN
from .coordinator import OstromDataUpdateCoordinator
from .options_flow import OstromOptionsFlowHandler # Import für Options-Flow

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


# HIER IST DIE FEHLENDE FUNKTION
def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # Diese Funktion wird aufgerufen, wenn sich die Optionen ändern.
    # Wir laden die Integration einfach neu, damit sie die neuen Sensoren erstellt.
    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ostrom Spot Prices from a config entry."""

    # 1. API-Client erstellen
    client = OstromApiClient(
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
        zip_code=entry.data[CONF_ZIP_CODE],
    )

    # 2. Coordinator erstellen
    coordinator = OstromDataUpdateCoordinator(hass, client, entry)

    # 3. Daten zum ersten Mal abrufen (für "Neu konfigurieren"-Flow)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed as err:
        # FEHLER! Falsche API-Schlüssel beim ersten Start.
        _LOGGER.warning("Authentication failed: %s. Starting re-auth flow.", err)
        hass.config_entries.async_start_reauth_flow(entry.entry_id)
        return False  # Setup ist fehlgeschlagen

    # 4. Coordinator im zentralen hass.data speichern
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 5. Den Options-Handler registrieren
    # DIESE ZEILE HAT DEN FEHLER VERURSACHT (jetzt ist die Funktion oben definiert)
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    # 6. Sensor-Plattformen (sensor.py / utility_meter.py) laden
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # Entlade die Plattformen (sensor.py / utility_meter.py)
    if unload_ok := await hass.config_entries.async_forward_entry_unload(
        entry, PLATFORMS
    ):
        # Entferne den Coordinator aus hass.data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok