"""Ostrom API Client."""

import time
from datetime import datetime
from typing import Any

import requests
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import API_BASE_URL, AUTH_URL


class OstromApiClient:
    """
    Ein API-Client für die Ostrom-API, der Authentifizierung
    und Token-Refreshing automatisch verwaltet.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        zip_code: str,
    ):
        """Initialisiere den API-Client."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.zip_code = zip_code

        self._access_token: str | None = None
        self._token_expires_at: float = 0  # Zeitstempel (Sekunden)

    def _get_access_token(self) -> bool:
        """
        Holt einen neuen Access Token.
        Wirft ConfigEntryAuthFailed bei Authentifizierungsfehlern.
        """
        try:
            response = requests.post(
                AUTH_URL,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = time.time() + expires_in - 60  # 60s Puffer
            return True

        except requests.exceptions.HTTPError as err:
            if err.response.status_code in (400, 401, 403):
                # 400 (invalid_request) oder 401 (invalid_client)
                raise ConfigEntryAuthFailed("Invalid Client ID or Secret") from err
            raise ConnectionError(f"Error during authentication: {err}") from err
        except Exception as err:
            raise ConnectionError(f"Unexpected error during auth: {err}") from err

    def _ensure_token_valid(self) -> None:
        """Stellt sicher, dass der Token gültig ist, holt sonst einen neuen."""
        if not self._access_token or time.time() >= self._token_expires_at:
            self._get_access_token()

    def get_spot_prices(
        self, start_date: datetime, end_date: datetime, resolution: str = "HOUR"
    ) -> dict[str, Any]:
        """
        Ruft die Spotpreise für einen gegebenen Zeitraum ab.
        Dies ist eine *synchrone* Funktion (wird in HA 'async_add_executor_job' benötigen).
        """
        self._ensure_token_valid()

        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        endpoint = f"{API_BASE_URL}/spot-prices"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        params = {
            "startDate": start_str,
            "endDate": end_str,
            "resolution": resolution,
            "zip": self.zip_code,
        }

        try:
            response = requests.get(
                endpoint, headers=headers, params=params, timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 400:
                # 400 kann auch eine ungültige PLZ sein
                raise ValueError(
                    f"Bad request (invalid ZIP?): {err.response.text}"
                ) from err
            raise ConnectionError(f"Error fetching spot prices: {err}") from err
        except Exception as err:
            raise ConnectionError(f"Unexpected error fetching prices: {err}") from err
