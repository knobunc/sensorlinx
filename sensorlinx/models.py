from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class User:
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    organization_name: Optional[str] = None
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> User:
        return cls(
            id=d.get("_id") or d.get("id", ""),
            email=d.get("email", ""),
            first_name=d.get("firstName", ""),
            last_name=d.get("lastName", ""),
            phone=d.get("phone"),
            organization_name=d.get("organizationName"),
            raw=d,
        )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass
class Building:
    id: str
    name: str
    location: Optional[dict] = None
    organization_name: Optional[str] = None
    short_id: Optional[str] = None
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Building:
        return cls(
            id=d.get("_id") or d.get("id", ""),
            name=d.get("title") or d.get("name", ""),
            location=d.get("location"),
            organization_name=d.get("organizationName"),
            short_id=d.get("shortId"),
            raw=d,
        )


@dataclass
class Device:
    id: str
    sync_code: str
    name: str
    device_type: str
    building_id: str
    firmware_version: Optional[str] = None
    settings: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Device:
        return cls(
            id=d.get("_id") or d.get("id", ""),
            sync_code=d.get("syncCode") or d.get("sync_code", ""),
            name=d.get("name", ""),
            device_type=d.get("deviceType") or d.get("type", ""),
            building_id=d.get("building") or d.get("buildingId") or d.get("building_id", ""),
            firmware_version=d.get("firmVer") or d.get("firmwareVersion"),
            settings={k: v for k, v in d.items() if k not in (
                "_id", "id", "syncCode", "name", "deviceType", "type",
                "building", "buildingId", "firmVer", "createdAt", "updatedAt",
            )},
            raw=d,
        )


@dataclass
class HistoryEntry:
    timestamp: Optional[datetime]
    readings: dict
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> HistoryEntry:
        ts = None
        for key in ("timestamp", "createdAt", "date", "time"):
            if d.get(key):
                try:
                    ts = datetime.fromisoformat(str(d[key]).replace("Z", "+00:00"))
                except ValueError:
                    pass
                break
        # Readings live inside the nested "data" key; fall back to top-level fields
        readings = d.get("data") or {
            k: v for k, v in d.items()
            if k not in ("timestamp", "createdAt", "date", "time", "_id", "source")
        }
        return cls(timestamp=ts, readings=readings, raw=d)


@dataclass
class Manager:
    id: str
    email: str
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Manager:
        return cls(
            id=d.get("_id") or d.get("id", ""),
            email=d.get("email", ""),
            raw=d,
        )


def _parse_list(data: Any, model_cls) -> list:
    """Parse a list or dict-wrapped list response into model instances."""
    if isinstance(data, list):
        return [model_cls.from_dict(item) for item in data]
    if isinstance(data, dict):
        for key in ("data", "items", "results"):
            if isinstance(data.get(key), list):
                return [model_cls.from_dict(item) for item in data[key]]
    return []
