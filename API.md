# HBX SensorLinx API Reference

Reverse engineered from APK `com.hbxcontrols.sensorlinx` v1.4600.

## Base URL

```
https://mobile.sensorlinx.co
```

---

## Authentication

The app uses JWT Bearer tokens via the `nuxt-auth` library.

### Login

```
POST /account/login
```

Request body:
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

Response: returns a token in `{ "token": "..." }` — stored as `Bearer` token in `Authorization` header for all subsequent requests.

**Token TTL**: 10,000,000 seconds (effectively permanent until refresh)

### Get Current User

```
GET /account/me
```

Response: returns user object in `{ "user": { ... } }`

### Refresh Token

```
GET /account/refresh
```

### Register

```
POST /account/register
```

Request body:
```json
{
  "email": "user@example.com",
  "password": "...",
  "firstName": "...",
  "lastName": "...",
  "phone": "...",
  "address": "...",
  "country": "...",
  "state": "...",
  "city": "...",
  "zipCode": "...",
  "organizationName": "..."
}
```

### Update Profile

```
PATCH /account/me
```

### Change Password

```
PATCH /account/password
```

### Password Recovery (Email Link)

```
POST /account/recover          # { "email": "..." } — send recovery email
GET  /account/recover/{token}  # verify token from email link
POST /account/recover/update   # { "token": "...", "password": "..." }
```

### Password Recovery (OTP)

```
POST  /account/recover/otp   # { "email": "..." } — send OTP
PATCH /account/recover/otp   # { "email": "...", <otp fields> } — verify OTP + set new password
```

---

## Buildings

### List Buildings

```
GET /buildings
```

### Create Building

```
POST /buildings
```

Request body: building object (name, location, etc.)

### Get Building

```
GET /buildings/{buildingId}
```

### Update Building

```
PATCH /buildings/{buildingId}
```

### Delete Building

```
DELETE /buildings/{buildingId}
```

### Get Weather for Building

```
GET /buildings/{buildingId}/weather
```

### Get Allowed Countries

```
GET /buildings/allowed-countries
```

### Geocode Location

```
POST /buildings/location
```

Request body: `{ "lat": ..., "lng": ... }` — returns map coordinates

---

## Building Managers

### List Managers

```
GET /buildings/{buildingId}/managers
```

### Add Manager

```
PUT /buildings/{buildingId}/managers
```

Request body:
```json
{ "email": "manager@example.com" }
```

### Remove Manager

```
DELETE /buildings/{buildingId}/managers/{managerId}
```

---

## Devices

Devices are identified by a **sync code** — an 8-character string formatted as `XYYY-NNNN` where:
- `X` = series letter (A-Z)
- `YYY` = device type code (3 letters, e.g. BTU, CPU, ECO, etc.)
- `NNNN` = 4-digit numeric identifier

### List Devices

```
GET /buildings/{buildingId}/devices
```

Response: array of device objects

### Get Device

```
GET /buildings/{buildingId}/devices/{syncCode}
```

### Link Device to Building

```
POST /buildings/{buildingId}/devices
```

Request body: `{ "syncCode": "XYYY-NNNN", "pin": "12345" }` (likely)

### Update Device

```
PATCH /buildings/{buildingId}/devices/{syncCode}
```

Request body: device settings object (varies by device type)

### Unlink Device

```
DELETE /buildings/{buildingId}/devices/{syncCode}
```

---

## Device History / Readings

All history endpoints are `POST` — the body specifies the time range/filters.

### Latest Sample

```
POST /buildings/{buildingId}/devices/{syncCode}/history/sample
```

Returns the most recent reading for a device.

### Today's History

```
POST /buildings/{buildingId}/devices/{syncCode}/history/today
```

Request body: `{}` or optional filters

### Last N Hours

```
POST /buildings/{buildingId}/devices/{syncCode}/history/hours
```

Request body: `{ "hours": N }` (optional, defaults to some value)

### Date Range

```
POST /buildings/{buildingId}/devices/{syncCode}/history/range
```

Request body: `{ "start": "ISO8601", "end": "ISO8601" }`

### Full History

```
POST /buildings/{buildingId}/devices/{syncCode}/history
```

---

## Spaces / Zones

```
GET /spaces/{buildingId}/space/{spaceId}
```

---

## Device Types

| Code | Description |
|------|-------------|
| BTU  | BTU/Energy Meter |
| CPU  | Boiler Controller |
| ECO  | Geothermal/HVAC Controller |
| FLO  | Flow Sensor |
| FLW  | Flow Sensor (alternate) |
| PRE  | Pressure Sensor |
| PRS  | Pressure Sensor (alternate) |
| SGL  | Single Reading Sensor |
| SNO  | Snow/Zone Sensor |
| SUN  | Solar Controller |
| THM  | Thermostat / Boiler Thermostat |
| ZON  | Zone Controller |
| ENG  | Energy Meter |

---

## Local Device Provisioning (Wi-Fi Setup)

When pairing a new device, the app connects directly to the device's Wi-Fi access point.

### Device Access Point

The device creates a hotspot. Local API address is computed from the sync code:

```python
identifier = syncCode[-4:]            # last 4 digits of sync code
last_two = int(identifier[-2:])
ip = f"192.168.{last_two + 10}.1"
base_url = f"http://{ip}:2000"
```

### Device AP Credentials

The device's Wi-Fi SSID and password are derived from the sync code:
```
identifier = syncCode[-4:]   # e.g. "1234"
parts = [identifier[0:2], identifier[2:4]]   # ["12", "34"]
pattern = str(int(parts[1]) + 1).zfill(2) + parts[0].zfill(2)
password = str(45 + (int(pattern + pattern) >> 3)).zfill(8)
```

### Scan for Available Networks

```
GET http://{device_ip}:2000?scan=1
```

Response: comma-separated `ssid::rssi` pairs

### Configure Wi-Fi Credentials

```
GET http://{device_ip}:2000?ssid={encoded_ssid}&pass={encoded_password}
```

---

## Request Headers

All API calls to `https://mobile.sensorlinx.co` include:

```
Authorization: Bearer {token}
Accept: application/json, text/plain, */*
Content-Type: application/json
```

---

## Notes

- The app uses two auth endpoints — `/api/auth/*` appears to be an older or alternate path; the active one is `/account/*` with `account/me` for the user object.
- Token is stored in localStorage with key `_token.local`; token expiration at `_token_expiration.local`.
- The app uses `@nuxtjs/auth` strategy named `"local"`.
- Deep linking: the app handles URLs like `https://mobile.sensorlinx.co/...` — the path after `.co` is pushed to the router.
