#!/usr/bin/env python3
"""
Sample SensorLinx client — reads credentials from secrets.json.

secrets.json format:
  { "email": "you@example.com", "password": "yourpassword" }

Or with a cached token (skips login):
  { "token": "eyJ..." }
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sensorlinx import SensorLinxClient
from sensorlinx.exceptions import APIError, AuthError, NotFoundError

SECRETS_FILE = Path("secrets.json")


def print_section(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def main() -> None:
    if not SECRETS_FILE.exists():
        print(f"Error: {SECRETS_FILE} not found.")
        print("Create it with: {\"email\": \"you@example.com\", \"password\": \"...\"}")
        sys.exit(1)

    with SensorLinxClient.from_secrets(SECRETS_FILE) as client:

        # --- Current user ---
        print_section("Current User")
        user = client.get_current_user()
        print(f"  Name : {user.full_name}")
        print(f"  Email: {user.email}")
        if user.organization_name:
            print(f"  Org  : {user.organization_name}")

        # --- Buildings ---
        print_section("Buildings")
        buildings = client.list_buildings()
        if not buildings:
            print("  No buildings found.")
            return

        for b in buildings:
            print(f"  [{b.id}]  {b.name}")

        # Work with the first building
        building = buildings[0]
        print(f"\n  Using building: {building.name}")

        # --- Weather ---
        try:
            weather_raw = client.get_weather(building.id)
            print_section(f"Weather — {building.name}")
            w = weather_raw.get("weather", {})
            print(f"  {w.get('description', '?').title()}  {w.get('temp')}°F  (feels like {w.get('feelsLike')}°F)")
            print(f"  Humidity : {w.get('humidity')}%   Wind: {w.get('wind')} mph @ {w.get('windDir')}°")
            print(f"  Pressure : {w.get('pressure')} hPa")
            if w.get("snow"):
                print(f"  Snow     : {w.get('snow')} mm/h")
            if w.get("rain"):
                print(f"  Rain     : {w.get('rain')} mm/h")
            forecast = weather_raw.get("forecast", [])
            if forecast:
                print("\n  Forecast:")
                for f in forecast:
                    time = f.get("time", "")[:10]
                    desc = f.get("description", "?").title()
                    lo, hi = f.get("min"), f.get("max")
                    snow = f"  snow={f['snow']}mm" if f.get("snow") else ""
                    rain = f"  rain={f['rain']}mm" if f.get("rain") else ""
                    print(f"    {time}  {desc:20}  {lo}–{hi}°F{snow}{rain}")
        except (NotFoundError, APIError) as e:
            print(f"  (weather unavailable: {e})")

        # --- Devices ---
        print_section(f"Devices — {building.name}")
        devices = client.list_devices(building.id)
        if not devices:
            print("  No devices found.")
            return

        for d in devices:
            print(f"  [{d.sync_code}]  {d.name or '(unnamed)'}  type={d.device_type}  fw={d.firmware_version or '?'}")

        # Work with the first device
        device = devices[0]
        print(f"\n  Using device: {device.sync_code}  ({device.device_type})")

        # --- Device status ---
        print_section(f"Device Status — {device.sync_code}")
        raw = device.raw

        print(f"  Connected : {raw.get('connected')}  (at {raw.get('connectedAt', '?')[:19]})")
        print(f"  Firmware  : {raw.get('firmVer')}")
        print(f"  Demand    : {raw.get('dmd')}%")

        temps = raw.get("temperatures") or []
        if temps:
            print("\n  Temperatures:")
            for t in temps:
                if not t.get("enabled"):
                    continue
                state = t.get("activatedState") or ("active" if t.get("activated") else "idle")
                target = f"  target={t['target']}°F" if t.get("target") is not None else ""
                print(f"    {t.get('title', '?'):12}  {t.get('current')}°F{target}  [{state}]")

        demands = raw.get("demands") or []
        if demands:
            print("\n  Demands:")
            for dem in demands:
                status = "ON" if dem.get("activated") else "off"
                print(f"    {dem.get('title', '?'):8}  {status}")

        stages = raw.get("stages") or []
        if stages:
            print("\n  Heat Pump Stages:")
            for s in stages:
                if not s.get("enabled"):
                    continue
                status = "RUNNING" if s.get("activated") else "off"
                print(f"    {s.get('title', '?'):10}  {status}  runtime={s.get('runTime', '?')}")

        pumps = raw.get("pumps") or []
        if pumps:
            print("\n  Pumps:")
            for p in pumps:
                status = "ON" if p.get("activated") else "off"
                print(f"    {p.get('title', '?'):10}  {status}")

        rv = raw.get("reversingValve")
        if rv:
            status = "ACTIVATED" if rv.get("activated") else "off"
            print(f"\n  Reversing Valve:  {status}")

        backup = raw.get("backup")
        if backup and backup.get("enabled"):
            status = "RUNNING" if backup.get("activated") else "off"
            print(f"  Backup Heat    :  {status}  runtime={backup.get('runTime', '?')}")

        wsd = raw.get("wsd") or {}
        wsd_active = [v.get("title") for v in wsd.values() if v.get("activated")]
        if wsd_active:
            print(f"  Shutdown active:  {', '.join(wsd_active)}")

        relays = raw.get("relays") or []
        active_relays = [i + 1 for i, on in enumerate(relays) if on]
        print(f"\n  Active relays : {active_relays if active_relays else 'none'}")

        # --- Latest reading ---
        print_section(f"Latest Reading — {device.sync_code}")
        try:
            sample = client.history_sample(building.id, device.sync_code)
            if sample:
                ts = sample.timestamp.strftime("%Y-%m-%d %H:%M:%S %Z") if sample.timestamp else "unknown time"
                print(f"  Timestamp: {ts}")
                for k, v in sample.readings.items():
                    print(f"  {k}: {v}")
            else:
                print("  No data returned.")
        except APIError as e:
            print(f"  Error: {e}")

        # --- Last 24 hours ---
        print_section(f"Last 24 Hours — {device.sync_code}")
        try:
            entries = client.history_hours(building.id, device.sync_code, hours=24)
            print(f"  {len(entries)} entries returned.")
            if entries:
                def fmt_ts(e):
                    return e.timestamp.strftime("%H:%M") if e.timestamp else "?"
                print(f"  Range: {fmt_ts(entries[-1])} → {fmt_ts(entries[0])}")
                # Summarize each temperature sensor
                temps_by_key: dict = {}
                for e in entries:
                    for slot, info in (e.readings.get("temps") or {}).items():
                        if isinstance(info, dict) and info.get("actual") is not None:
                            temps_by_key.setdefault(slot, []).append(info["actual"])
                for slot, vals in temps_by_key.items():
                    title = (entries[0].readings.get("temps") or {}).get(slot, {}).get("title") or slot
                    print(f"  {title:12}  min={min(vals):.1f}°  max={max(vals):.1f}°  avg={sum(vals)/len(vals):.1f}°")
        except APIError as e:
            print(f"  Error: {e}")

        # --- Managers ---
        print_section(f"Managers — {building.name}")
        try:
            managers = client.list_managers(building.id)
            if managers:
                for m in managers:
                    print(f"  {m.email}  (id={m.id})")
            else:
                print("  No managers.")
        except APIError as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    try:
        main()
    except AuthError as e:
        print(f"\nAuthentication error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
