"""Sensor platform for Ostrom Spot Prices."""

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
# --- NEUE IMPORTE FÜR DEN UTILITY METER ---
from homeassistant.components.utility_meter.sensor import (
    UtilityMeterSensor,
)
from homeassistant.const import (
    STATE_UNAVAILABLE, 
    STATE_UNKNOWN, 
    UnitOfEnergy
)
# ----------------------------------------
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_ZIP_CODE
from .coordinator import OstromDataUpdateCoordinator
from .options_flow import OPTION_TOTAL_CONSUMPTION

_LOGGER = logging.getLogger(__name__)

# Konfiguration für unsere automatisch erstellten Helfer
AUTOMATED_METERS = {
    "hourly": {
        "name": "Ostrom Hourly Consumption",
        "cycle": "hourly",
    },
    "daily": {
        "name": "Ostrom Daily Consumption",
        "cycle": "daily",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    
    _LOGGER.info("Setting up Ostrom sensor platform...")
    
    coordinator: OstromDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # --- KOMPLETTER NEUER SETUP-PROZESS ---
    
    # 1. Erstelle den Standard-Preissensor (immer)
    sensors_to_add = [
        OstromCurrentPriceSensor(coordinator, entry),
    ]

    # 2. Prüfe, ob der Benutzer einen Hauptzähler konfiguriert hat
    source_sensor_id = entry.options.get(OPTION_TOTAL_CONSUMPTION)
    
    if source_sensor_id:
        _LOGGER.info("Consumption sensor defined. Creating helper and cost sensors.")
        
        # Verknüpfe alle Sensoren mit unserem Ostrom-Gerät
        device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }

        # 3. Erstelle die automatischen Utility-Meter-Helfer
        for key, config in AUTOMATED_METERS.items():
            
            meter = UtilityMeterSensor(
                hass=hass,
                parent_meter=source_sensor_id,
                name=config["name"],
                meter_type=config["cycle"],
                meter_offset=None,
                delta_values=False,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, 
                device_class=SensorDeviceClass.ENERGY,
                device_info=device_info,
                unique_id=f"{entry.entry_id}_auto_consumption_{key}",
            )
            sensors_to_add.append(meter)
            
            # 4. Erstelle den passenden Kostensensor für diesen Helfer
            # Wir verwenden die Entity-ID, die der Helfer haben wird
            # (sensor.ostrom_hourly_consumption / sensor.ostrom_daily_consumption)
            consumption_sensor_id = f"sensor.{config['name'].lower().replace(' ', '_')}"
            
            cost_sensor = OstromCostSensor(
                coordinator,
                entry,
                key, # "hourly" or "daily"
                consumption_sensor_id
            )
            sensors_to_add.append(cost_sensor)

    # 5. Füge alle erstellten Sensoren zu Home Assistant hinzu
    async_add_entities(sensors_to_add)
    _LOGGER.info("Successfully added %s Ostrom sensors.", len(sensors_to_add))


class OstromCurrentPriceSensor(CoordinatorEntity, SensorEntity):
    """
    Ein Sensor, der den *aktuellen* stündlichen Ostrom-Preis anzeigt.
    Zukünftige Preise werden als Attribute gespeichert.
    """

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
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
            _LOGGER.debug("Coordinator has no data, sensor value is None")
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


class OstromCostSensor(CoordinatorEntity, SensorEntity):
    """
    Ein Sensor, der die Kosten basierend auf dem Ostrom-Preis
    und einem Verbrauchs-Helfer (Utility Meter) berechnet.
    """
    _attr_state_class = SensorStateClass.TOTAL
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_icon = "mdi:cash"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OstromDataUpdateCoordinator,
        entry: ConfigEntry,
        timescale: str, # "hourly" or "daily"
        consumption_sensor_id: str,
    ):
        """Initialisiere den Kostensensor."""
        super().__init__(coordinator)
        self.consumption_sensor_id = consumption_sensor_id
        self._timescale = timescale
        self._attr_unique_id = f"{entry.entry_id}_cost_{timescale}"
        self._attr_translation_key = f"cost_{timescale}" 

        # Verknüpfe mit demselben Gerät
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }
        
        self._consumption = 0.0
        self._price = 0.0

    @property
    def native_value(self) -> float | None:
        """Gibt die berechneten Kosten zurück."""
        cost = self._consumption * self._price
        return round(cost, 2)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Wird aufgerufen, wenn der Coordinator neue *Preise* hat."""
        self._update_price()
        self.async_write_ha_state()

    @callback
    def _handle_consumption_update(self, event) -> None:
        """Wird aufgerufen, wenn der *Verbrauchs-Helfer* einen neuen Wert hat."""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        try:
            self._consumption = float(new_state.state)
        except (ValueError, TypeError):
            self._consumption = 0.0
            
        self.async_write_ha_state()

    def _update_price(self):
        """Holt den relevanten Preis vom Coordinator."""
        if self._timescale == "hourly":
            self._price = self._get_current_price_from_coordinator()
        else:
            # Für tägliche Kosten nehmen wir auch den aktuellen Preis
            # (Der tägliche Utility-Meter-Sensor wird ja eh nur 1x am Tag resettet,
            # aber die Kosten-Logik hier ist nicht 100%ig, da der Preis variiert)
            # Besser wäre ein Durchschnitt, aber das ist komplizierter.
            self._price = self._get_current_price_from_coordinator()

    def _get_current_price_from_coordinator(self) -> float:
        """Hilfsfunktion, um den aktuellen Preis in EUR/kWh zu holen."""
        if not self.coordinator.data or not self.coordinator.data.get("entries"):
            return 0.0

        now = dt_util.now()
        for entry in self.coordinator.data["entries"]:
            if entry["start_time"].hour == now.hour and entry["start_time"].date() == now.date():
                return round(entry["price_cent_kwh"] / 100, 4)
        return 0.0

    async def async_added_to_hass(self) -> None:
        """Wird aufgerufen, wenn der Sensor zu HA hinzugefügt wird."""
        await super().async_added_to_hass()
        
        if state := self.hass.states.get(self.consumption_sensor_id):
            if state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    self._consumption = float(state.state)
                except (ValueError, TypeError):
                    self._consumption = 0.0

        self._update_price()
        
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self.consumption_sensor_id], self._handle_consumption_update
            )
        )