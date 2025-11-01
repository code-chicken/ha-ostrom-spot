"""DataUpdateCoordinator for the Ostrom integration."""

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from .api import OstromApiClient  # Nur den Client importieren
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Wie oft rufen wir die API ab?
# Alle 30 Minuten ist ein guter Start. Die Preise ändern sich nur stündlich.
POLLING_INTERVAL = timedelta(minutes=30)


class OstromDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages fetching data from the Ostrom API for all sensors."""

    def __init__(self, hass: HomeAssistant, client: OstromApiClient, entry: ConfigEntry):
        """Initialisiere den DataUpdateCoordinator."""
        self.client = client
        self.config_entry = entry  # Speichere den ConfigEntry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=POLLING_INTERVAL,
        )

    async def _async_update_data(self) -> dict:
        """
        Holt die neuesten Spotpreise von der Ostrom API.
        Wird von Home Assistant im Hintergrund aufgerufen (alle 30 Min).
        """
        try:
            # Definiere den Zeitraum (Heute + 2 Tage in die Zukunft)
            # Wir holen immer die Daten für heute und die nächsten 2 Tage
            start_date = dt_util.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_date = start_date + timedelta(days=2)

            # Führe den synchronen API-Aufruf in einem Executor-Job aus
            api_data = await self.hass.async_add_executor_job(
                self.client.get_spot_prices, start_date, end_date
            )

            if not api_data or "data" not in api_data:
                raise UpdateFailed("No data received from API")

            # Verarbeite die Rohdaten in ein nützliches Format
            return self._process_price_data(api_data["data"])

        except ConfigEntryAuthFailed as err:
            # FEHLER! Falsche API-Schlüssel im laufenden Betrieb.
            # Starte den "Neu konfigurieren"-Flow.
            _LOGGER.warning("Authentication failed: %s. Starting re-auth flow.", err)
            self.hass.config_entries.async_start_reauth_flow(self.config_entry.entry_id)
            
            # Wirf den Fehler trotzdem, damit das Update als fehlgeschlagen markiert wird
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except ConnectionError as err:
            # Temporärer Netzwerkfehler (dies ist ein Python Built-in)
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error during data update")
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _process_price_data(self, price_list: list) -> dict:
        """
        Wandelt die Preis-Liste der API in ein verarbeitbares Dict um.
        Wir berechnen hier den finalen Arbeitspreis.
        """
        processed_data = {
            "entries": [],
            "monthly_base_fee": 0,
            "monthly_grid_fee": 0,
        }

        if not price_list:
            return processed_data

        # Speichere die monatlichen Gebühren (sind in jedem Eintrag gleich)
        first_entry = price_list[0]
        processed_data["monthly_base_fee"] = first_entry.get(
            "grossMonthlyOstromBaseFee", 0
        )
        processed_data["monthly_grid_fee"] = first_entry.get("grossMonthlyGridFees", 0)

        # Berechne den finalen Arbeitspreis für jede Stunde
        for entry in price_list:
            try:
                start_time = datetime.fromisoformat(entry["date"])
                spot_price = entry.get("grossKwhPrice", 0)
                taxes_levies = entry.get("grossKwhTaxAndLevies", 0)

                # Der finale Arbeitspreis (Cent/kWh)
                total_price = round(spot_price + taxes_levies, 2)

                processed_data["entries"].append(
                    {
                        "start_time": start_time,
                        "price_cent_kwh": total_price,
                        "spot_price": spot_price,
                        "taxes_levies": taxes_levies,
                    }
                )
            except (TypeError, ValueError) as ex:
                _LOGGER.warning(f"Could not parse price entry: {entry} - Error: {ex}")

        return processed_data
