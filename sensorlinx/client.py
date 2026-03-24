from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx

from .exceptions import APIError, AuthError, NotFoundError
from .models import Building, Device, HistoryEntry, Manager, User, _parse_list

BASE_URL = "https://mobile.sensorlinx.co"


class SensorLinxClient:
    """Client for the HBX SensorLinx API.

    Usage::

        client = SensorLinxClient.from_secrets("secrets.json")
        buildings = client.list_buildings()
        devices = client.list_devices(buildings[0].id)
        reading = client.history_sample(buildings[0].id, devices[0].sync_code)
    """

    def __init__(self, base_url: str = BASE_URL, token: Optional[str] = None):
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if token:
            self._set_token(token)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_secrets(cls, path: str | Path = "secrets.json") -> SensorLinxClient:
        """Create and authenticate a client from a JSON secrets file.

        Expected format::

            {
              "email": "you@example.com",
              "password": "yourpassword"
            }

        Or with a pre-existing token::

            {
              "token": "eyJ..."
            }
        """
        secrets = json.loads(Path(path).read_text())
        client = cls()
        if "token" in secrets:
            client._set_token(secrets["token"])
        else:
            client.login(secrets["email"], secrets["password"])
        return client

    @classmethod
    def from_credentials(cls, email: str, password: str) -> SensorLinxClient:
        client = cls()
        client.login(email, password)
        return client

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> str:
        """Authenticate and store the token. Returns the token string."""
        data = self._post("/account/login", {"email": email, "password": password})
        token = data.get("token") or (data.get("user") or {}).get("token")
        if not token:
            raise AuthError(f"Login succeeded but no token in response: {data}")
        self._set_token(token)
        return token

    def refresh(self) -> str:
        """Refresh the current token."""
        data = self._get("/account/refresh")
        token = data.get("token")
        if token:
            self._set_token(token)
        return token

    def get_current_user(self) -> User:
        data = self._get("/account/me")
        return User.from_dict(data.get("user") or data)

    def update_profile(self, **kwargs) -> User:
        data = self._patch("/account/me", kwargs)
        return User.from_dict(data.get("user") or data)

    def change_password(self, current_password: str, new_password: str) -> None:
        self._patch("/account/password", {
            "currentPassword": current_password,
            "newPassword": new_password,
        })

    # ------------------------------------------------------------------
    # Buildings
    # ------------------------------------------------------------------

    def list_buildings(self) -> list[Building]:
        data = self._get("/buildings")
        return _parse_list(data, Building)

    def get_building(self, building_id: str) -> Building:
        data = self._get(f"/buildings/{building_id}")
        return Building.from_dict(data.get("data") or data)

    def create_building(self, name: str, **kwargs) -> Building:
        data = self._post("/buildings", {"name": name, **kwargs})
        return Building.from_dict(data.get("data") or data)

    def update_building(self, building_id: str, **kwargs) -> Building:
        data = self._patch(f"/buildings/{building_id}", kwargs)
        return Building.from_dict(data.get("data") or data)

    def delete_building(self, building_id: str) -> None:
        self._delete(f"/buildings/{building_id}")

    def get_weather(self, building_id: str) -> dict:
        return self._get(f"/buildings/{building_id}/weather")

    def get_allowed_countries(self) -> list[str]:
        data = self._get("/buildings/allowed-countries")
        if isinstance(data, list):
            return data
        return data.get("data") or data.get("countries") or []

    # ------------------------------------------------------------------
    # Building managers
    # ------------------------------------------------------------------

    def list_managers(self, building_id: str) -> list[Manager]:
        data = self._get(f"/buildings/{building_id}/managers")
        return _parse_list(data, Manager)

    def add_manager(self, building_id: str, email: str) -> Manager:
        data = self._put(f"/buildings/{building_id}/managers", {"email": email})
        return Manager.from_dict(data.get("data") or data)

    def remove_manager(self, building_id: str, manager_id: str) -> None:
        self._delete(f"/buildings/{building_id}/managers/{manager_id}")

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------

    def list_devices(self, building_id: str) -> list[Device]:
        data = self._get(f"/buildings/{building_id}/devices")
        return _parse_list(data, Device)

    def get_device(self, building_id: str, sync_code: str) -> Device:
        data = self._get(f"/buildings/{building_id}/devices/{sync_code}")
        return Device.from_dict(data.get("data") or data)

    def link_device(self, building_id: str, sync_code: str, pin: str, **kwargs) -> Device:
        """Register a device to a building by sync code and PIN."""
        data = self._post(f"/buildings/{building_id}/devices", {
            "syncCode": sync_code,
            "pin": pin,
            **kwargs,
        })
        return Device.from_dict(data.get("data") or data)

    def update_device(self, building_id: str, sync_code: str, **kwargs) -> Device:
        data = self._patch(f"/buildings/{building_id}/devices/{sync_code}", kwargs)
        return Device.from_dict(data.get("data") or data)

    def unlink_device(self, building_id: str, sync_code: str) -> None:
        self._delete(f"/buildings/{building_id}/devices/{sync_code}")

    # ------------------------------------------------------------------
    # History / readings
    # ------------------------------------------------------------------

    def history_sample(self, building_id: str, sync_code: str) -> HistoryEntry | None:
        """Return the most recent reading for a device."""
        data = self._post(f"/buildings/{building_id}/devices/{sync_code}/history/sample")
        entries = _parse_list(data, HistoryEntry)
        if entries:
            return entries[0]
        if isinstance(data, dict) and data:
            return HistoryEntry.from_dict(data.get("data") or data)
        return None

    def history_today(self, building_id: str, sync_code: str, fields: list[str] | None = None, **kwargs) -> list[HistoryEntry]:
        """Fetch today's history. ``fields`` selects which data fields to return (e.g. ``["temps", "dmd"]``)."""
        body = {"fields": fields, **kwargs} if fields else {}
        data = self._post(
            f"/buildings/{building_id}/devices/{sync_code}/history/today", body
        )
        return _parse_list(data, HistoryEntry)

    def history_hours(self, building_id: str, sync_code: str, hours: int = 24, fields: list[str] | None = None, **kwargs) -> list[HistoryEntry]:
        """Fetch history for the past N hours. ``fields`` selects which data fields to return (e.g. ``["temps", "dmd"]``)."""
        data = self._post(
            f"/buildings/{building_id}/devices/{sync_code}/history/hours",
            {"hours": hours, "fields": fields or ["temps", "dmd", "relStat"], **kwargs},
        )
        return _parse_list(data, HistoryEntry)

    def history_range(
        self,
        building_id: str,
        sync_code: str,
        start: datetime,
        end: datetime,
        **kwargs,
    ) -> list[HistoryEntry]:
        data = self._post(
            f"/buildings/{building_id}/devices/{sync_code}/history/range",
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                **kwargs,
            },
        )
        return _parse_list(data, HistoryEntry)

    def history_all(self, building_id: str, sync_code: str) -> list[HistoryEntry]:
        data = self._post(f"/buildings/{building_id}/devices/{sync_code}/history")
        return _parse_list(data, HistoryEntry)

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _set_token(self, token: str) -> None:
        self._http.headers["Authorization"] = f"Bearer {token}"

    def _request(self, method: str, path: str, **kwargs) -> Any:
        response = self._http.request(method, path, **kwargs)
        return self._handle_response(response)

    def _get(self, path: str, **kwargs) -> Any:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, body: Optional[dict] = None, **kwargs) -> Any:
        return self._request("POST", path, json=body or {}, **kwargs)

    def _patch(self, path: str, body: dict, **kwargs) -> Any:
        return self._request("PATCH", path, json=body, **kwargs)

    def _put(self, path: str, body: dict, **kwargs) -> Any:
        return self._request("PUT", path, json=body, **kwargs)

    def _delete(self, path: str, **kwargs) -> Any:
        return self._request("DELETE", path, **kwargs)

    @staticmethod
    def _handle_response(response: httpx.Response) -> Any:
        if response.status_code == 401:
            raise AuthError("Not authenticated or token expired. Call login() again.")
        if response.status_code == 404:
            raise NotFoundError(f"Resource not found: {response.url.path}")
        if response.status_code >= 400:
            try:
                msg = response.json().get("message") or response.text
            except Exception:
                msg = response.text
            raise APIError(response.status_code, msg)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> SensorLinxClient:
        return self

    def __exit__(self, *_) -> None:
        self.close()
