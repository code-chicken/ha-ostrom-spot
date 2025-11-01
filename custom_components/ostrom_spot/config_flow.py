"""Config flow for Ostrom Spot Prices."""

import logging
from datetime import timedelta
from typing import Any
from homeassistant import data_entry_flow

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET

# --- KORREKTUR HIER ---
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.util import dt as dt_util

from .api import OstromApiClient

# -----------------------
from .const import CONF_ZIP_CODE, DOMAIN

_LOGGER = logging.getLogger(__name__)


# Definition der Exceptions
class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidZip(HomeAssistantError):
    """Error to indicate the ZIP code is invalid."""


class UnknownError(HomeAssistantError):
    """Error to indicate an unknown error occurred."""


# Schema für die Benutzereingaben in der GUI
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
        vol.Required(CONF_ZIP_CODE): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validiere die Benutzereingaben, indem ein Test-API-Aufruf gemacht wird.
    Wirft eine Exception, wenn etwas schiefgeht.
    """
    client_id = data[CONF_CLIENT_ID]
    client_secret = data[CONF_CLIENT_SECRET]
    zip_code = data[CONF_ZIP_CODE]

    api = OstromApiClient(client_id, client_secret, zip_code)

    try:
        start_date = dt_util.now().replace(minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(hours=1)

        await hass.async_add_executor_job(api.get_spot_prices, start_date, end_date)
    except ConfigEntryAuthFailed as err:
        raise InvalidAuth from err
    except ValueError as err:
        raise InvalidZip from err
    except ConnectionError as err:
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.exception("Unexpected error during validation")
        raise UnknownError from err

    return {"title": f"Ostrom ({zip_code})"}


class OstromConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ostrom Spot Prices."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Behandelt den ersten Schritt (Eingabe durch Benutzer)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CLIENT_ID])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidZip:
                errors["base"] = "invalid_zip"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except UnknownError:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """
        Behandelt den "Neu konfigurieren"-Flow.
        Wird aufgerufen, wenn die Authentifizierung fehlgeschlagen ist.
        """
        
        # Hole den bestehenden Config-Eintrag, der die Neukonfiguration ausgelöst hat
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None

        errors: dict[str, str] = {}

        if user_input is not None:
            # Benutzer hat das Formular abgeschickt, validiere die NEUEN Daten
            try:
                info = await validate_input(self.hass, user_input)
                
                # Update den bestehenden Eintrag mit den neuen Daten
                self.hass.config_entries.async_update_entry(
                    entry, data=user_input, title=info["title"]
                )
                
                # Lade die Integration neu, damit sie die neuen Daten verwendet
                await self.hass.config_entries.async_reload(entry.entry_id)
                
                # Schließe den Flow
                return self.async_abort(reason="reauth_successful")

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidZip:
                errors["base"] = "invalid_zip"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except UnknownError:
                errors["base"] = "unknown"

        # Zeige das Formular an.
        # WICHTIG: Wir füllen das Formular mit den ALTEN Daten vor,
        # damit der Benutzer sieht, was er ändern muss.
        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIENT_ID, default=entry.data.get(CONF_CLIENT_ID)): str,
                    vol.Required(CONF_CLIENT_SECRET, default=""): str, # Secret aus Sicherheitsgründen nie vorfüllen
                    vol.Required(CONF_ZIP_CODE, default=entry.data.get(CONF_ZIP_CODE)): str,
                }
            ),
            errors=errors,
        )


    