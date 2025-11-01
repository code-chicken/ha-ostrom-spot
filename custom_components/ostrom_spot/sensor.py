"""Sensor platform for Ostrom Spot Prices."""

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_ZIP_CODE
from .coordinator import OstromDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    
    _LOGGER.info("Setting up Ostrom sensor platform...")
    
    coordinator: OstromDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Wir erstellen NUR noch den einen Preissensor
    sensors_to_add = [
        OstromCurrentPriceSensor(coordinator, entry),
    ]
    async_add_entities(sensors_to_add)
    _LOGGER.info("Successfully added Ostrom sensors.")


class OstromCurrentPriceSensor(CoordinatorEntity, SensorEntity):
    """
    Ein Sensor, der den *aktuellen* stündlichen Ostrom-Preis anzeigt.
    Zukünftige Preise werden als Attribute gespeichert.
    """

    _attr_has_entity_name = True
    _attr_state_class = None # Korrigiert
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR/kWh"
    _attr_icon = "mdi:currency-eur"
    _attr_translation_key = "current_price"

    def __init__(self, coordinator: OstromDataUpdateCoordinator, entry: ConfigEntry):
        """Initialisiere den Sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_current_price"
        zip_code = entry.data.get(CONF_ZIP_CODE, "Unknown ZIP")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Ostrom ({zip_code})",
            "manufacturer": "Ostrom",
            "model": "Spot Price",
            "entry_type": "service",
        }

    @property
    def native_value(self) -> float | None:
        """Gibt den aktuellen stündlichen Preis als EUR/kWh zurück."""
        if not self.coordinator.data or not self.coordinator.data.get("entries"):
            return None
        now = dt_util.now()
        current_entry = None
        for entry in self.coordinator.data["entries"]:
            if entry["start_time"].hour == now.hour and entry["start_time"].date() == now.date():
                current_entry = entry
                break
        if current_entry:
            price_in_eur = current_entry["price_cent_kwh"] / 100
            return round(price_in_eur, 4)
        _LOGGER.warning("Could not find current spot price for %s", now)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Speichert alle zukünftigen Preise als Attribute."""
        if not self.coordinator.data or not self.coordinator.data.get("entries"):
            return None
        all_prices = {}
        for entry in self.coordinator.data["entries"]:
            try:
                entry_time_utc = entry["start_time"]
                price_eur = round(entry["price_cent_kwh"] / 100, 4)
                all_prices[entry_time_utc.isoformat()] = price_eur
            except Exception as e:
                _LOGGER.warning("Error processing attribute entry: %s", e)
        return {
            "monthly_base_fee_eur": self.coordinator.data.get("monthly_base_fee"),
            "monthly_grid_fee_eur": self.coordinator.data.get("monthly_grid_fee"),
            "all_prices": all_prices,
            "last_update_utc": dt_util.utcnow().isoformat(),
        }

# KEINE 'OstromCostSensor'-Klasse mehr