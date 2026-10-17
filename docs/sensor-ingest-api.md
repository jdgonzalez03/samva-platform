# Sensor ingest API — integrator guide

How a field sensor (or the gateway it reports through) pushes readings to SAMVA. LoRaWAN nodes do not call this endpoint: they reach SAMVA through The Things Network, see [LoRaWAN vía TTN](#lorawan-vía-ttn). The live, always-current schema is the Swagger UI at `/api/docs/` (operation `api_sensors_ingest_create`); this guide covers what a schema cannot: setup, retries and troubleshooting.

## Before the first upload

1. **The sensor must be registered.** An administrator creates the `FieldSensor` on its plot with the device's hardware **serial number** and maps the variables it measures (`FieldSensorVariable`). Serial numbers are unique across the platform.
2. **Get the API secret.** The farm owner copies it from *Perfil → Acceso API* in the dashboard. It starts with `smv_`.
3. **Check the serial.** *Mis sensores* in the dashboard lists every sensor of the selected farm with its serial and status.

The secret identifies the **owner**, the serial identifies the **sensor**. Every device of the same owner uses the same secret.

## Request

```
POST /api/sensors/ingest/
Content-Type: application/json
X-API-Key: smv_…

{
  "serial_number": "SN-001",
  "recorded_at": "2026-09-29T14:30:00Z",
  "readings": [
    {"variable": "soil_moisture", "value": 31.2},
    {"variable": "air_temperature", "value": 24.8}
  ]
}
```

| Field | Rules |
|---|---|
| `serial_number` | The registered serial of the sending sensor. |
| `recorded_at` | ISO 8601 **with a timezone offset** (`Z` or `-05:00`). The moment the sensor measured, not the moment it sends. At most 5 minutes ahead of the server clock. |
| `readings` | One entry per variable measured at that instant (at least one, each variable once). |
| `readings[].variable` | A semantic key: `soil_moisture`, `air_temperature`, `solar_radiation`, `relative_humidity`, `leaf_temperature`, `soil_temperature`, `soil_water_tension`, `co2`, `battery_voltage`, `battery_current`, `solar_panel_voltage`, `solar_panel_current` or `other`. Must be a variable mapped to this sensor. |
| `readings[].value` | A number with up to 4 decimals, or `null` when the probe failed. |

One request carries one instant. A device that buffered readings while offline sends them one request per instant, oldest first.

## Responses

| Status | Meaning | What the device should do |
|---|---|---|
| `201` | Stored. Body: `{"created": n, "duplicates": m}`. | Move on. `duplicates > 0` means that instant was already stored (a retry after a lost response) — not an error. |
| `400` | Payload invalid: missing offset, future timestamp, unknown or unmapped variable, bad value. Body names the field. | Do **not** retry the same payload; fix the firmware or the sensor's variable mapping. |
| `401` | `X-API-Key` missing or wrong (e.g. the owner regenerated the secret). | Stop and alert; retrying will not help until the secret is updated. |
| `403` | The account or the sensor is inactive. | Stop; contact the administrator. |
| `404` | Serial unknown for this secret (unregistered, or belongs to another owner). | Stop; check the serial in *Mis sensores*. |
| `429` | Rate limit exceeded (120 requests per minute per secret). | Back off and retry later. |
| `5xx` / timeout | Server or network problem. | Retry with exponential backoff; resending is safe. |

**Retries are safe:** a reading is unique per sensor variable and `recorded_at`, so resending the same instant never duplicates data.

## Status in the dashboard

Every request that reaches a registered, active sensor (even one rejected with `400`) updates its *last seen* time. *Mis sensores* shows a sensor **offline** after 45 minutes without any request, and **no data yet** if it never reached the API.

## Examples

### curl

```bash
curl -X POST https://<host>/api/sensors/ingest/ \
  -H "X-API-Key: $SAMVA_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"serial_number":"SN-001","recorded_at":"2026-09-29T14:30:00Z",
       "readings":[{"variable":"soil_moisture","value":31.2}]}'
```

### ESP32 (Arduino core, HTTPClient)

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>

const char* INGEST_URL = "https://<host>/api/sensors/ingest/";
const char* API_SECRET = "smv_...";  // from Perfil → Acceso API
const char* SERIAL_NUMBER = "SN-001";

// Call configTime(0, 0, "pool.ntp.org") in setup(): recorded_at must be real UTC.
String isoNowUtc() {
  time_t now = time(nullptr);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", gmtime(&now));
  return String(buffer);
}

int sendReading(float soilMoisture) {
  HTTPClient http;
  http.begin(INGEST_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_SECRET);

  String body = String("{\"serial_number\":\"") + SERIAL_NUMBER +
                "\",\"recorded_at\":\"" + isoNowUtc() +
                "\",\"readings\":[{\"variable\":\"soil_moisture\",\"value\":" +
                String(soilMoisture, 2) + "}]}";

  int status = http.POST(body);
  http.end();
  return status;  // 201 = stored; see the table above for the rest
}
```

## Troubleshooting

Rejected requests are logged by the backend (`sensors.api` logger) with status, owner id, serial and the error detail — never the secret. Ask an administrator to check them when a device keeps failing.

## LoRaWAN vía TTN

LoRaWAN nodes radio to a gateway that forwards to **The Things Network** (cluster `au1`); TTN decodes each uplink with our formatter and the backend's `mqtt_ingest` service reads it from TTN's MQTT broker. No API secret is involved: the TTN credentials are the trust boundary, and the owner follows from the sensor's plot. Design and trade-offs: [ADR 0002](adr/0002-mqtt-ingest-for-lorawan-sensors.md).

### 1. Register each probe

Every physical probe of a node is its own sensor. Its **id** is a `u16` constant in the firmware ([code-python.py](test-sensors/code-python.py): `ID_AIRE = 101` … `ID_ENERGIA = 109`) and is the sensor's **serial number** in SAMVA. In the admin, create one *Field sensor* per probe on its plot with that serial, and map the variables it sends:

| Probe | Firmware constant | Variables |
|---|---|---|
| SHT30 #1 / DHT | `ID_AIRE` | `air_temperature`, `relative_humidity` |
| MLX90614 | `ID_FOLIAR` | `leaf_temperature`, `air_temperature` (sensor ambient) |
| Auxiliary probe | `ID_AUX` | `air_temperature` |
| SEN0159 | `ID_CO2` | `co2` |
| Watermark 1–3 | `ID_WM1..3` | `soil_water_tension` |
| Soil temperature | `ID_SUELO` | `soil_temperature` |
| INA3221 | `ID_ENERGIA` | `battery_voltage`, `battery_current`, `solar_panel_voltage`, `solar_panel_current` |

Ids are unique across the platform: two nodes must not share them. Untick *Use in predictions* on a variable that should not feed the irrigation model (the MLX90614 ambient temperature, for instance).

### 2. Payload and formatter

Payload v2: 46 bytes, big-endian, **fPort 3**, one `[id u16][values…]` block per probe. Paste [response-format.js](test-sensors/response-format.js) in TTN under *Application → Payload formatters → Uplink → Custom Javascript*. It emits

```json
{"sensors": [{"id": 101, "readings": {"air_temperature": 22.98, "relative_humidity": 89.79}}, …],
 "delta_t_hoja_aire": -0.65}
```

whose `readings` keys are the semantic keys above. An uplink on another fPort (an old v1 node) is rejected as a whole.

### 3. TTN API key and environment

In TTN, *Application → API keys → Add API key* with the right **Read application traffic**. Then set in `backend/.env` (template in the root `.env.example`):

```
MQTT_SOURCE=ttn
TTN_APP_ID=agriculture-unillanos
TTN_API_KEY=NNSXS....
```

and apply it with `make mqtt-restart` (from `backend/`). `MQTT_SOURCE=local` (the default) switches back to the development Mosquitto and the simulator (`make simulate-lora`). Each running `mqtt_ingest` needs its own `MQTT_CLIENT_ID` if two of them subscribe to the same TTN application.

### 4. Diagnose

`make mqtt-logs` follows the `mqtt_ingest` service. On start it prints the source, broker and topic (never the key); then one line per probe: `LoRaWAN probe stored: … serial=101 created=2 duplicates=0`, or `LoRaWAN uplink rejected: dev_eui=… device_id=… serial=… reason=…` for an unknown serial, an inactive sensor, an unmapped variable or an uplink the formatter could not decode. A reading's time is TTN's reception time, truncated to the second, so a redelivered uplink is stored once.

TTN does not queue uplinks while `mqtt_ingest` is down: readings sent during that window are lost.
