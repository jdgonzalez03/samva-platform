# backend handoff — LoRaWAN ingest from The Things Network
Summary:        LoRaWAN payload v2 (fPort 3, 46 B, one `[id u16][values]` block per probe) ingested from TTN MQTT (or dev Mosquitto) by a new `mqtt_ingest` service; 8 new SemanticKeys; irrigation predictions now average field sensors + farm weather station (per-variable "Use in predictions") and expose `input_sources`.
Files changed:  backend/sensors/{models.py,admin.py,utils.py,constants.py,lorawan.py(new),tests.py}
                backend/sensors/management/commands/{mqtt_ingest.py(new),seed_sensor_readings.py}
                backend/sensors/migrations/0006_fieldsensorvariable_use_in_predictions_and_more.py
                backend/sensors/fixtures/{initial_sensors.json,lora_demo_sensors.json(new)}
                backend/predictions/{models.py,utils.py,serializers.py,tests.py,migrations/0003_irrigationprediction_input_sources.py}
                backend/backend/settings/common.py, backend/requirements.txt (paho-mqtt==2.1.0)
                backend/docker-compose.yml, backend/makefile, backend/mosquitto/mosquitto.conf, backend/scripts/simulate_lora_node.py(new)
                Makefile (root loaddata), .env.example, docs/test-sensors/{code-python.py,response-format.js}
                docs/adr/0002-mqtt-ingest-for-lorawan-sensors.md, docs/sensor-ingest-api.md, docs/ARCHITECTURE.md, backend/CLAUDE.md
Contract:       No contract.md for this slug; plan = ~/.claude/plans/pasted-content-id-0a0c-tengo-una-zazzy-wren.md.
                POST/GET /api/predictions/plots/<id>/irrigation/ — each prediction gains
                `"input_sources": {"moisture": {"field": float|null, "station": float|null}, "temperature": {...}, "radiation": {...}}`
                (keys = model inputs, values rounded to 2 dp; predictions created before this change have `{}`).
                422 body unchanged: `{"detail", "missing": [semantic keys]}` — now only when NEITHER source has data.
                POST /api/sensors/ingest/ unchanged (except the new SemanticKey choices are accepted).
Contract deviations: none vs plan. `make simulate-lora --count 3` (plan wording) is not valid make syntax → `make simulate-lora ARGS="--count 3"`.
AC self-check:  Plan §1–5, §7 (backend docs), §8 backend tests ✓. E2E check done live: `make simulate-lora ARGS="--count 2 --interval 2"` → mqtt_ingest logged 9 "probe stored" per uplink; history API on farm 3 / plot 7 returned the 14 readings per uplink; sensors 101–109 `status: online`.
Gotchas:        - `avg_moisture/temperature/radiation` are now the mean of the available source means (one vote per source, not per sample).
                - Station variables default to `use_in_predictions=False`, field variables to True — existing seeded predictions behave as before.
                - Demo probes live on plot 7 "Lote El Rodeo" (Finca La Montaña, user maria.lopez@email.com) — deliberately NOT on juan.perez's farms, whose e2e specs assert 4 variables per plot/farm.
                - In the demo fixture, 102/103 `air_temperature` and all 109 energy variables have `use_in_predictions=false`.
                - `mqtt_ingest` refuses to start (CommandError) on an unknown MQTT_SOURCE or `ttn` without TTN_APP_ID/TTN_API_KEY; web/Celery are unaffected.
                - TTN does not queue while the subscriber is down (lost uplinks). `make mqtt-restart` recreates the container so `.env` changes apply.
Decisions:      handle_uplink resolves the sensor before validating (so a misconfigured probe still stamps last_seen_at), then runs the same SensorIngestSerializer as HTTP (clock skew, decimals); one savepoint per probe. Per-probe failures log on `sensors.mqtt`; the command attaches its own INFO stream handler. Seeder got realistic curves for the new keys. Added `make lint` to backend/makefile (root lint targets the dev.yml stack). Out of scope: TTN Storage Integration backfill, prod compose service, Mosquitto auth.
For next agent: Frontend: add the 8 keys (`leaf_temperature, soil_temperature, soil_water_tension, co2, battery_voltage, battery_current, solar_panel_voltage, solar_panel_current`) to `SensorSemanticKey`; render `input_sources[input].field/station` with "—" for null; handle `input_sources = {}` on old history rows. QA: log in as maria.lopez to see probes 101–109; `make loaddata` then `make simulate-lora ARGS="--count 2"`. Lint: 137 ruff errors remain, all pre-existing (none in new/changed code).

## Proposed improvements
- Rule: "Verify ORM state in dev with the REST API (curl + JWT) rather than `make shell` piped stdin — `make shell` runs `exec` with a TTY and hangs when fed a script." → `backend/CLAUDE.md` (Dev environment).
- Rule: "A test that calls code doing `close_old_connections()` must patch it: inside `TestCase`'s transaction autocommit is off, so Django closes the test's own connection." → `backend/CLAUDE.md` (Tests).
- Rule: "Seed demo/fixture data for new features on a farm the e2e user does not own (e.g. Finca La Montaña): e2e specs assert exact variable/sensor counts on juan.perez's farms." → `backend/CLAUDE.md` (Dev environment).
