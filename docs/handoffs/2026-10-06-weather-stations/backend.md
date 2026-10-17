# backend handoff — Weather stations

Summary: Six owner-scoped read endpoints for weather stations (farm list of station cards, station detail, series, paginated readings, CSV/JSON export) under `api/sensors/`. They reuse the field-sensor history helpers, which are generalized and give the same responses as before. The old `GET /api/farm/farms/<id>/weather/` is removed. `make test` passes: 290 baseline, minus 14 removed weather tests, plus 50 new, for 326 OK. No migrations.

Files changed:
- `backend/sensors/constants.py`, `aggregation.py`, `serializers.py`, `utils.py`, `openapi.py`, `api.py`, `urls.py`, `tests.py`
- `backend/farm/api.py`, `farm/urls.py`, `farm/tests.py` (removed `FarmWeatherAPIView`, its route and `FarmWeatherTests`; the seed-contract weather test now uses the stations endpoint)
- `docs/ARCHITECTURE.md`

Contract: no `contract.md` existed. The orchestrator's brief is the contract, and the shapes below are now the source of truth. Reverse names are `sensors:<name>`.
| Method + path | name |
|---|---|
| `GET /api/sensors/farms/<farm_id>/stations/` | `farm-stations` |
| `GET /api/sensors/stations/<station_id>/` | `station-detail` |
| `GET /api/sensors/stations/<station_id>/series/` | `station-series` |
| `GET /api/sensors/stations/<station_id>/readings/` | `station-readings` |
| `GET /api/sensors/stations/<station_id>/export/csv/` · `/export/json/` | `station-export-csv` · `station-export-json` |
| ~~`GET /api/farm/farms/<id>/weather/`~~ | removed, now 404 |

Contract deviations (additive or clarifying only):
- Station items carry an extra `farm_id`.
- Reading rows carry an extra `id`, matching the history readings.
- The series has no min/max. The existing history series has none either, so it matches exactly: points are `{t, value, sample_count}`.
- `variable` takes a **semantic key only**, the same as the history endpoints. It does not accept an env variable id.

AC self-check: there is no acceptance-criteria.md. Every item in the brief is covered by tests: ownership 404s and 401s on all 6, each status value plus the 29/31 min boundary, latest and sparkline correctness, bucket tiers 900/3600/21600/86400, pagination order with a tie-break, export BOM/filename/cap/filters, query counts and the schema.

Gotchas:
- **Status** is based on the newest *snapshot*, even one with only null values: `inactive` > `never_seen` > `stale` (more than 30 min, `STATION_STALE_AFTER`) > `online`.
- **latest** lists only active station variables that have at least one non-null value, ordered by env variable name. A variable with no data is absent, not null.
- **sparkline** is `null` when there is no *active* `air_temperature` variable. It is `{…, points: []}` when the variable exists but has no data in the window. The window starts at `floor_hour(now − 24 h)`, so it holds up to 25 hour-aligned points. Empty hours are absent and values are not rounded.
- History endpoints ignore the station's own `is_active`, so an inactive station's stored history stays readable. Inactive *station variables* and null values are excluded everywhere.
- `variable=other` matches every `other`-keyed variable of the station. The series still returns them as separate series, one per `variable_id`.
- Query counts: list 5 (2 when the farm has no stations), detail 4, series 2, readings 3. Exports use 3: ownership, `count()` for the cap, and a streaming cursor.
- Series buckets start at `date_from`, the same as history. Send a `date_from` aligned to the hour or day to get round axis labels.

Decisions:
- `build_series` gained `time_field`/`variable_field` kwargs, with defaults equal to the old behaviour.
- `stream_csv(columns, records)`/`stream_json(records)` are now format-only. The `sensor_export_records`/`station_export_records` functions shape the rows. `CSV_HEADER` became `SENSOR_CSV_COLUMNS`.
- `SensorHistoryFilterSerializer` = `HistoryRangeFilterSerializer` + `plot`. The stations use the base serializer.
- New views are plain `APIView`s. Readings instantiates `SensorHistoryPagination` by hand.

For next agent:
- **Frontend:** remove `farmApi.getWeather`, `useFarmWeatherQuery`, the `FarmWeather` type and its query key. The home weather cards move to `GET sensors/farms/<id>/stations/`. The series response is the same type as the history series, so its chart components can be reused. Reading rows match `SensorReading` without the `plot_*`/`sensor_*` fields. CSV columns are `recorded_at,station,variable,semantic_key,value,unit`. Filename: `historial-estacion-<slug>-YYYYMMDD_YYYYMMDD.<ext>`.
- **QA:** seed farm 1 has online stations plus an inactive one, farm 2 is stale and farm 13 has no stations. The `e2e/frontend/farm.spec.ts` weather-card retry comment refers to the old endpoint.

## Proposed improvements
- `backend/makefile`: add `ARGS` passthrough to `test` (`python manage.py test $(ARGS)`), so a single test class can run through make instead of a raw `docker compose exec … manage.py test`. Belongs in `backend/CLAUDE.md` (Tests) as the documented way to run a subset.
- `backend/CLAUDE.md` (DRF API layer): "A view-type rule (APIView-only vs generics) is in agent specs but not in `backend/CLAUDE.md`, and the repo mixes both. Write the convention down in one place."
