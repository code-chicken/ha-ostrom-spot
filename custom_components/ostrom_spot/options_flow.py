"""Options flow for Ostrom Spot Prices."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)
from homeassistant.components.sensor import SensorDeviceClass

from .const import DOMAIN

# Definiere die (optionalen) Entitäten, nach denen wir fragen
OPTION_TOTAL_CONSUMPTION = "total_consumption_sensor"


class OstromOptionsFlowHandler(OptionsFlow):
    """Handle options flow for the integration."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize the options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options step."""
        errors = {}

        if user_input is not None:
            # Benutzer hat das Formular abgeschickt, speichere die Optionen
            return self.async_create_entry(title="", data=user_input)

        # Hole die aktuell gespeicherten Optionen (falls vorhanden)
        options = self.config_entry.options

        # Erstelle das Formular
        options_schema = vol.Schema(
            {
                vol.Optional(
                    OPTION_TOTAL_CONSUMPTION,
                    description={
                        "suggested_value": options.get(OPTION_TOTAL_CONSUMPTION)
                    },
                ): EntitySelector(
                    EntitySelectorConfig(
                        # Zeige nur Sensoren, die "total_increasing" sind
                        device_class=SensorDeviceClass.ENERGY,
                        state_class="total_increasing",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )