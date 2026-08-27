# api contract — dashboard farm map, plot list, stat cards, plot detail

Slug: `2026-08-22-dashboard-farm-map-and-plots` · Context: [`spec.md`](spec.md) ·
[`acceptance-criteria.md`](acceptance-criteria.md)

**Summary.** Four read-only, owner-scoped endpoints feed `/dashboard` (map + list + stat cards)
and `/dashboard/plots/[id]`: the existing farms and plots lists gain geometry and counts, and two
endpoints are new (plot detail, farm weather). Nothing here writes.

Paths below are written **as the frontend calls them** — relative to the fetcher baseURL `/api`
(`frontend/CLAUDE.md`), so `farm/farms/` is Django's `/api/farm/farms/`. All four live under the
**existing** `path("api/farm/", include((farm_urlpatterns, "farm")))` mount in
`backend/backend/urls.py`; no new top-level mount is created.

## Entities

| Entity | Fields this contract exposes |
| --- | --- |
| `farm.Farm` | `id`, `name`, `address`, `location` (`PointField`, nullable), **`boundary` (new nullable `PolygonField`, SRID 4326 — needs a migration)**, `created_at` |
| `farm.Plot` | `id`, `farm` FK, `name`, `description` (`TextField`, `blank=True` → `""`, never `null`), `geometry` (`PolygonField` 4326, nullable), `centroid` (`PointField`, nullable, set on save), `area_hectares` (`Decimal(10,2)`, nullable — computed on save, `null` exactly when `geometry` is `null`), `created_at`, `updated_at` |
| `sensors.FieldSensor` | `plot` FK (`related_name='field_sensors'`), `is_active` — counted only |
| weather chain | `WeatherStation(farm, is_active)` → `WeatherStationVariableConfiguration(env_variable, is_active)` → `EnvironmentalVariable(semantic_key, unit)`; `WeatherSnapshot(station, recorded_at)` → `WeatherMeasurement(snapshot, station_variable, value Decimal(12,2) nullable)` |

## Endpoints

Auth on all four: `IsAuthenticated`, JWT **Bearer access token in the `Authorization` header**
(`rest_framework_simplejwt.authentication.JWTAuthentication`, the project's only auth class — no
cookies). The frontend `fetcher` already refreshes on 401 and retries once.
No pagination anywhere: the project sets no `DEFAULT_PAGINATION_CLASS`, so list endpoints return a
**bare JSON array**. No query params on any endpoint.

### 1. `GET farm/farms/` — farms list *(existing, extended)*

Ordered by `Farm.Meta.ordering = ['name']`.

**200 OK**

```json
[
  {
    "id": 1,
    "name": "Finca La Esperanza",
    "address": "Vereda El Cairo, Villavicencio, Meta",
    "location": { "type": "Point", "coordinates": [-73.6266, 4.1421] },
    "boundary": {
      "type": "Polygon",
      "coordinates": [[[-73.6300, 4.1450], [-73.6210, 4.1450], [-73.6210, 4.1380], [-73.6300, 4.1380], [-73.6300, 4.1450]]]
    },
    "created_at": "2026-03-11T14:02:31.512340Z"
  }
]
```

- `location`: GeoJSON `Point` or `null`. `boundary`: GeoJSON `Polygon` or `null`.
- **Additive only** — `id`, `name`, `address`, `created_at` keep their names, types and values, and
  the array stays a bare array. The existing frontend `Farm` interface only gains two fields; no
  existing consumer breaks.

**Errors** — `401` `{"detail": "Authentication credentials were not provided."}`. A user with no
`Farmer` row gets `200 []` (owner-lookup scoping), not a 500.

### 2. `GET farm/farms/<farm_id>/plots/` — plots of a farm *(existing, extended)*

Path param `farm_id`: integer. Ordered by `Plot.Meta.ordering = ['name']` — the map's tab order and
the list order are therefore the same (AC-A11Y-3).

**200 OK**

```json
[
  {
    "id": 7,
    "name": "Lote Norte",
    "description": "Arroz de riego, siembra escalonada",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[-73.6291, 4.1443], [-73.6262, 4.1443], [-73.6262, 4.1418], [-73.6291, 4.1418], [-73.6291, 4.1443]]]
    },
    "centroid": { "type": "Point", "coordinates": [-73.62765, 4.14305] },
    "label_point": { "type": "Point", "coordinates": [-73.62765, 4.14305] },
    "area_hectares": "8.42",
    "sensor_count": 3
  },
  {
    "id": 9,
    "name": "Lote Sin Mapear",
    "description": "",
    "geometry": null,
    "centroid": null,
    "label_point": null,
    "area_hectares": null,
    "sensor_count": 0
  }
]
```

- `area_hectares`: **JSON string** (`"8.42"`) or `null`. DRF's `COERCE_DECIMAL_TO_STRING` is not
  overridden in `backend/backend/settings/common.py`, so it defaults to `True`. The existing
  frontend type (`area_hectares: string | null`) is already correct — the frontend must `Number(...)`
  before formatting with `Intl.NumberFormat`. **Do not** flip the setting: it would silently change
  every other decimal on the wire.
- `sensor_count`: integer ≥ 0, **active sensors only** (`FieldSensor.is_active=True`).
- `label_point`: GeoJSON `Point` or `null` (`null` exactly when `geometry` is `null`). **Derived, not
  stored** — `geometry.point_on_surface` (PostGIS `ST_PointOnSurface`), computed per response.
  It is **guaranteed to lie inside the polygon**, which neither `centroid` nor the bounding-box
  centre is: for a concave plot (an L, a U, a crescent) both fall outside the shape, so a marker or
  a name label anchored to them floats over land that is not the plot — or over a neighbouring plot.
  Verified: for an L-shaped polygon, bounding-box centre `(1.5, 1.5)` → outside, `centroid`
  `(1.1, 1.1)` → outside, `point_on_surface` `(0.5, 2.0)` → **inside**.
  The frontend anchors the plot's map pin and its permanent name label to this point, and must not
  fall back to `centroid` or `getBounds().getCenter()` for either.
  `centroid` remains on the wire unchanged (it is a stored model field); it is simply not the right
  anchor for anything that must sit *on* the shape.
- `description`: always a string, `""` when unset (never `null`) — the "sin descripción" fallback
  (AC5) is a frontend concern, triggered by the empty string.
- Satisfies **AC31**.

**Errors** — `404 {"detail": "Not found."}` when `farm_id` does not exist **or** belongs to another
farmer (ownership is part of the lookup — never `200 []`, never `403`); `401` as above.

### 3. `GET farm/plots/<plot_id>/` — plot detail *(new)*

Path param `plot_id`: integer. Scoped by `farm__owner__user=request.user`. Exists so
`/dashboard/plots/[id]` survives a direct load, refresh or bookmark with nothing in the query
cache (AC28).

**200 OK**

```json
{
  "id": 7,
  "name": "Lote Norte",
  "description": "Arroz de riego, siembra escalonada",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-73.6291, 4.1443], [-73.6262, 4.1443], [-73.6262, 4.1418], [-73.6291, 4.1418], [-73.6291, 4.1443]]]
  },
  "centroid": { "type": "Point", "coordinates": [-73.62765, 4.14305] },
  "label_point": { "type": "Point", "coordinates": [-73.62765, 4.14305] },
  "area_hectares": "8.42",
  "sensor_count": 3,
  "farm": { "id": 1, "name": "Finca La Esperanza" },
  "created_at": "2026-04-02T09:15:00.004512Z",
  "updated_at": "2026-08-19T18:44:07.881003Z"
}
```

- Single object, **not** wrapped in a list or an envelope.
- The first six fields are **byte-identical to a list row** (same names, same types) so the frontend
  can declare `interface PlotDetail extends Plot`.
- `farm` is `{id: number, name: string}` — a direct load must be able to name the plot's farm for
  the breadcrumb/back link and to reconcile `useSelectedFarm` when the plot belongs to a farm other
  than the selected one. Nothing else about the farm is exposed here.

**Errors** — `404 {"detail": "Not found."}` for a non-existent id **and** for another farmer's plot,
with no field of the plot in the body (AC29, AC33); `401` as above.

### 4. `GET farm/farms/<farm_id>/weather/` — latest readings for a farm *(new)*

Path param `farm_id`: integer. Same farm ownership check as endpoint 2.

**200 OK** — a JSON **object keyed by `semantic_key`**:

```json
{
  "air_temperature": { "value": 27.4, "unit": "°C", "recorded_at": "2026-08-22T13:50:00Z" },
  "solar_radiation": { "value": 612.0, "unit": "W/m²", "recorded_at": "2026-08-22T13:50:00Z" }
}
```

- **Absence is the only "no data" signal.** A key with no usable reading is **omitted**. There is
  never a key whose value is `null`, never a `value: null`, never a `0` placeholder. A farm with no
  station, no snapshots or no configured variable returns **`200 {}`** — never 404, never 204.
- Each entry has exactly three fields: `value` (**JSON number**, 2 decimals — the view builds this
  dict by hand and must emit `float(measurement.value)`, not the DRF Decimal-as-string default),
  `unit` (string, verbatim from `EnvironmentalVariable.unit`; the frontend never hardcodes `°C` or
  `W/m²`), `recorded_at` (string, see Decisions).
- Keys the frontend consumes: `air_temperature`, `solar_radiation`. The backend returns every
  `SemanticKey` that has a reading **except `other`** (several variables can share `other`, so it
  cannot key a unique entry); the frontend ignores keys it does not render.
- Selection rule (AC22): per semantic key, the reading with the greatest `snapshot.recorded_at`
  across **all active stations** of the farm, considering only `is_active=True` station-variable
  configurations and `value IS NOT NULL`. Ties on `recorded_at` break on the highest station id, so
  the response is deterministic.

**Errors** — `404 {"detail": "Not found."}` for an unknown or unowned `farm_id` (AC33 — the weather
endpoint has exactly the same posture as the other three); `401` as above.

## Surfaces

| Surface / route | Endpoint(s) |
| --- | --- |
| `FarmsMenu` (sidebar switcher) + map boundary & fallback centring | `GET farm/farms/` (`boundary`, `location`) |
| `/dashboard` map view, list view, and the plot-count + sensor-count stat cards (counts derive from this one response — no extra request) | `GET farm/farms/<farm_id>/plots/` |
| `/dashboard` air-temperature + solar-radiation stat cards | `GET farm/farms/<farm_id>/weather/` |
| `/dashboard/plots/[id]` (and `/en/...`), including direct load / refresh / bookmark | `GET farm/plots/<plot_id>/` |

Farm switching re-keys the plots and weather queries by `farm_id`, so both refetch (AC23). The
weather query is independent: its failure must not block the plots query or vice versa (AC26).

## Decisions

1. **Placement.** All four routes stay in `backend/farm/urls.py` under the existing `api/farm/`
   mount. The weather view lives in `backend/farm/api.py` and imports `sensors.models` (safe —
   `sensors.models` refers to farm by string FK, so there is no import cycle). Rationale: the
   resource is "the weather **of a farm**", its authorization is the identical `Farm` ownership
   lookup, and the spec's out-of-scope explicitly rules out a general `sensors` API — minting an
   `api/sensors/` mount for one read-only endpoint would be a mount with no app behind it.
2. **GeoJSON is hand-serialized**, no `djangorestframework-gis`: a `SerializerMethodField` returning
   `json.loads(value.geojson)` (`None` when the field is `null`). That produces exactly
   `{"type": "Polygon", "coordinates": [[[lng, lat], …]]}` and `{"type": "Point", "coordinates": [lng, lat]}`
   — **`type` and `coordinates` only**; if GEOS ever emits a `crs` key, strip it. Polygon rings are
   closed (first coordinate == last) and the outer ring is `coordinates[0]`.
3. **Coordinate order is `[longitude, latitude]`** (GeoJSON / RFC 7946), i.e. `[-73.63, 4.14]` for
   Villavicencio. Leaflet's `L.LatLng` and `L.polygon()` are **`[lat, lng]`** — the reverse. The
   frontend must feed these objects to `L.geoJSON(...)`, which reads GeoJSON order correctly, and
   must never pass `coordinates` straight into `L.polygon`/`L.marker`. Getting this wrong puts every
   Colombian plot in the Indian Ocean, and it fails silently.
4. **`sensor_count` is one annotation, never a per-row query** (AC32):
   `Count('field_sensors', filter=Q(field_sensors__is_active=True))` on the plots queryset — note the
   filter uses the **full related path** (`field_sensors__is_active`), not `is_active`.
   **`distinct=True` is not needed**: the queryset has exactly one multi-valued join, so no row
   fan-out can inflate the count. Add `distinct=True` only if another multi-valued join or a second
   aggregate is ever added to the same queryset. The plot **detail** view annotates the same way
   before `get_object_or_404`, so it is one query too.
5. **Detail uses a distinct serializer**, `PlotDetailSerializer(PlotSerializer)`, adding only `farm`,
   `created_at`, `updated_at`. Subclassing (not a second flat serializer) is what guarantees the
   shared six fields cannot drift apart.
6. **`recorded_at` is ISO 8601 in UTC with a `Z` suffix** (`TIME_ZONE='UTC'`, `USE_TZ=True`, DRF's
   default ISO renderer): `"2026-08-22T13:50:00Z"`, possibly with microseconds
   (`"…T13:50:00.123456Z"`). Parse it (`new Date(...)`) — never string-compare or slice it.
7. **The frontend owns staleness.** The backend sends **no `is_stale` flag** and no age. AC20 already
   requires rendering the reading's age, which only the client can keep truthful as the page sits
   open; a server-computed boolean would disagree with the age shown next to it within a minute of
   arriving. The 30-minute threshold (AC21) is a frontend constant, derived from the same
   `Date.now() - recorded_at` value that renders the age.
8. **Error envelope is DRF's default** `{"detail": "<message>"}` for 401/404 — the frontend keys off
   the **HTTP status**, not the message text (an invalid-token 401 carries a different simplejwt
   body). No 2xx response is ever empty: every success has a JSON body and no endpoint returns 204.
9. **Ownership failures are always 404**, never 403 and never an empty collection — a 403 would
   confirm that someone else's farm or plot exists (AC33).

## Open questions

None. Everything the spec left open (endpoint placement, wire types, absent-key semantics, who owns
staleness, tie-breaking across stations) is decided above.

## Proposed improvements

Not applied by me — for the orchestrator to put to the user.

1. `backend/CLAUDE.md`, replacing the current line *"Geometry fields (`PointField`/`PolygonField`) do
   not serialize through a plain `ModelSerializer`; exposing them needs `djangorestframework-gis`,
   which is not installed yet"* (now out of date and it points the next engineer at a dependency this
   project deliberately declined):
   > Expose geometry fields read-only with a `SerializerMethodField` returning `json.loads(value.geojson)` (`None` when null) — GeoJSON `{"type", "coordinates"}` in **`[longitude, latitude]`** order; `djangorestframework-gis` is only warranted if geometry ever becomes writable through the API.
2. `frontend/CLAUDE.md`, under the map/HTTP rules:
   > Backend geometry arrives as GeoJSON (`[lng, lat]`), the reverse of Leaflet's `LatLng` — render it through `L.geoJSON()`, never by passing `coordinates` to `L.polygon`/`L.marker`.
