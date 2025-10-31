"""The Ostrom Spot Prices integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, Platform
from homeassistant.core import HomeAssistant

from .api import OstromApiClient
from .const import CONF_ZIP_CODE, DOMAIN
from .coordinator import OstromDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ostrom Spot Prices from a config entry."""
    # 1. API-Client erstellen
    client = OstromApiClient(
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
        zip_code=entry.data[CONF_ZIP_CODE],
    )

    # 2. Coordinator erstellen und Daten zum ersten Mal abrufen
    coordinator = OstromDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    # 3. Coordinator im zentralen hass.data speichern, damit Plattformen ihn finden
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 4. Sensor-Plattformen (sensor.py) laden
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Entlade die Plattformen (sensor.py)
    if unload_ok := await hass.config_entries.async_forward_entry_unload(
        entry, PLATFORMS
    ):
        # Entferne den Coordinator aus hass.data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
