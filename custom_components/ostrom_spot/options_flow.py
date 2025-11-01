"""Options flow for Ostrom Spot Prices."""

import voluptuous as vol
from homeassistant.config_entries import OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)

# Wir importieren die Konstante
from .const import DOMAIN, OPTION_TOTAL_CONSUMPTION


class OstromOptionsFlowHandler(OptionsFlow):
    """Handle options flow for the integration."""

    async def async_step_init(self, user_input=None):
        """Manage the options step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        # FINALES SCHEMA (verwendet die Filter, die funktionieren)
        options_schema = vol.Schema(
            {
                vol.Optional(
                    OPTION_TOTAL_CONSUMPTION,
                    default=options.get(OPTION_TOTAL_CONSUMPTION),
                ): EntitySelector(
                    EntitySelectorConfig(
                        domain="sensor",
                        device_class="energy" # Dieser Filter funktioniert
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )