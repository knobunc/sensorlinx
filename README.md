# sensorlinx

> **Deprecated:** This project is no longer maintained. Please use [pysensorlinx](https://github.com/sslivins/pysensorlinx) instead.

A Python client library for the [HBX SensorLinx](https://mobile.sensorlinx.co) building automation platform. Supports reading sensor data, device status, weather, and historical readings for buildings managed through SensorLinx.

This library was reverse-engineered from the SensorLinx mobile app. See [`API.md`](API.md) for the full API reference.

## Features

- Authenticate with email/password or a cached JWT token
- List and manage buildings, devices, and building managers
- Fetch current device readings and historical data (latest sample, today, last N hours, date ranges)
- Retrieve weather and forecasts for building locations
- Clean dataclass models with access to raw API responses
- Context manager support for automatic connection cleanup

## Installation

**From PyPI** (once published):

```bash
pip install sensorlinx
```

**From source:**

```bash
git clone https://github.com/knobunc/sensorlinx.git
cd sensorlinx
pip install .
```

**For development:**

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from sensorlinx import SensorLinxClient

# Authenticate with email and password
with SensorLinxClient.from_credentials("you@example.com", "yourpassword") as client:
    buildings = client.list_buildings()
    devices = client.list_devices(buildings[0].id)
    sample = client.history_sample(buildings[0].id, devices[0].sync_code)
    print(sample.readings)
```

### Using a secrets file

Create `secrets.json`:

```json
{
  "email": "you@example.com",
  "password": "yourpassword"
}
```

Or with a cached token (skips the login request):

```json
{
  "token": "eyJ..."
}
```

Then:

```python
from sensorlinx import SensorLinxClient

with SensorLinxClient.from_secrets("secrets.json") as client:
    user = client.get_current_user()
    print(f"Hello, {user.full_name}")
```

## API Overview

### Authentication

```python
client = SensorLinxClient.from_credentials("email", "password")
client = SensorLinxClient.from_secrets("secrets.json")
client = SensorLinxClient(token="eyJ...")  # pre-existing token

user = client.get_current_user()
token = client.refresh()
```

### Buildings

```python
buildings = client.list_buildings()
building = client.get_building(building_id)
weather = client.get_weather(building_id)
```

### Devices

```python
devices = client.list_devices(building_id)
device = client.get_device(building_id, sync_code)
```

### Historical Readings

```python
# Most recent reading
sample = client.history_sample(building_id, sync_code)

# Today's readings
entries = client.history_today(building_id, sync_code)

# Last N hours
entries = client.history_hours(building_id, sync_code, hours=24)

# Date range
from datetime import datetime, timedelta, timezone
now = datetime.now(timezone.utc)
entries = client.history_range(building_id, sync_code, start=now - timedelta(days=7), end=now)
```

Each `HistoryEntry` has:
- `timestamp` — `datetime` object (or `None`)
- `readings` — `dict` of sensor values
- `raw` — the original API response dict

### Building Managers

```python
managers = client.list_managers(building_id)
client.add_manager(building_id, "colleague@example.com")
client.remove_manager(building_id, manager_id)
```

## Device Types

| Code | Description              |
|------|--------------------------|
| BTU  | BTU/Energy Meter         |
| CPU  | Boiler Controller        |
| ECO  | Geothermal/HVAC Controller |
| FLO  | Flow Sensor              |
| FLW  | Flow Sensor (alternate)  |
| PRE  | Pressure Sensor          |
| PRS  | Pressure Sensor (alternate) |
| SGL  | Single Reading Sensor    |
| SNO  | Snow/Zone Sensor         |
| SUN  | Solar Controller         |
| THM  | Thermostat               |
| ZON  | Zone Controller          |
| ENG  | Energy Meter             |

## Example Script

A complete demonstration is in [`examples/example_client.py`](examples/example_client.py). It shows:

- User profile retrieval
- Building and device listing
- Weather and forecast display
- Live device status (temperatures, demands, stages, pumps, relays)
- Latest reading and 24-hour history summary
- Manager enumeration

Run it with:

```bash
cp secrets.json.example secrets.json
# edit secrets.json with your credentials
python examples/example_client.py
```

## Exceptions

```python
from sensorlinx.exceptions import SensorLinxError, AuthError, NotFoundError, APIError

try:
    client.get_device(building_id, "XXXX-0000")
except NotFoundError:
    print("Device not found")
except AuthError:
    print("Token expired — call client.login() again")
except APIError as e:
    print(f"HTTP {e.status_code}: {e}")
```

## Requirements

- Python 3.10+
- [httpx](https://www.python-httpx.org/) >= 0.25

## Disclaimer

This library is not affiliated with or endorsed by HBX Controls. It is based on reverse engineering of the SensorLinx mobile app for personal automation use. Use at your own risk and in accordance with HBX Controls' terms of service.

## License

[MIT](LICENSE)
