# Implementation plan — Dashboard farm map, plot list, stat cards, plot detail

Slug: `2026-08-22-dashboard-farm-map-and-plots`

Inputs (authoritative, in precedence order): [`spec.md`](spec.md) ·
[`contract.md`](contract.md) · [`acceptance-criteria.md`](acceptance-criteria.md) ·
[`discovery-ba.md`](discovery-ba.md) · [`discovery-ux.md`](discovery-ux.md).

**How to read this document.** The three area sections (Backend, Frontend, E2E) are
independently actionable: backend and frontend are dispatched **in parallel** and share only
`contract.md`, so anything the two must agree on that is *not* in the contract is written
into [§0 Shared facts](#0-shared-facts-the-only-things-not-in-contractmd) and repeated inside
each area section. Do not read the other area's section to do your work; read §0.

---

## 0. Shared facts (the only things not in `contract.md`)

`contract.md` fixes every endpoint, field name, type and no-data semantic. It does **not** fix
the seed data or the UI copy, and both frontend and E2E depend on them. These are pinned here.

### 0.1 Seed data contract (backend produces it, frontend/E2E assert against it)

The e2e user is `juan.perez@email.com` (farmer pk 1), who owns farms **1 Finca El Tesoro** and
**2 Finca San Vicente** (ordered by name, so *El Tesoro* is selected by default). After
`make loaddata` the state below must hold. Every negative-path AC is reachable from this one
login without touching another user.

| Fact | Farm / row | Which AC needs it |
| --- | --- | --- |
| `boundary` set | Farm 1 *Finca El Tesoro* | AC2 |
| `boundary` **null** | Farm 2 *Finca San Vicente* | AC3 |
| plot with `geometry = null`, `description = ""` | new Plot **pk 29** `Lote Sin Mapear` on Farm 1 | AC5, AC8, AC-A11Y-13 |
| farm with **zero plots** | new Farm **pk 13** `Finca Sin Lotes` (owner 1, `location` set, no boundary) | AC13, AC9 (fallback-to-location branch) |
| **two active** weather stations + one **inactive** station | Farm 1 | AC22, active-only filtering |
| station configured for `air_temperature` **only** (no `solar_radiation`) | Farm 2 | AC19 |
| newest reading ~3 min old | Farm 1 | AC20 |
| newest reading ~95 min old | Farm 2 | AC21 |
| farm with **no station at all** | Farm 13 | AC19 (whole-response `{}`) |
| plot with **0 active** sensors, plot with a mix of active/inactive sensors | Farm 1 plots | AC32, AC11 |
| an `EnvironmentalVariable` with `semantic_key = other` that has readings | Farm 1 station | proves the `other` exclusion |

Farm 13 sorts **after** both existing farms alphabetically (`Finca El Tesoro` < `Finca San
Vicente` < `Finca Sin Lotes`), so the default farm selection and the existing
`e2e/frontend/farm.spec.ts` ordering assumptions are unaffected.

New primary keys (`farm.farm` 13, `farm.plot` 29) are chosen so a re-`loaddata` over an
existing dev database cannot collide with the current rows.

### 0.2 UI copy contract (frontend writes it, E2E selects by it)

Spanish is the default locale and the only one `e2e`'s `frontend` project renders unprefixed.
These exact `es` values go in `layers/dashboard/i18n/locales/es.json`; E2E puts them in the
`T` map. English mirrors go in `en.json` and the E2E-relevant ones in `T_EN`.

| Key | `es` | `en` |
| --- | --- | --- |
| `dashboard.view.label` | `Vista de los lotes` | `Plots view` |
| `dashboard.view.map` | `Mapa` | `Map` |
| `dashboard.view.list` | `Lista` | `List` |
| `dashboard.stats.plots` | `Lotes` | `Plots` |
| `dashboard.stats.sensors` | `Sensores activos` | `Active sensors` |
| `dashboard.stats.temperature` | `Temperatura del aire` | `Air temperature` |
| `dashboard.stats.radiation` | `Radiación solar` | `Solar radiation` |
| `dashboard.stats.noData` | `Sin datos` | `No data` |
| `dashboard.stats.stale` | `Desactualizada` | `Outdated` |
| `dashboard.stats.error` | `No se pudo cargar el clima.` | `Weather could not be loaded.` |
| `dashboard.stats.updated` | `Actualizado {age}` | `Updated {age}` |
| `dashboard.map.region` | `Mapa de la finca, {name}` | `Farm map, {name}` |
| `dashboard.map.alternative` | `La vista de lista muestra la misma información en texto.` | `The list view shows the same information as text.` |
| `dashboard.map.plotLabel` | `{name}, {description}, {count} sensores` | `{name}, {description}, {count} sensors` |
| `dashboard.map.unmapped` | `{count} lote no se muestra en el mapa \| {count} lotes no se muestran en el mapa` | `{count} plot is not shown on the map \| {count} plots are not shown on the map` |
| `dashboard.map.noLocation` | `Esta finca aún no tiene ubicación en el mapa.` | `This farm has no map location yet.` |
| `dashboard.map.basemap` | `Mapa base` | `Basemap` |
| `dashboard.map.street` | `Calles` | `Street` |
| `dashboard.map.satellite` | `Satélite` | `Satellite` |
| `dashboard.map.loading` | `Cargando el mapa` | `Loading the map` |
| `dashboard.plots.noDescription` | `Sin descripción` | `No description` |
| `dashboard.plots.sensors` | `{count} sensor \| {count} sensores` | `{count} sensor \| {count} sensors` |
| `dashboard.plots.area` | `{value} ha` | `{value} ha` |
| `dashboard.plots.viewPlot` | `Ver lote` | `View plot` |
| `dashboard.plots.listLabel` | `Lotes de la finca` | `Farm plots` |
| `dashboard.plotDetail.title` | `Lote {name}` | `Plot {name}` |
| `dashboard.plotDetail.dump` | `Datos del lote` | `Plot data` |
| `dashboard.plotDetail.back` | `Volver al panel` | `Back to dashboard` |
| `dashboard.plotDetail.notFound` | `Lote no encontrado` | `Plot not found` |
| `dashboard.plotDetail.notFoundBody` | `Este lote no existe o no pertenece a tu cuenta.` | `This plot does not exist or does not belong to your account.` |

Reused **unchanged** from `layers/farm/i18n/locales/*.json` (do **not** duplicate them into the
dashboard namespace): `farm.plots.title`, `farm.plots.none`, `farm.plots.noFarm`,
`farm.plots.error`, `farm.plots.retry`. `farm.plots.count` stays for the farm layer's own use
but is **no longer rendered by the dashboard index page** — the plot count moves into a stat
card showing a bare number under the label `dashboard.stats.plots`. This is what breaks
`T.plotCount` in E2E (see §3).

### 0.3 DOM hooks the E2E suite selects by (frontend must ship them)

Leaflet renders vector layers as **SVG `<path>` elements**, which have no useful default role.
Frontend must stamp these so E2E has something stable and a11y has something real:

- each plot **core** path: `data-plot-id="<id>"`, `data-role="plot"`, `role="link"`,
  `tabindex="0"`, `aria-label` = `dashboard.map.plotLabel`, `aria-describedby` = popover id
- each plot **casing** path: `data-role="plot-casing"`, `aria-hidden="true"`, no tabindex
- boundary paths: `data-role="boundary"` / `data-role="boundary-casing"`, `aria-hidden="true"`
- the map region wrapper: `role="region"` with `aria-label` = `dashboard.map.region`
- the basemap selector: a `radiogroup` named `dashboard.map.basemap`, options named
  `dashboard.map.street` / `dashboard.map.satellite`

---

## 1. Backend

Everything lands under the **existing** `path("api/farm/", include((farm_urlpatterns, "farm")))`
mount. No new top-level mount, no new app, no new Python dependency.

Files touched:
`backend/farm/models.py`, `backend/farm/forms.py`, `backend/farm/wagtail_hooks.py`,
`backend/farm/serializers.py`, `backend/farm/api.py`, `backend/farm/urls.py`,
`backend/farm/tests.py`, `backend/farm/migrations/0004_farm_boundary.py` (generated),
`backend/farm/fixtures/initial_farms_with_plots.json`,
`backend/sensors/fixtures/initial_sensors.json` (new),
`backend/sensors/management/commands/seed_weather_readings.py` (new),
root `Makefile`, `backend/makefile`.

### 1.1 `Farm.boundary` migration + Wagtail panel

Mirror exactly how `Plot.geometry` is panelled today — a plain `FieldPanel` on the model, with
the Leaflet **drawing** widget injected through a `ModelForm` returned by the snippet viewset's
`get_form_class()`. `wagtailgeowidget`'s `LeafletPanel` is a *point* picker and cannot draw a
polygon; that is why `Plot` uses `django-leaflet`'s `LeafletWidget` instead, and `Farm` must do
the same.

1. `farm/models.py` — add to `Farm`:
   `boundary = gis_models.PolygonField(blank=True, null=True, srid=4326, ...)` with
   `help_text`/`verbose_name` in Spanish via `gettext_lazy`, matching the surrounding style.
2. `farm/models.py` — add a **new** `MultiFieldPanel([FieldPanel("boundary")],
   heading=_("Límite de la finca"))` to `Farm.panels`, placed **after** the existing
   `_("Ubicación")` panel. Keep it in its own panel rather than merging it into `Ubicación`:
   that group already renders `wagtailgeowidget`'s `GeoAddressPanel` + `LeafletPanel`, and
   stacking a second, differently-initialised Leaflet stack inside the same collapsible group
   is the most likely source of a silent JS init failure.
3. `farm/forms.py` — add `FarmAdminForm(forms.ModelForm)` alongside `PlotAdminForm`, reusing the
   module-level `LEAFLET_WIDGET_ATTRS`:
   `boundary = gis_forms.PolygonField(widget=LeafletWidget(attrs=LEAFLET_WIDGET_ATTRS), required=False, label=..., help_text=...)`,
   `class Meta: model = Farm; fields = '__all__'`.
4. `farm/wagtail_hooks.py` — `WagtailFarmAdmin.get_form_class(self, for_update=False)` returns
   `FarmAdminForm`, byte-for-byte the same override `WagtailPlotAdmin` already has.
5. `make migrations` then `make migrate` (never `python manage.py` directly). Expected file:
   `farm/migrations/0004_farm_boundary.py`, a single `AddField`. Nullable + blank, so no
   default and no data migration.

**Manual verification (not automatable):** open `/admin/snippets/farm/farm/edit/1/`, confirm
both the address/point picker *and* the polygon drawing tools render and save on the same page.
If they conflict, the fallback is to move `boundary` to its own Wagtail panel tab or drop the
point picker to a plain `FieldPanel` — report before choosing.

### 1.2 `sensor_count`: one annotation, one place

Per `contract.md` §Decisions 4, and this is the AC32 gate. Put the annotation on a **queryset
method** so the list view, the detail view and any future reuse cannot diverge:

- `farm/models.py`: `class PlotQuerySet(models.QuerySet)` with
  `with_sensor_count(self)` returning
  `self.annotate(sensor_count=Count("field_sensors", filter=Q(field_sensors__is_active=True)))`,
  and `objects = PlotQuerySet.as_manager()` on `Plot`.
  - the filter uses the **full related path** `field_sensors__is_active`, not `is_active`
  - **no `distinct=True`** — exactly one multi-valued join, so no row fan-out. Add it only if a
    second multi-valued join or aggregate is ever added to the same queryset.
  - `as_manager()` makes the method available on the reverse accessor too, so
    `farm.plots.with_sensor_count()` works — that is why the list view keeps its current shape.
  - Managers are not serialised into migrations (`use_in_migrations` defaults to `False`), so
    this adds no migration.
  - `Plot.Meta.ordering = ["name"]` stays; `name` is a local column, so the implicit `GROUP BY`
    the annotation introduces pulls in no extra join.

Import `Count`/`Q` from `django.db.models` in `farm/models.py`.

### 1.3 Serializers

`farm/serializers.py`. Geometry is hand-serialised — **no `djangorestframework-gis`**.

- module-level helper (used by both serializers):
  `def to_geojson(value): return None if value is None else json.loads(value.geojson)`.
  GEOS emits `{"type", "coordinates"}` only; if a `crs` key ever appears, pop it in this one
  helper. Coordinates are `[longitude, latitude]` (RFC 7946) — do not reorder.
- `FarmSerializer` gains `location` and `boundary` as `SerializerMethodField()`s, both
  `to_geojson(...)`. Field order in `Meta.fields`:
  `['id', 'name', 'address', 'location', 'boundary', 'created_at']`.
- `PlotSerializer` gains `geometry` and `centroid` as `SerializerMethodField()`s and
  `sensor_count = serializers.IntegerField(read_only=True)` (reads the annotation).
  `Meta.fields = ['id', 'name', 'description', 'geometry', 'centroid', 'area_hectares', 'sensor_count']`.
  `area_hectares` stays a `DecimalField` → serialises as the JSON **string** `"8.42"`;
  **do not** touch `COERCE_DECIMAL_TO_STRING` in `backend/backend/settings/common.py`.
- `PlotDetailSerializer(PlotSerializer)` — subclass, never a second flat serializer — adds
  `farm = FarmSummarySerializer(read_only=True)` (a tiny `ModelSerializer` exposing only
  `id`, `name`), plus `created_at`, `updated_at`, via
  `Meta.fields = PlotSerializer.Meta.fields + ['farm', 'created_at', 'updated_at']`.
  Subclassing is what guarantees the six shared fields cannot drift from a list row.

### 1.4 Views and routes

`farm/api.py` (all views set `permission_classes = [IsAuthenticated]` explicitly — the project
has no `DEFAULT_PERMISSION_CLASSES`, so the DRF default is `AllowAny`).

- `FarmPlotListAPIView.get_queryset()` — unchanged ownership lookup, then
  `return farm.plots.with_sensor_count()`. **2 queries total** (farm lookup + plot list).
- `PlotDetailAPIView(generics.RetrieveAPIView)` — `serializer_class = PlotDetailSerializer`,
  `get_object()` does
  `get_object_or_404(Plot.objects.with_sensor_count().select_related("farm"), pk=self.kwargs["plot_id"], farm__owner__user=self.request.user)`.
  Ownership is **part of the lookup**, so another farmer's plot 404s (never 403, never an empty
  body containing a field of the plot). **1 query.**
- `FarmWeatherAPIView(APIView)` — see §1.5.
- `farm/urls.py` adds:
  - `path("plots/<int:plot_id>/", PlotDetailAPIView.as_view(), name="plot-detail")`
  - `path("farms/<int:farm_id>/weather/", FarmWeatherAPIView.as_view(), name="farm-weather")`

  Route order does not matter (`plots/` and `farms/` do not overlap). The `app_name = "farm"`
  namespace already exists, so `reverse("farm:plot-detail", args=[7])` works in tests.

### 1.5 The weather query — latest reading per `semantic_key` (and the query-count risk)

**The risk, stated plainly.** The obvious implementation — loop the farm's active stations, and
for each, loop its active variable configurations and take the newest measurement — is
`O(stations × variables)` queries and grows every time an admin configures a variable. A farm
with 3 stations × 6 variables is 18+ queries for two numbers on screen. Do not write it.

**The implementation.** One `DISTINCT ON` query over `WeatherMeasurement`, which is exactly the
contract's selection rule (greatest `snapshot.recorded_at` across all active stations, ties
broken on the highest station id) expressed as an ordering:

```
WeatherMeasurement.objects
    .filter(
        station_variable__station__farm=farm,
        station_variable__station__is_active=True,
        station_variable__is_active=True,
        value__isnull=False,
    )
    .exclude(station_variable__env_variable__semantic_key=SemanticKey.OTHER)
    .select_related("snapshot", "station_variable__env_variable")
    .order_by(
        "station_variable__env_variable__semantic_key",
        "-snapshot__recorded_at",
        "-station_variable__station_id",
    )
    .distinct("station_variable__env_variable__semantic_key")
```

- `DISTINCT ON` requires the leading `order_by` expressions to match the `distinct()` fields —
  they do. It is **PostgreSQL-only**; this project is PostGIS, so that is fine, and it is worth
  a one-line comment in the view saying so.
- The `-station_variable__station_id` term is the contract's deterministic tie-break.
- `select_related` is what keeps `unit` and `recorded_at` off a second query.
- Total for the endpoint: **2 queries** — `get_object_or_404(Farm, pk=farm_id, owner__user=request.user)`
  plus the measurement query. Constant in the number of stations, variables and snapshots.

Response building, by hand (this view does **not** use a serializer):

```
{
    m.station_variable.env_variable.semantic_key: {
        "value": float(m.value),
        "unit": m.station_variable.env_variable.unit,
        "recorded_at": m.snapshot.recorded_at,
    }
    for m in queryset
}
```

- `float(m.value)` — the contract pins `value` as a **JSON number**, not DRF's
  Decimal-as-string. This is hand-built, so the setting does not apply.
- `recorded_at` renders through DRF's default ISO-8601 encoder → `"2026-08-22T13:50:00Z"`
  (`TIME_ZONE='UTC'`, `USE_TZ=True`), possibly with microseconds.
- A key with no usable reading is **simply not in the dict**. Never `null`, never `0`, never a
  key with a null value. A farm with no station returns `200 {}` — never 404, never 204.
- `SemanticKey.OTHER` is excluded because several variables can share it and it cannot key a
  unique entry.
- The view imports `sensors.models` — safe, no import cycle (`sensors.models` refers to farm by
  string FK).

### 1.6 Fixtures and keeping `recorded_at` recent

**How `make loaddata` works today** (checked, both root `Makefile` and `backend/makefile`): it is
three literal `manage.py loaddata <path>` calls — `accounts` → `farmer` → `farm`. There is **no
management-command infrastructure in the repo at all** (`find backend -type d -name management`
is empty). Django fixtures are static JSON, so a fixture physically cannot express "three
minutes ago"; a frozen `recorded_at` makes every weather card read *"hace 7 meses"* forever,
which the spec forbids. Therefore: **static rows in a fixture, time-relative rows in a
management command.**

**(a) `backend/farm/fixtures/initial_farms_with_plots.json`** — edited in place:
- add `"boundary": "SRID=4326;POLYGON ((...))"` to every farm **except farm 2 and farm 13**
  (farm 2's null boundary is what AC3 is tested against). Each polygon must be a closed ring
  that **encloses that farm's plots** with a little margin — take the min/max of the farm's plot
  coordinates and pad by ~0.002°. Farms 3–12 get boundaries too so the admin/demo is coherent.
- add `farm.plot` **pk 29** `Lote Sin Mapear` on farm 1 with `"description": ""`,
  `"geometry": null`, `"centroid": null`, `"area_hectares": null`.
- add `farm.farm` **pk 13** `Finca Sin Lotes`, owner 1, `location` set (near farm 1),
  `boundary` null, and no plots.

**(b) `backend/sensors/fixtures/initial_sensors.json`** — new, all time-independent rows, in
dependency order so a single `loaddata` succeeds:
1. `sensors.environmentalvariable` — `air_temperature` (`°C`), `solar_radiation` (`W/m²`),
   `relative_humidity` (`%`), `soil_moisture` (`%`), and one `other` (e.g. `Presión barométrica`,
   `hPa`) so the `other`-exclusion has something to exclude.
2. `sensors.weatherstation` — farm 1: two `is_active: true` stations **and** one
   `is_active: false` station; farm 2: one active station; farms 3–12: one active station each;
   farm 13: **none**.
3. `sensors.weatherstationvariableconfiguration` — farm 1's two active stations get
   `air_temperature` + `solar_radiation` + the `other` variable; farm 1's **inactive** station
   also gets `air_temperature` (so "active stations only" is provable); **farm 2's station gets
   `air_temperature` only** — that is AC19's missing-key case.
4. `sensors.fieldsensor` — across farm 1's plots: plot 1 gets 3 active + 1 inactive, plot 2 gets
   1 active, plot 29 gets **0**. Farm 2's plots get 2 and 1. Others get 1–2 each.
5. `sensors.fieldsensorvariable` — one row per sensor; cheap, and keeps the admin coherent.

`api_key`/`api_secret` in the fixture must be obvious dummies (`"seed-not-a-real-key"`) — these
rows are credentials-shaped.

**(c) `backend/sensors/management/commands/seed_weather_readings.py`** — new, plus the
`management/` and `management/commands/` packages with `__init__.py`. It owns everything with a
timestamp:
- for every **active** station that has at least one active variable configuration, delete that
  station's existing `WeatherSnapshot` rows (cascade removes their measurements — this is what
  makes the command idempotent and re-runnable), then create `--count` (default 12) snapshots at
  5-minute intervals ending at `timezone.now() - lag`, with one `WeatherMeasurement` per active
  configuration and a plausible value per `semantic_key`
  (`air_temperature` 18–30, `solar_radiation` 0–950, `relative_humidity` 40–95, `soil_moisture`
  20–60, `other` 900–1015), rounded to 2 decimals.
- `lag` is **3 minutes** for every station **except farm 2's**, which uses **95 minutes** —
  that single asymmetry is what makes the AC21 "desactualizada" badge visible in dev without any
  clock manipulation.
- flags: `--count`, `--interval-minutes`, `--stale-minutes`, `--farm <id>`; defaults must be the
  values above so a bare `manage.py seed_weather_readings` reproduces the §0.1 table.
- respect `WeatherSnapshot`'s `unique_together ('station', 'recorded_at')` — the delete-first
  approach already does.

**(d) Make targets** — extend **both** `Makefile` (root, `-f docker-compose.dev.yml`) and
`backend/makefile` (plain `docker compose exec`), keeping each file's own compose invocation:
- append to the existing `loaddata` target:
  `... loaddata sensors/fixtures/initial_sensors.json` then `... seed_weather_readings`
- add a standalone `seed-weather:` target running only `seed_weather_readings`, so a dev whose
  database has been sitting for a day can refresh the timestamps in one command without
  re-loading everything. Mention it in `e2e/README.md` (see §3).

*Alternative considered and rejected:* seeding snapshots as a static fixture plus a second
command that shifts their timestamps — two moving parts where one does the job, and the fixture
would still be wrong on a bare `loaddata`.

### 1.7 Django tests (`make test`, from `backend/`)

All in `backend/farm/tests.py`. The existing `FarmAPITestCase` has **two assertions that this
change breaks** and that must be updated, not deleted:
`test_farm_list_serializes_the_agreed_fields` (exact key set gains `location`, `boundary`) and
`test_plot_list_returns_only_the_plots_of_the_requested_farm` (exact key set gains `geometry`,
`centroid`, `sensor_count`).

New coverage, grouped in new `APITestCase` classes so `setUpTestData` stays readable:

**`PlotListSerializationTests` — AC31**
- a plot with geometry serialises `geometry` as `{"type": "Polygon", "coordinates": [[[lng, lat], …]]}`
  with the ring closed and **no `crs` key**, `centroid` as a GeoJSON `Point`, `area_hectares` as
  the **string** `"…"`, `sensor_count` as an `int`
- a plot without geometry serialises `geometry`, `centroid`, `area_hectares` as `null` and
  `sensor_count` as `0`
- `description` of an unset plot is `""`, never `None`
- longitude comes **first**: assert `coordinates[0][0][0] < 0` and `coordinates[0][0][1] > 0`
  for a Colombian polygon — this is the one assertion that catches a silent `[lat, lng]` swap

**`PlotSensorCountTests` — AC32 (the N+1 gate)**
- `sensor_count` counts **active only**: a plot with 3 active + 2 inactive sensors reports `3`
- **constant query count**: run the endpoint against a farm with 2 plots and against a farm with
  12 plots inside `assertNumQueries(N)` with the *same* `N`. Derive `N` once by running the test
  and reading the failure message — **do not guess it**, and do not let the two calls use
  different numbers. Expected today: `2` (farm ownership lookup + annotated plot list) under
  `force_authenticate` (which sets `request.user` directly, so there is no user query). Add a
  comment naming what the two queries are, so the next person who adds one knows what they
  changed.

**`PlotDetailTests` — AC29/AC33**
- own plot → `200`, body is a **single object** (not a list), the six shared fields are
  byte-identical to the same plot's list row (assert by comparing the two responses' shared
  keys), plus `farm: {id, name}`, `created_at`, `updated_at`
- another farmer's plot → `404` with `{"detail": "Not found."}` and **no field of the plot** in
  the body (assert the plot's `name` string is not in `response.content`)
- unknown id → `404`; unauthenticated → `401`
- `assertNumQueries` — the detail view is **1 query**

**`FarmWeatherTests` — the weather endpoint's absent-key semantics + AC22/AC33**
- two active stations, the second with a **newer** snapshot → the response carries the newer
  station's `value` (AC22)
- equal `recorded_at` on two stations → the **higher station id** wins (deterministic tie-break)
- an **inactive** station with the newest reading is ignored
- an **inactive variable configuration** is ignored
- a measurement with `value = None` is ignored, and if it is the only one for that key the key
  is **absent** — not `null`, not `0`
- a variable whose `semantic_key` is `other` never appears as a key
- farm with no station → `200 {}` (**not** 404, **not** 204)
- key present → exactly three fields `{value, unit, recorded_at}`; `value` is a
  `float`/`int` (`assertIsInstance(..., float)` on the parsed JSON — use `response.json()`, not
  `response.data`, so the Decimal-as-string default would be caught); `unit` is verbatim from
  `EnvironmentalVariable.unit`
- `recorded_at` parses as ISO-8601 and ends in `Z`
- another farmer's farm → `404`; unknown farm id → `404`; unauthenticated → `401`
- `assertNumQueries(2)`, asserted **twice**: once with one station and once with three, to prove
  the count does not grow with stations

**`FarmListSerializationTests` — the farms extension**
- `boundary` is GeoJSON `Polygon` when set and `null` when unset; `location` likewise for `Point`
- the response stays a **bare array** (no pagination envelope) and `id`/`name`/`address`/
  `created_at` keep their names and values (the additive-only guarantee)

Run with `make test` from `backend/`. Never `python manage.py` directly.

### 1.8 Backend risks

| Risk | Mitigation |
| --- | --- |
| Two Leaflet stacks (`wagtailgeowidget` point picker + `django-leaflet` polygon widget) on the same Farm admin form | `boundary` in its own `MultiFieldPanel`; manual verification of the edit page is a required step, not optional |
| `assertNumQueries` is brittle and invites hard-coding a wrong number | Assert the *same* number for two different row counts; comment what each query is |
| `DISTINCT ON` is PostgreSQL-only | Documented in a comment; the project is PostGIS and will not move |
| A future second aggregate on the plots queryset silently inflates `sensor_count` | Comment on `with_sensor_count` naming the `distinct=True` condition |
| `loaddata` over an existing dev DB | New pks (farm 13, plot 29) chosen to avoid collisions; `seed_weather_readings` is delete-then-create |
| Seeded weather ages out during a long dev session | `make seed-weather` re-stamps in one command; E2E does not depend on seed freshness (§3) |

---

## 2. Frontend

**Layer ownership (spec, resolved decision 8).** Pages and presentational components live in the
`dashboard` layer; **all** data — types, api module, query keys, query composables — lives in the
`farm` layer. This follows the sanctioned one-way `dashboard → farm` dependency already recorded
in `frontend/CLAUDE.md`; `farm` never imports from `dashboard`.

**Before you start:** adding or renaming a file under a layer's `app/{composables,utils}`
invalidates the running dev server's module graph — restart `npm run dev` after creating them,
or the stale module 404s and route navigation aborts with no visible error.

### 2.1 `farm` layer additions (data only)

`frontend/layers/farm/app/types/farm.ts`
- `export interface GeoJSONPolygon { type: 'Polygon'; coordinates: [number, number][][] }`
- `export interface GeoJSONPoint { type: 'Point'; coordinates: [number, number] }`
- `Farm` gains `location: GeoJSONPoint | null` and `boundary: GeoJSONPolygon | null`
- `Plot` gains `geometry: GeoJSONPolygon | null`, `centroid: GeoJSONPoint | null`,
  `sensor_count: number`. `area_hectares: string | null` stays a **string** (DRF's
  `COERCE_DECIMAL_TO_STRING`) — components must `Number(...)` before `Intl.NumberFormat`.
- `export interface PlotDetail extends Plot { farm: { id: number; name: string }; created_at: string; updated_at: string }`
  — `extends`, because the contract guarantees the six shared fields are byte-identical
- `export interface WeatherReading { value: number; unit: string; recorded_at: string }`
- `export type WeatherSemanticKey = 'air_temperature' | 'solar_radiation'`
- `export type FarmWeather = Partial<Record<string, WeatherReading>>` — **`Partial`/optional is
  the type-level expression of "absence is the only no-data signal"**. The backend may return
  other semantic keys; the frontend ignores what it does not render. There is never a
  `value: null`.

`frontend/layers/farm/app/utils/api/farm.ts` — add to the existing `farmApi` object (paths are
relative to the fetcher baseURL, trailing slash required):
- `getPlot: (plotId: number) => fetcher.get<PlotDetail>(\`farm/plots/${plotId}/\`)`
- `getWeather: (farmId: number) => fetcher.get<FarmWeather>(\`farm/farms/${farmId}/weather/\`)`

`frontend/layers/farm/app/constants/query-keys.ts` — add `PLOT = 'plot'` and `WEATHER = 'weather'`
to `FarmQueryKey`.

`frontend/layers/farm/app/composables/usePlotQuery.ts` — new, following `useFarmPlotsQuery`
exactly (plain-object options factory + `as const` key, **not** the `queryOptions()` helper):
- `plotQueryOptions(plotId: Ref<number | null>)` → key `[FarmQueryKey.ROOT, FarmQueryKey.PLOT, plotId]`
- `usePlotQuery(plotId)` → `enabled: () => hasTokens() && plotId.value !== null`
- add `retry: (failureCount, error) => (error as { status?: number }).status === 404 ? false : failureCount < 3`
  so a 404 renders the not-found state immediately instead of after three retries

`frontend/layers/farm/app/composables/useFarmWeatherQuery.ts` — new, identical shape to
`useFarmPlotsQuery`: key `[FarmQueryKey.ROOT, FarmQueryKey.WEATHER, farmId]`,
`enabled: () => hasTokens() && farmId.value !== null`. Putting `farmId` **in the key** is what
makes AC23 work with no watcher: switching farms re-keys and refetches. The weather query is
**independent** of the plots query — a weather failure must not block plots or vice versa
(AC26), which falls out of them being two separate `useQuery` calls with separate keys.

Both new composables are picked up by the farm layer's existing
`imports.dirs: ['./app/composables']` in `layers/farm/nuxt.config.ts`, so the dashboard layer
auto-imports them with no cross-layer file import.

### 2.2 `dashboard` layer — page composition

`frontend/layers/dashboard/app/pages/dashboard/index.vue` — rewritten body, same
`definePageMeta({ middleware: ['auth'], layout: 'dashboard' })`, same `UDashboardPanel` /
`UDashboardNavbar` header, same `useHead`.

DOM order inside `#body > UContainer` — **this order is load-bearing**:

1. **Stat cards** — `<UPageGrid class="lg:grid-cols-4 …">` of four `<UPageCard variant="subtle">`,
   harvesting the exact `:ui` treatment from the deleted `FarmStats.vue` (rounded ring leading
   icon, `font-normal text-muted text-xs uppercase` title, `text-2xl font-semibold` value,
   `lg:rounded-none first:rounded-l-lg last:rounded-r-lg` seam). The seam classes only make sense
   in the 4-across row — verify they do not leak into the stacked `sm` breakpoints.
2. **Section header** — the farm name (`<h2>`) on one line with the `UTabs` triggers and the
   basemap selector.
3. **`UTabs`** with **real content panels** and `:unmount-on-hide="false"`.

`UTabs` configuration:
```
:items="[{ label: t('dashboard.view.map'), icon: 'i-lucide-map', value: 'map', slot: 'map' },
         { label: t('dashboard.view.list'), icon: 'i-lucide-list', value: 'list', slot: 'list' }]"
:model-value="mode" @update:model-value="setMode"
:unmount-on-hide="false" variant="pill" :aria-label="t('dashboard.view.label')"
```
- **Never** `:content="false"` with a hand-rolled panel: the triggers still emit `aria-controls`
  pointing at an element that no longer exists, and axe flags it (AC-A11Y-1/2).
- `:unmount-on-hide="false"` keeps the Leaflet instance alive across switches — a remount would
  refetch tiles and lose the viewport. **Consequence:** the hidden panel has zero size, so
  Leaflet's cached dimensions go stale. The map component must call `map.invalidateSize()` when
  its panel becomes visible again. This is the single most likely "the map is grey after
  switching tabs" bug in this feature.
- Reka supplies `role="tablist"`, roving tabindex, arrow-key navigation and `aria-selected`
  (AC-A11Y-2) — do not hand-roll any of it.
- The toggle **precedes the map in DOM order** because the list is the accessible alternative to
  the Leaflet canvas, not a convenience (AC-A11Y-6).

State wiring in `<script setup>`:
```
const { selectedFarm, isPending: farmsPending } = useSelectedFarm()
const farmId = computed(() => selectedFarm.value?.id ?? null)
const { data: plots, isPending: plotsPending, isError: plotsError, refetch: refetchPlots } = useFarmPlotsQuery(farmId)
const { data: weather, isPending: weatherPending, isError: weatherError, refetch: refetchWeather } = useFarmWeatherQuery(farmId)
```
Destructure — `useQuery` returns a bag of refs, and `query.isPending` used straight in a template
is a Ref object and always truthy. Template `@click` handlers wrap `refetch` to return `void`
(vue-tsc rejects the promise type on `@click`).

Derived values (AC18: both counts come from the plots response, **no extra request**):
- `plotCount = plots.value?.length ?? 0`
- `sensorCount = plots.value?.reduce((total, plot) => total + plot.sensor_count, 0) ?? 0`

State vocabulary — extend the one the page already uses, do not invent a second:
`farmsPending || plotsPending` → skeleton with `aria-busy="true"`; `!selectedFarm` →
`farm.plots.noFarm` (AC24 — and the map is **not** rendered at all in this state);
`plotsError` → text + `UButton` Retry inside `role="alert"` (AC25, AC-A11Y-10);
`plotCount === 0` → `UEmpty` with `farm.plots.none` in **both** panels (AC13).

### 2.3 The Leaflet map component

`frontend/layers/dashboard/app/components/dashboard/PlotsMap.client.vue` — **new, and this is the
app's first map.** `leaflet` is installed but imported nowhere, and its CSS is loaded nowhere.

**Client-only + dynamically imported + CSS out of the shared bundle.** Three separate things,
all required:
1. The file is named `.client.vue` — Nuxt never renders it on the server. Leaflet touches
   `window` at import time.
2. `index.vue` renders it as `<LazyDashboardPlotsMap>` inside `<ClientOnly>`, so the component
   lands in its own async chunk rather than the dashboard route chunk.
3. `import 'leaflet/dist/leaflet.css'` goes **inside** `PlotsMap.client.vue`'s `<script setup>`.
   Vite hoists it into that component's own CSS chunk. **Do not** add it to the `css: []` array
   in `frontend/nuxt.config.ts` — that array is the shared entry, and the SSR landing page must
   not pay ~15 kB of map CSS for a page with no map.
   **Verification step (do it, it is cheap):** `npm run build`, then confirm `leaflet-container`
   appears in exactly one non-entry `.output/public/_nuxt/*.css` chunk and not in the entry CSS.
4. Leaflet's JS is additionally deferred: `const L = (await import('leaflet')).default` inside
   `onMounted`, not a top-level import, so the chunk is fetched only when the map actually mounts.

**The `<ClientOnly>` same-height fallback (AC-A11Y-10 and no hydration jump):**
```
<ClientOnly>
  <LazyDashboardPlotsMap … />
  <template #fallback>
    <div :class="MAP_HEIGHT_CLASS" aria-busy="true" role="status">
      <USkeleton class="size-full" /> <span class="sr-only">{{ t('dashboard.map.loading') }}</span>
    </div>
  </template>
</ClientOnly>
```
`MAP_HEIGHT_CLASS` is a single exported constant in
`frontend/layers/dashboard/app/constants/map.ts` (`'h-[60vh] min-h-80 lg:h-[520px]'`) used by
**both** the fallback and the map's own container — a fallback of a different height is the
hydration jump this is meant to prevent. Never `100vh` (mobile browser chrome), and never a
height that collapses to `0` inside a flex parent — Leaflet needs a measurable box.

**`[lng, lat]` vs `[lat, lng]` — the failure that is silent.** Backend GeoJSON is
`[longitude, latitude]` (RFC 7946): `[-74.10, 4.59]` for Colombia. Leaflet's `L.LatLng`,
`L.polygon()`, `L.marker()` and `map.setView()` are **`[latitude, longitude]`** — the reverse.
- Draw everything through `L.geoJSON(featureCollection, { … })`, which reads GeoJSON order
  correctly. **Never** pass `coordinates` into `L.polygon`/`L.marker`.
- The **only** place a manual swap is allowed is the `Farm.location` fallback centring:
  `map.setView([location.coordinates[1], location.coordinates[0]], 14)`. Comment it.
- Getting this wrong puts every Colombian plot in the Indian Ocean and throws no error.

**Panes and the stroke casing (AC-A11Y-7 — the price of the satellite decision).** A single
stroke colour cannot hold ≥3:1 against photographic imagery. Every shape is therefore drawn
**twice**: a wide near-black *casing* underneath and a narrower light *core* on top. Whatever the
tiles look like, one of the two contrasts with them and the two always contrast with each other.
- `map.createPane('casing')` z-index 400, `map.createPane('core')` 410, `map.createPane('labels')` 420
- plot casing: `{ pane: 'casing', color: '#0a0a0a', weight: 7, opacity: 0.9, fill: false }`
- plot core: `{ pane: 'core', color: '#f8fafc', weight: 3, opacity: 1, fillColor: <plot hue>, fillOpacity: 0.22 }`
- boundary casing/core: same pairing, plus `dashArray: '10 6'` on **both** — the farm boundary is
  distinguished from plots by **stroke style, not hue**, so it survives greyscale (AC-A11Y-7)
- **permanent name label** per plot: `L.tooltip({ permanent: true, direction: 'center',
  interactive: false, className: 'samva-plot-label' })`, styled with a dark `text-shadow` halo,
  and its element marked `aria-hidden="true"` (the plot path already carries the name in its
  `aria-label`; without this the screen reader hears every name twice)
- hover/focus adds a **weight change** (core `weight: 3 → 5`), never only a hue shift

**Focusable plot shapes (AC-A11Y-3/4).** In `onEachFeature`, once the layer is added, take
`layer.getElement()` (the SVG `<path>`) and set:
`tabindex="0"`, `role="link"`, `data-plot-id`, `data-role="plot"`,
`aria-label = t('dashboard.map.plotLabel', { name, description: description || t('dashboard.plots.noDescription'), count: sensor_count })`,
and `aria-describedby` = the popover content's id.
- Features are added in the **plots array order**, which the contract guarantees is
  `Plot.Meta.ordering = ['name']` — the same order as the list view (AC-A11Y-3).
- Focus indicator: a CSS `:focus-visible { outline: 3px solid …; outline-offset: 2px }` on
  `path[data-role='plot']` **and** a JS `setStyle({ weight: 5 })` on focus. Two mechanisms
  because SVG outline rendering is not uniformly reliable, and because the indicator must clear
  ≥3:1 against both its own fill and the tiles.
- `keydown` Enter/Space → `navigateTo(localePath(\`/dashboard/plots/${id}\`))`, `preventDefault()`
  on Space so the page does not scroll.
- Casing paths get `aria-hidden="true"` and **no** tabindex — otherwise every plot is two tab
  stops.
- Leaflet's own container gets `tabindex="0"` from `keyboard: true` (arrow-key panning). Keep it;
  it is the map region's own focus stop and is desirable.

**Info card — `UPopover`, never `UTooltip` (AC-A11Y-5, WCAG 1.4.13).** A tooltip is
non-interactive: the pointer cannot travel into it and it cannot hold the "Ver lote" action.
- One `UPopover` instance for the whole map, `:open` controlled, anchored via the **`#anchor`
  slot** — an absolutely-positioned zero-size `<div>` moved to `map.latLngToContainerPoint(centroid)`
  whenever the active plot changes. (Reka's `PopoverTrigger` is a `<button>`; there is no way to
  make an SVG path the trigger, and Nuxt UI's `reference` prop is not honoured by
  `PopoverTrigger`. The `#anchor` slot sets `hasCustomAnchor` and is the supported path.)
- **Suppress the content autofocus** — Reka focuses the popover content on open, which would
  steal focus from the plot path and break "Escape dismisses it without moving focus". Pass it
  through the `content` prop, which `UPopover` `v-bind`s onto `PopoverContent`:
  `:content="{ onOpenAutoFocus: (event) => event.preventDefault(), side: 'top' }"`.
- Opens on **hover and focus**, closes on `mouseleave`/`blur` with a ~150 ms delay that the card
  itself cancels on `mouseenter` — this is the "hoverable" half of 1.4.13.
- `Escape` closes it and leaves focus on the path (`event.stopPropagation()`, do not blur).
- Card content: plot name, description or `dashboard.plots.noDescription` (AC5), sensor count as
  text, and a `ULink` "Ver lote" (`dashboard.plots.viewPlot`) to the detail page.
- *Escape hatch:* if `UPopover` fights the anchor positioning, a hand-rolled absolutely
  positioned `<div role="dialog">` with the same open/close/`aria-describedby` behaviour is
  acceptable — but report it, because the spec chose `UPopover` deliberately.

**Touch (AC7, AC-A11Y-4).** The first tap opens the card and does **not** navigate. Track the
pointer type on `pointerdown` (`event.pointerType === 'touch'`) and, in the `click` handler,
return early when the last pointer was touch — the card's "Ver lote" link is then the navigation
path. Mouse click and Enter/Space still navigate in one action. No drag, long-press or
multi-point gesture anywhere.

**Basemaps + attribution (AC10, AC-A11Y-14).** Two `L.tileLayer`s, each declaring its own
`attribution`, so Leaflet's attribution control updates itself when they swap:
- street (muted): CARTO Positron —
  `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png`,
  attribution `© OpenStreetMap contributors © CARTO`
- satellite: Esri World Imagery —
  `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`,
  attribution `Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community`

Attribution is a **licensing requirement, not a nicety** — never hide `.leaflet-control-attribution`.
Note the dashboard layout forces `colorMode.preference = 'dark'`; Positron is a light basemap and
is the better choice for polygon contrast — verify the surrounding dark chrome does not make it
look like a bug, and switch to CARTO Voyager if it does.

The selector is a `URadioGroup` (`orientation="horizontal"`, legend = `dashboard.map.basemap`)
rendered in the **section header, outside the `.leaflet-container`** — that keeps it trivially
keyboard-operable and stops Leaflet swallowing its events. A radiogroup exposes the current
basemap via `aria-checked`, which is exactly AC-A11Y-14's "programmatically exposed". Switching
must **not** remove the vector layers (they live in their own panes, so `removeLayer(tileLayer)`
cannot touch them — assert this in E2E).

**Fit / refit (AC1, AC3, AC9, AC23).** One `fitTarget()` function, called on mount and on every
farm change:
1. boundary present → `map.fitBounds(boundaryLayer.getBounds(), { padding: [24, 24] })`
2. else any plot geometry → `map.fitBounds(plotsLayer.getBounds(), { padding: [24, 24] })`
3. else `farm.location` present → `map.setView([coordinates[1], coordinates[0]], 14)`
4. else → do not create a map at all; render `dashboard.map.noLocation` as a `UEmpty` (AC9's
   second branch — an explicit empty state, never a grey world map)

Honour `prefers-reduced-motion` by passing `{ animate: false }` when it is set.

**Unmapped plots note (AC8, AC-A11Y-13).** Below the map, when any plot has
`geometry === null`: a visible `<p>` with `dashboard.map.unmapped` (pluralised) followed by a
`ULink` per unmapped plot, named by the plot, pointing at its detail page. This is what stops a
plot being reachable only to sighted users of the map.

**Region + text alternative (AC-A11Y-6).** Wrap the Leaflet container in
`<section role="region" :aria-label="t('dashboard.map.region', { name: farm.name })"
:aria-describedby="alternativeId">` and render `dashboard.map.alternative` as visible text
inside it.

### 2.4 The list view

`frontend/layers/dashboard/app/components/dashboard/PlotsList.vue`
- `<UPageList divide :aria-label="t('dashboard.plots.listLabel')">` — `UPageList` renders
  `role="list"`; each row is wrapped in a `<div role="listitem">` so the item count is announced
  (AC-A11Y-8). `UPageList` alone does not give you list items.
- Each row is **one** `<ULink :to="localePath(\`/dashboard/plots/${plot.id}\`)" :aria-label="plot.name">`
  — `aria-label` is what keeps the accessible name **"&lt;plot name&gt;"** while the row still
  *shows* description, area and sensor count. Without it, the link's name would be the whole
  concatenated row. (Same technique as the `aria-hidden` avatar in `DropDownUser.vue`.)
- Row content: **name** (medium weight) · **description** or `dashboard.plots.noDescription` ·
  **area in hectares** via `dashboard.plots.area` with
  `new Intl.NumberFormat(locale.value, { maximumFractionDigits: 2 }).format(Number(plot.area_hectares))`
  (remember `area_hectares` is a **string**; `null` renders `—`) · **sensor count at the far end**
  (`ms-auto`) as a `UBadge variant="subtle"` with `i-lucide-radio-tower` and the **text**
  `dashboard.plots.sensors` — never the icon alone.
- Padding must keep every row's target ≥24×24 px; at `< sm` the row wraps to two lines
  (name + description, then area + sensors) with **no horizontal scroll**.
- `UTable` was rejected: 4 fields, one navigation target per row, and TanStack's machinery buys
  nothing while costing the simple keyboard path.

### 2.5 Stat cards

`frontend/layers/dashboard/app/components/dashboard/FarmStatCards.vue` (the `UPageGrid` + the two
count cards) and `WeatherStatCard.vue` (one weather tile, used twice).

- Four tiles: **plots**, **active sensors**, **air temperature**, **solar radiation**. Each shows
  a visible text **label** and, for weather, the **unit verbatim from the response** — the
  frontend never hardcodes `°C` or `W/m²` (AC18, AC-A11Y-9).
- Counts come from the plots response; a plots error affects only those two tiles, a weather
  error only the other two (AC26).
- `WeatherStatCard` states: pending → `USkeleton` + `aria-busy="true"`; error →
  `dashboard.stats.error` + Retry inside `role="alert"`; **key absent** →
  `dashboard.stats.noData` as text (AC19 — never `0`, never an invented value, never a broken
  card); present → value + unit + `dashboard.stats.updated` with the age (AC20), plus a
  `UBadge variant="subtle"` reading `dashboard.stats.stale` when
  `Date.now() - Date.parse(recorded_at) > 30 * 60 * 1000` (AC21).
- **The age must stay truthful while the page sits open.** A `now` ref ticking on a 30 s
  `setInterval`, created under `import.meta.client` and cleared in `onScopeDispose`, feeds both
  the age string and the staleness boolean — they are derived from the *same* value, so they can
  never disagree. The backend sends **no `is_stale` flag**: staleness is a frontend constant
  (`WEATHER_STALE_AFTER_MINUTES = 30` in `layers/dashboard/app/constants/weather.ts`).
- Age formatting: add `formatRelativeTime(iso: string, locale: string, now: number): string` to
  `frontend/layers/common/app/utils/date.ts` next to the existing `formatMonthYear`, using
  `Intl.RelativeTimeFormat` with the active locale. It is generic and cross-domain, so `common`
  is the right home. Never a hardcoded locale.
- `recorded_at` is **parsed** (`Date.parse`) — never string-compared or sliced.
- Badges use `variant="subtle"`, not solid `color="warning"`: the app already has a known
  contrast failure from white-on-solid-primary (`e2e/frontend/a11y.spec.ts`'s
  `LOGIN_SUBMIT_KNOWN_CONTRAST`), and solid badges in the forced dark mode would reproduce it
  against AC-A11Y-9.

### 2.6 View mode: `?view=map|list`

`frontend/layers/dashboard/app/utils/view-mode.ts` — a direct copy of the shape of
`frontend/layers/farm/app/utils/selected-farm.ts`: `const VIEW_MODE_KEY = 'dashboardViewMode'`,
`getStoredViewMode(): ViewMode | null` and `setStoredViewMode(mode): void`, both guarded with
`if (!import.meta.client) return null / return` (pages and middleware run server-side on direct
loads), and the stored string validated against the two literals before being trusted.

`frontend/layers/dashboard/app/composables/useDashboardViewMode.ts`:
```
const initial = parseViewMode(route.query.view) ?? getStoredViewMode() ?? 'map'
onMounted(() => { if (!parseViewMode(route.query.view)) router.replace({ query: { ...route.query, view: initial } }) })
const mode = computed(() => parseViewMode(route.query.view) ?? initial)
const setMode = (next: ViewMode) => { setStoredViewMode(next); void router.push({ query: { ...route.query, view: next } }) }
```
- The URL is the **source of truth** (AC14: `?view=list` and `?view=map` both work on load).
- `localStorage` is a **fallback only when the query param is absent** (AC16), and a first-ever
  visit with neither is **map** (AC17).
- The `router.replace` on mount is what makes **Back** work (AC15): without it, going back to the
  paramless `/dashboard` entry would re-read `localStorage` — which now holds the *new* mode —
  and stay put. `replace` (not `push`) so it adds no history entry of its own.
- All functions in the composable are arrow functions (`frontend/CLAUDE.md`).
- If Nuxt does not auto-import it, mirror the farm layer and add
  `imports: { dirs: [fileURLToPath(new URL('./app/composables', import.meta.url))] }` to
  `layers/dashboard/nuxt.config.ts` — resolve to an **absolute** path; relative paths are not
  layer-relative.

### 2.7 `/dashboard/plots/[id]`

`frontend/layers/dashboard/app/pages/dashboard/plots/[id].vue` — deliberate placeholder.
- `definePageMeta({ middleware: ['auth'], layout: 'dashboard' })` (AC30: the auth middleware
  already redirects through `useLocalePath()`, so the `/en` prefix survives).
- `const plotId = computed(() => { const parsed = Number(route.params.id); return Number.isInteger(parsed) ? parsed : null })`
  — a non-numeric id resolves to `null`, the query stays disabled, and the not-found state renders
  without a request.
- `usePlotQuery(plotId)` — direct load, refresh and bookmark all work because the endpoint takes
  the plot id alone (AC28); nothing depends on a warm plots cache.
- **Not found (AC29):** `isError && (error.status === 404)` → render an in-page `UEmpty` with
  `dashboard.plotDetail.notFound` + `notFoundBody` + the back link, `<h1>` = `notFound`,
  document title = `notFound`. Do **not** call `showError`/`createError` — that swaps in
  `app/error.vue` and loses the dashboard layout. **No plot data is rendered in this state.**
- **Found (AC27, AC-A11Y-11):** a single `<h1>` = `dashboard.plotDetail.title` with the plot
  name, `useHead(() => ({ title: … }))` matching it, and the record inside
  `<pre tabindex="0" role="region" :aria-label="t('dashboard.plotDetail.dump')" class="overflow-auto max-h-96"><code>{{ JSON.stringify(plot, null, 2) }}</code></pre>`
  — `tabindex="0"` is what makes the scrollable region keyboard-scrollable.
- **Back link:** `<ULink :to="localePath({ path: '/dashboard', query: { view: getStoredViewMode() ?? 'map' } })">`
  with `dashboard.plotDetail.back` — "returns to the previous view mode".
- **Farm reconciliation:** `watch(plot, (value) => { if (value && value.farm.id !== selectedFarm.value?.id) selectFarm(value.farm.id) })`
  — a direct load of a plot belonging to a non-selected farm must leave the sidebar coherent.
  This is why the contract exposes `farm: {id, name}` on the detail response.
- Pending → skeleton with `aria-busy="true"`; non-404 error → text + Retry.

### 2.8 Deletions and other edits

- **Delete `frontend/layers/dashboard/app/components/dashboard/FarmStats.vue`.** It is
  unreferenced (zero imports in `frontend/` or `e2e/`), its four values are `Math.random()`
  output, its strings are hardcoded Spanish, and two of its cards (relative humidity, soil pH)
  have **no possible backend source** — there is no `soil_ph` semantic key. Harvest its `:ui`
  treatment into `FarmStatCards.vue`, then delete the file. Leaving it invites someone to ship
  fake data.
- `frontend/layers/dashboard/i18n/locales/{es,en}.json` — add the `dashboard.view.*`,
  `dashboard.stats.*`, `dashboard.map.*`, `dashboard.plots.*`, `dashboard.plotDetail.*` keys from
  §0.2. Escape a literal `@` as `{'@'}` in message strings (a bare `@` crashes SSR with "Invalid
  linked format") — relevant if any copy grows an email address.
- `dashboard.index.welcome` ("Muy pronto encontrarás aquí…") is now false — delete the key and
  its usage.
- No change to `frontend/nuxt.config.ts` — **especially not** to `css: []`.
- `@vue-leaflet/vue-leaflet` stays unused. This plan uses raw Leaflet because the casing pairs,
  the per-path ARIA attributes and the popover anchoring all need direct layer/element access
  that the wrapper hides. Flag the dependency to the orchestrator as removable — do **not**
  remove it in this feature.

### 2.9 Vitest — **this does not exist yet**

`frontend/package.json` has **no vitest, no @nuxt/test-utils, no test script**, and there is not a
single `*.test.ts`/`*.spec.ts` under `frontend/`. The root `CLAUDE.md` names "Django +
Vitest/Playwright" as the rule, but the Vitest half has never been set up. This is a genuine gap
in the spec, not an oversight in this plan.

**Recommended (confirm with the user before spending the time):** stand up a minimal Vitest
setup as part of this feature —
`npm install -D vitest @nuxt/test-utils happy-dom @vue/test-utils`, a `vitest.config.ts` using
`defineVitestConfig` from `@nuxt/test-utils/config`, and `"test": "vitest run"` /
`"test:watch": "vitest"` in `frontend/package.json` — and cover only the **pure logic**, where
unit tests are cheapest and Playwright is most expensive:
- `layers/dashboard/app/utils/view-mode.ts` — parse/validate/round-trip, and the
  `import.meta.client` guard returning `null` on the server
- `useDashboardViewMode` resolution order — query > storage > `'map'` (AC14/16/17 at unit speed)
- `formatRelativeTime` + the 30-minute staleness boundary — assert at 29 min, 30 min and 31 min
  (AC20/AC21 edges, which are painful to hit through the browser)
- the GeoJSON → `FeatureCollection` builder — that `[lng, lat]` is passed through **unswapped**,
  and that a `geometry: null` plot is excluded from the collection but present in the "unmapped"
  list (AC8)
- `WeatherStatCard` rendering: absent key → "Sin datos" and **no** `0` in the DOM (AC19)

**Fallback if the user declines:** every item above is already covered by an E2E assertion in §3;
the loss is speed and edge-case precision, not coverage. Say so explicitly rather than silently
skipping tests.

### 2.10 Frontend risks

| Risk | Mitigation |
| --- | --- |
| Leaflet CSS leaks into the shared entry — the landing page pays for a map it does not have | CSS imported inside `PlotsMap.client.vue` only; post-build grep of the entry CSS is a required check |
| `:unmount-on-hide="false"` leaves the hidden map with stale dimensions → grey tiles after a tab switch | `map.invalidateSize()` when the map panel becomes visible |
| `UPopover` autofocuses its content and steals focus from the plot path | `:content="{ onOpenAutoFocus: (e) => e.preventDefault() }"`; documented escape hatch |
| `[lng, lat]` / `[lat, lng]` swap — fails silently, plots land in the Indian Ocean | Everything through `L.geoJSON`; exactly one commented manual swap for `setView` |
| Leaflet's own controls (attribution links, zoom buttons) trip axe on `/dashboard` | Fix by relabelling first; only exclude with a `KNOWN_*` comment, following the existing `LOGIN_SUBMIT_KNOWN_CONTRAST` precedent |
| Solid badges in the forced dark mode reproduce the known white-on-primary contrast failure | `variant="subtle"` everywhere |
| Adding files under `app/composables`/`app/utils` breaks the running dev server silently | Restart `npm run dev` after creating them |
| CARTO/Esri free tiles have usage policies and can rate-limit | Attribution always visible; note for a future production review; E2E stubs the tiles entirely |

---

## 3. E2E

Runner: Playwright from `e2e/`, `npm test`. `workers: 1`, `fullyParallel: false` — the specs
share one backend user, so files must not race. The `frontend` project pins `locale: 'es-CO'`.

### 3.1 Which files change

| File | Change |
| --- | --- |
| `e2e/frontend/helpers.ts` | Extend `T` with every new Spanish string from §0.2 and `T_EN` with the English ones the i18n assertions need. **`T.plotCount` must change** — the page no longer renders `"2 lotes"`. |
| `e2e/frontend/dashboard.spec.ts` | The bulk of the new coverage: map, list, toggle, view-mode persistence, stat cards, plot detail. The pages live in the **`dashboard`** layer, so this is the layer-matching file. |
| `e2e/frontend/farm.spec.ts` | **Will break and must be updated.** It asserts `page.getByText(T.plotCount, { exact: true })` in four tests; that string is gone. Re-point those assertions at the plot-count stat card, and extend the farm-switch test to prove the map refits and the weather refetches (AC23). The spec named only `dashboard.spec.ts` and `a11y.spec.ts` — this third file is a real, unavoidable edit. |
| `e2e/frontend/a11y.spec.ts` | Add scans for both view modes, both basemaps, `/en/dashboard`, and `/dashboard/plots/<id>`. |
| `e2e/README.md` | Document `make seed-weather` and the tile-stubbing convention. |

**New spec file: none.** The rule is one spec per **frontend layer name**; every new page and
component lives in the `dashboard` layer, so `dashboard.spec.ts` is the correct home and simply
grows. Creating `plots.spec.ts` or `map.spec.ts` would break the layer-name convention.

### 3.2 Conventions that are not optional

- Reuse `loginAs(page)` (logs in through the real form as the seeded user) and
  `gotoHydrated(page, path)` (navigates and waits for hydration — interacting with a form before
  hydration triggers a native full-page submit). Never re-implement either.
- **Every UI string a spec selects by lives in the exported `T` map**, never inline. `T` is the
  locale seam: if the default UI language changes, only `T` changes, never spec logic. Form
  inputs are selected by `type` attribute so translated labels do not break them.
- `UDropdownMenu` overlays aria-hide the rest of the page while open — press `Escape` before
  locating anything in the background (already encoded in `farm.spec.ts`'s `selectFarm` helper;
  reuse it).
- After editing frontend code, warm the dev server (load one page) before running the suite —
  cold Vite compile swallows pre-hydration clicks.

### 3.3 How the map is actually tested

Leaflet's default renderer is **SVG**, not canvas — every plot is a real `<path>` in the DOM. The
suite therefore never screenshots and never samples pixels. It asserts against:

1. **The region**: `page.getByRole('region', { name: T.mapRegion })` (the `aria-label` is
   `"Mapa de la finca, Finca El Tesoro"`).
2. **The shapes**: `page.locator('path[data-role="plot"]')` — count equals the number of seeded
   plots **with** geometry (2 for Finca El Tesoro, since plot 29 has none); each has a
   `data-plot-id`. `path[data-role="boundary"]` present for farm 1, **absent** for farm 2 (AC3).
   The casing pair is proved by `path[data-role="plot-casing"]` having the same count — that is
   the automatable half of AC-A11Y-7.
3. **The accessible name**: `page.getByRole('link', { name: /Lote La Colina/ })` resolves to the
   path — role-based, so it survives class and markup churn.
4. **Keyboard**: `.focus()` the path, `page.keyboard.press('Enter')`, then
   `await expect(page).toHaveURL(/\/dashboard\/plots\/\d+$/)` (AC6, AC-A11Y-4).
5. **The popover**: focus a path → the card is visible with the plot name, description and
   "Ver lote"; move the mouse from the path onto the card and assert it is **still** visible
   (WCAG 1.4.13 "hoverable", AC-A11Y-5); `Escape` closes it and
   `page.evaluate(() => document.activeElement?.getAttribute('data-plot-id'))` still returns the
   plot id (focus did not move).
6. **Attribution**: `.leaflet-control-attribution` contains `OpenStreetMap` on street and `Esri`
   on satellite (AC10) — and after switching, `path[data-role="plot"]` is still present, proving
   the vector layers survived the basemap swap.
7. **Tiles are stubbed**, always:
   `page.route('**basemaps.cartocdn.com/**', fulfil 1×1 PNG)` and
   `page.route('**server.arcgisonline.com/**', fulfil 1×1 PNG)` in a `beforeEach`. Hitting real
   tile CDNs from CI is slow, flaky and rude. Nothing in the suite depends on tile *content*.

### 3.4 The a11y backstop must cover both modes and both basemaps

`a11y.spec.ts` keeps its existing `severeViolations(page, exclude?)` helper and `WCAG_TAGS`. Add:
- `/dashboard?view=map` (es) — after the login toast has expired, so the scan sees steady state
- `/dashboard?view=list` (es)
- `/dashboard?view=map` with the **satellite** basemap selected (AC-A11Y-7's automatable half:
  axe re-runs its non-text and text contrast rules over the changed background)
- `/en/dashboard?view=map` and `/en/dashboard?view=list`
- `/dashboard/plots/<id>` and `/en/dashboard/plots/<id>`

Wait for the map to have painted (`await expect(page.locator('path[data-role="plot"]').first()).toBeVisible()`)
before scanning, or axe races the async chunk. If Leaflet's own controls produce violations,
prefer fixing them in the frontend; if one must be excluded, follow the existing
`LOGIN_SUBMIT_KNOWN_CONTRAST` precedent — a named constant with a comment saying **why** and
**when it can be removed**.

### 3.5 Not dependent on seed freshness

AC20 (age shown) and AC21 (stale badge) must **not** depend on when `make seed-weather` last ran.
Both are asserted with a route interception that returns synthetic timestamps:
`page.route('**/farm/farms/*/weather/', …)` fulfilling
`{ air_temperature: { value: 27.4, unit: '°C', recorded_at: <now - 2 min> }, solar_radiation: { … recorded_at: <now - 95 min> } }`.
The same technique covers AC19 (`{}` → "Sin datos"), AC24 (`farms/` → `[]`), AC26 (abort weather
only and assert the map, list and count cards still render) and AC9's null-`location` branch. The
fixtures exist for the **demo and the dev experience**; the assertions own their own data.

---

## 4. AC coverage

Legend — **BE** Django test (`make test`), **FE‑E2E** Playwright, **VT** Vitest (§2.9),
**MAN** manual QA (documented procedure, cannot be automated).

| AC | Area | Proof |
| --- | --- | --- |
| AC1 map fitted, plots drawn | FE | FE‑E2E `dashboard.spec.ts`: `path[data-role="plot"]` count == plots with geometry; map region visible |
| AC2 boundary distinct | FE | FE‑E2E: `path[data-role="boundary"]` present on farm 1 and carries `stroke-dasharray` |
| AC3 no boundary → fit to plots, no error | FE | FE‑E2E: switch to *Finca San Vicente* (fixture boundary `null`) → no boundary path, plots still drawn, no error text |
| AC4 hover/focus info card (name + description) | FE | FE‑E2E: `.hover()` and `.focus()` each open the card with both fields |
| AC5 "sin descripción" | FE | FE‑E2E on plot 29 (`description: ""`) + VT on the card component |
| AC6 click / Enter / "Ver lote" → detail | FE | FE‑E2E: three separate assertions, all landing on `/dashboard/plots/<id>` |
| AC7 first tap opens card, does not navigate | FE | FE‑E2E in a `test.use({ hasTouch: true })` block: `page.tap()` → card visible, URL unchanged |
| AC8 unmapped note with links | FE | FE‑E2E: "1 lote no se muestra en el mapa" + a link named `Lote Sin Mapear` (fixture plot 29) |
| AC9 no geometries → centre on location; null location → empty state | FE | FE‑E2E: route-intercept plots with all-null geometry (map still renders), then intercept farms with `location: null` → `dashboard.map.noLocation` |
| AC10 basemap switch + attribution | FE | FE‑E2E: attribution text changes, shapes persist |
| AC11 list row fields | FE | FE‑E2E: row shows name, description, `ha`, sensor count |
| AC12 row → detail | FE | FE‑E2E: click a row → detail URL |
| AC13 empty state (no plots) | FE | FE‑E2E: select *Finca Sin Lotes* (fixture farm 13) → `farm.plots.none` in **both** panels |
| AC14 `?view=list` / `?view=map` deep link | FE | FE‑E2E: `gotoHydrated('/dashboard?view=list')` → list tab selected; + VT on the composable |
| AC15 toggle updates the query param, Back restores | FE | FE‑E2E: click List → URL has `view=list`; `goBack()` → map active |
| AC16 restore from `localStorage` | FE | FE‑E2E: choose list, `goto('/dashboard')` → list; + VT |
| AC17 first visit = map | FE | FE‑E2E in a **fresh** browser context (no storage) → map; + VT |
| AC18 four cards with labels + units | FE | FE‑E2E: four labels, two counts, unit text from the response |
| AC19 "sin datos" when a key is absent | FE | FE‑E2E: weather intercepted as `{}` → "Sin datos", **no `0`**; counts still render. Also demoable on farm 2 (no `solar_radiation` config) |
| AC20 age shown | FE | FE‑E2E with a synthetic `recorded_at = now − 2 min`; + VT on `formatRelativeTime` |
| AC21 "desactualizada" past 30 min | FE | FE‑E2E with `recorded_at = now − 95 min`; + VT at the 29/30/31-minute edges |
| AC22 most recent across active stations | BE | BE `FarmWeatherTests`: two active stations, newer wins; equal timestamps → higher station id; inactive station ignored |
| AC23 farm switch refits + refetches everything | FE | FE‑E2E `farm.spec.ts`: distinct `plots/` **and** `weather/` request URLs observed after switching; stat cards change |
| AC24 no farms at all | FE | FE‑E2E: `farms/` intercepted as `[]` → existing no-farm state, no map, no error |
| AC25 plots error + Retry | FE | FE‑E2E: abort `plots/` → error text + Retry, unroute, Retry succeeds (extends the existing `farm.spec.ts` test) |
| AC26 weather error is isolated | FE | FE‑E2E: abort **only** `weather/` → weather cards show error + Retry, map/list/count cards still render |
| AC27 detail renders a `<code>` dump in the dashboard layout with a back link | FE | FE‑E2E: `<pre><code>` contains the plot name, sidebar present, back link present |
| AC28 direct load / refresh / bookmark | FE | FE‑E2E: `gotoHydrated('/dashboard/plots/<id>')` cold, then `page.reload()` |
| AC29 another farmer's plot / unknown id → not found, no data | BE + FE | BE `PlotDetailTests` (404, plot name absent from the body) + FE‑E2E not-found state |
| AC30 unauthenticated → login with locale prefix | FE | FE‑E2E: `/en/dashboard/plots/1` without tokens → `/en/login` |
| AC31 plots response fields | BE | BE `PlotListSerializationTests` |
| AC32 active-only + constant query count | BE | BE `PlotSensorCountTests` — `assertNumQueries` with the **same** N for 2 plots and 12 plots (the N+1 gate) |
| AC33 404 on all four endpoints for a non-owned farm/plot | BE | BE tests on farms, plots, plot-detail and weather |
| AC34 English mirrors | FE | FE‑E2E: `/en/dashboard` and `/en/dashboard/plots/<id>` assert `T_EN` strings; no Spanish leaks |
| AC‑A11Y‑1 axe, zero serious/critical | FE | FE‑E2E `a11y.spec.ts`: 7 scans (§3.4) |
| AC‑A11Y‑2 tablist semantics + arrows | FE | FE‑E2E: `role="tablist"`, two `role="tab"`, `aria-selected`, Left/Right, Enter/Space |
| AC‑A11Y‑3 focusable shapes, list order, accessible name | FE | FE‑E2E: repeated `Tab` collects `data-plot-id`s in the list's order; `getByRole('link', { name: … })` matches the `"<name>, <description>, <n> sensores"` shape. **Focus-indicator ≥3:1 is MAN** |
| AC‑A11Y‑4 Enter/Space, single tap, single click, no gestures | FE | FE‑E2E (three input modes) |
| AC‑A11Y‑5 hover **and** focus, `aria-describedby`, hoverable, Escape keeps focus | FE | FE‑E2E (§3.3 item 5) |
| AC‑A11Y‑6 labelled region, text alternative, toggle precedes map | FE | FE‑E2E: `getByRole('region', { name })`; DOM order asserted with `evaluateAll` comparing `compareDocumentPosition` of the tablist and the map region |
| AC‑A11Y‑7 greyscale, both basemaps, ≥3:1 outlines | FE | **MAN** — the definitive check. Automatable proxies: casing paths present, boundary `stroke-dasharray` differs from plots, permanent name labels present, and the satellite axe scan |
| AC‑A11Y‑8 row link name, sensor text, ≥24 px, list count | FE | FE‑E2E: `getByRole('link', { name: 'Lote La Colina', exact: true })`; `getByRole('list')` → `getByRole('listitem')` count; `boundingBox()` height ≥ 24 |
| AC‑A11Y‑9 label + unit, no colour-only state, dark-mode contrast | FE | FE‑E2E text assertions (badge text present) + axe `color-contrast` inside AC‑A11Y‑1 |
| AC‑A11Y‑10 `aria-busy` while pending, live-region error + Retry | FE | FE‑E2E: `[aria-busy="true"]` during a delayed response; `role="alert"` contains the error and a button named `Reintentar` |
| AC‑A11Y‑11 title + single `<h1>`, labelled scrollable `<pre>`, back link | FE | FE‑E2E: `toHaveTitle`, one `h1`, `getByRole('region', { name: 'Datos del lote' })` with `tabindex="0"`, back link returns to the stored mode |
| AC‑A11Y‑12 320 px and 200 % zoom reflow | FE | FE‑E2E: `setViewportSize({ width: 320, height: 800 })` → `scrollWidth <= clientWidth`; repeat at 1280 px with `deviceScaleFactor`-equivalent zoom |
| AC‑A11Y‑13 geometry-less plot still reachable | FE | FE‑E2E — same assertion as AC8 |
| AC‑A11Y‑14 basemap selector keyboard + exposed state | FE | FE‑E2E: `getByRole('radiogroup', { name: 'Mapa base' })`, arrow keys move, `aria-checked` tracks |

**Cannot be automated (verified manually, recorded in `qa.md`):**
1. **AC‑A11Y‑7** — greyscale legibility and ≥3:1 outline contrast over *photographic* satellite
   imagery. Procedure: open `/dashboard?view=map`, switch to satellite, apply a browser
   greyscale filter (DevTools → Rendering → Emulate vision deficiencies → Achromatopsia), confirm
   every plot is identifiable by its **name label**, the boundary is distinguishable by its
   **dash pattern**, and sample the casing/core stroke pair against three different tile regions
   (dark canopy, bright field, water) with a contrast picker. Repeat on street.
2. **AC‑A11Y‑3, focus-indicator contrast** — same procedure, focusing a plot and sampling the
   indicator against its own fill and against the tiles.
3. **The Wagtail `Farm.boundary` panel** (§1.1) — that the polygon drawing tools and the
   `wagtailgeowidget` point picker both initialise and save on the same admin form.

---

## 5. Ordering, parallelism, and the two points of agreement

**Backend and frontend are dispatched in parallel and share only `contract.md`.**

**Backend needs nothing from the frontend.** `contract.md` fully specifies its output. Suggested
internal order: migration + panel → `with_sensor_count` → serializers → the two new views →
fixtures + seed command → tests. Fixtures can be written before or after the views; the tests
depend on neither (they build their own data with `setUpTestData`).

**Frontend needs nothing from the backend to start**, but the risk profile favours this order:
1. types + `farmApi` + query keys + the two composables (contract only)
2. stat cards (hand-mocked data)
3. list view + view-mode composable + `[id].vue` — everything valuable that needs no map
4. the map last: it is the largest single risk and the only piece that genuinely benefits from
   real geometry on the wire

That order is also the sequencing advice the BA discovery gave: *list + cards + detail* is most
of the daily value and lands without a new frontend dependency; the map is the differentiator and
still ships.

**The two things they must agree on that the contract does not cover:**
1. **The seed data** (§0.1). The frontend's and E2E's negative-path assertions — farm 2's null
   boundary, plot 29's null geometry and empty description, farm 13's zero plots, farm 2's
   missing `solar_radiation`, farm 1's two active stations — are only true if the backend writes
   the fixtures exactly as §0.1 specifies. **This section is the agreement**; neither side should
   invent its own seed.
2. **The Spanish copy** (§0.2). E2E selects by it and cannot be written until the strings are
   fixed. **§0.2 is the agreement**; the frontend must ship those exact `es` values so E2E can be
   drafted in parallel rather than after.

**E2E is written third**, but its `T` additions and spec skeletons can be drafted from §0.2 and
§0.1 while the other two areas are in flight. E2E's only hard blocker is a running stack with the
new fixtures loaded.

**Non-negotiable sequencing inside backend:** `make migrations` → `make migrate` → `make loaddata`
(the fixture references `boundary`, which does not exist before the migration).

---

## 6. Files touched, by area

**Backend**
```
backend/farm/models.py                                       (Farm.boundary, PlotQuerySet)
backend/farm/forms.py                                        (FarmAdminForm)
backend/farm/wagtail_hooks.py                                (WagtailFarmAdmin.get_form_class)
backend/farm/serializers.py                                  (to_geojson, Farm/Plot/PlotDetail)
backend/farm/api.py                                          (PlotDetailAPIView, FarmWeatherAPIView)
backend/farm/urls.py                                         (2 routes)
backend/farm/tests.py                                        (2 updated + 4 new test classes)
backend/farm/migrations/0004_farm_boundary.py                NEW (generated)
backend/farm/fixtures/initial_farms_with_plots.json          (boundaries, plot 29, farm 13)
backend/sensors/fixtures/initial_sensors.json                NEW
backend/sensors/management/__init__.py                       NEW
backend/sensors/management/commands/__init__.py              NEW
backend/sensors/management/commands/seed_weather_readings.py NEW
Makefile                                                     (loaddata, seed-weather)
backend/makefile                                             (loaddata, seed-weather)
```

**Frontend**
```
frontend/layers/farm/app/types/farm.ts                                    (extended)
frontend/layers/farm/app/utils/api/farm.ts                                (getPlot, getWeather)
frontend/layers/farm/app/constants/query-keys.ts                          (PLOT, WEATHER)
frontend/layers/farm/app/composables/usePlotQuery.ts                      NEW
frontend/layers/farm/app/composables/useFarmWeatherQuery.ts               NEW
frontend/layers/dashboard/app/pages/dashboard/index.vue                   (rewritten body)
frontend/layers/dashboard/app/pages/dashboard/plots/[id].vue              NEW
frontend/layers/dashboard/app/components/dashboard/FarmStatCards.vue      NEW
frontend/layers/dashboard/app/components/dashboard/WeatherStatCard.vue    NEW
frontend/layers/dashboard/app/components/dashboard/PlotsMap.client.vue    NEW
frontend/layers/dashboard/app/components/dashboard/PlotsList.vue          NEW
frontend/layers/dashboard/app/components/dashboard/PlotInfoCard.vue       NEW
frontend/layers/dashboard/app/composables/useDashboardViewMode.ts         NEW
frontend/layers/dashboard/app/utils/view-mode.ts                          NEW
frontend/layers/dashboard/app/constants/map.ts                            NEW
frontend/layers/dashboard/app/constants/weather.ts                        NEW
frontend/layers/dashboard/app/components/dashboard/FarmStats.vue          DELETED
frontend/layers/dashboard/i18n/locales/{es,en}.json                       (new keys)
frontend/layers/dashboard/nuxt.config.ts                                  (imports.dirs, if needed)
frontend/layers/common/app/utils/date.ts                                  (formatRelativeTime)
frontend/package.json + vitest.config.ts                                  NEW, if §2.9 is approved
```

**E2E**
```
e2e/frontend/helpers.ts        (T, T_EN)
e2e/frontend/dashboard.spec.ts (bulk of new coverage)
e2e/frontend/farm.spec.ts      (breaking update + AC23)
e2e/frontend/a11y.spec.ts      (both modes, both basemaps, new route)
e2e/README.md                  (make seed-weather, tile stubbing)
```

---

## 7. Where I believe the spec is incomplete

Raised for the orchestrator to put to the user; none of them change the agreed scope.

1. **Vitest does not exist.** `frontend/package.json` has no test runner and there is not one
   frontend unit test in the repo, yet the root `CLAUDE.md` and this feature's brief both assume
   "Vitest coverage". Standing it up is real, unbudgeted work (§2.9). Approve it, or accept
   E2E-only coverage explicitly.
2. **`e2e/frontend/farm.spec.ts` will break.** The spec names only `dashboard.spec.ts` and
   `a11y.spec.ts`, but four assertions in `farm.spec.ts` select the string `"2 lotes"`, which
   this feature removes from the page.
3. **The fixtures as described cover only the happy path.** The spec says to seed stations,
   variables, snapshots, measurements and sensors — it never says the seed must also contain the
   *negative* cases (a farm with no boundary, a plot with no geometry, a farm with no plots, a
   station missing a variable, a stale reading). Without them AC3, AC8, AC9, AC13, AC19, AC21 and
   AC‑A11Y‑13 have nothing to run against. §0.1 adds them.
4. **AC‑A11Y‑7 has no automatable gate.** Greyscale legibility and ≥3:1 outline contrast over
   photographic imagery cannot be asserted by axe or Playwright. It is listed as a criterion with
   no stated verification method; §4 supplies a manual procedure and automatable proxies.
5. **The seeded weather goes stale on its own.** A dev who ran `make loaddata` yesterday sees
   "desactualizada" on every card — which looks like a bug in the feature. `make seed-weather`
   fixes it in one command, and E2E is deliberately made independent of seed freshness (§3.5).
6. **`@vue-leaflet/vue-leaflet` is installed and this plan does not use it.** Raw Leaflet is the
   right call here (casing pairs, per-path ARIA, popover anchoring all need direct element
   access), which leaves an unused dependency. Flagging it rather than removing it inside this
   feature.
7. **AC‑A11Y‑9's dark-mode contrast rubs against a known existing failure.** The app already
   carries a documented white-on-solid-primary contrast violation (`LOGIN_SUBMIT_KNOWN_CONTRAST`
   in `a11y.spec.ts`); solid badges on the new cards would reproduce it. The plan mandates
   `variant="subtle"`, but the underlying primary-colour problem is a separate fix the user may
   want scheduled.
