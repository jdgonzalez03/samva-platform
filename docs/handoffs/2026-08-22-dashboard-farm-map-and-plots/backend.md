# backend handoff — dashboard farm map, plot list, stat cards, plot detail

Summary: `Farm.boundary` added and every farm/plot endpoint now serialises hand-built GeoJSON;
plot detail and farm weather are new; the dev seed grows the unhappy-path rows plus a
time-relative weather seeder. A later addition puts **`label_point`** on every plot row.
`make test` is green at **59 tests** (baseline 9).

## Files changed

- `backend/farm/models.py` — `Farm.boundary` + its own Wagtail panel; `PlotQuerySet.with_sensor_count()` (annotation + explicit `.order_by('name')`), `Plot.objects`
- `backend/farm/migrations/0004_farm_boundary.py` — single `AddField`, nullable, no data migration
- `backend/farm/forms.py` — `FarmAdminForm` (django-leaflet polygon drawing widget)
- `backend/farm/wagtail_hooks.py` — `WagtailFarmAdmin.get_form_class()`
- `backend/farm/serializers.py` — `to_geojson()`, `FarmSerializer` (+location/boundary), `FarmSummarySerializer`, `PlotSerializer` (+geometry/centroid/**label_point**/sensor_count), `PlotDetailSerializer(PlotSerializer)`
- `backend/farm/api.py` — `get_owned_or_404()`, `PlotDetailAPIView`, `FarmWeatherAPIView`
- `backend/farm/urls.py` — two new `path()`s
- `backend/farm/tests.py` — 3 existing assertions updated + 8 new classes (incl. `PlotLabelPointTests`, `an_l_shaped_polygon()`)
- `backend/farm/fixtures/initial_farms_with_plots.json` — boundaries, plot 29, farm 13
- `backend/sensors/fixtures/initial_sensors.json` — **new**
- `backend/sensors/management/{__init__.py,commands/__init__.py,commands/seed_weather_readings.py}` — **new**
- `backend/sensors/tests.py` — command tests
- `Makefile` (root) and `backend/makefile` — `loaddata` extended, new `seed-weather` target

## Contract

All per `contract.md`, all `IsAuthenticated`, all under the existing `api/farm/` mount:

| Method + path | Notes |
| --- | --- |
| `GET /api/farm/farms/` | extended: `location`, `boundary` (GeoJSON or `null`), bare array |
| `GET /api/farm/farms/<farm_id>/plots/` | extended: `geometry`, `centroid`, `label_point`, `sensor_count`; `area_hectares` stays a JSON **string** |
| `GET /api/farm/plots/<plot_id>/` | new; single object, the seven shared fields (`label_point` included, by subclassing) + `farm {id,name}`, `created_at`, `updated_at` |
| `GET /api/farm/farms/<farm_id>/weather/` | new; object keyed by `semantic_key`, `value` is a JSON **number**, absent key = no data, `{}` when nothing |

404 body is exactly `{"detail": "Not found."}` on all of them. Django's `get_object_or_404`
puts the model name in that body (`"No Plot matches the given query."`), which would let a
caller tell "exists but not yours" from "does not exist" — `farm/api.py::get_owned_or_404`
raises DRF's `NotFound` instead. The pre-existing plots-list 404 body changed with it.

## Contract deviations

**None as shipped now.** The first pass had one and it is fixed in this pass, recorded here because
a downstream agent may have read the earlier "none": the plots list did **not** honour `contract.md`
§2's ordering guarantee. `annotate()` builds a `GROUP BY` query, and Django does not apply
`Meta.ordering` to those — the annotated queryset came back with no `ORDER BY` at all
(`qs.ordered is False`), and the dev DB really returned `["Lote Sin Mapear", "Lote La Colina",
"Lote El Abrevadero"]`. `PlotQuerySet.with_sensor_count()` now ends in `.order_by('name')`
(query count unchanged), so the list order and the map's tab order match again (AC-A11Y-3).

Every field name, type, nullability, status code and error body matches `contract.md`; ordering now
does too, pinned by `PlotListOrderingTests` (see AC self-check).

## AC self-check

- **AC31 ✓** — `PlotListSerializationTests`: `test_a_mapped_plot_serializes_geometry_centroid_area_and_count`
  (Polygon/Point with `{type, coordinates}` only, closed ring, `area_hectares` as `str`,
  `sensor_count` as `int`), `test_an_unmapped_plot_serializes_nulls_and_a_zero_count`,
  `test_an_unset_description_is_an_empty_string_not_null`,
  `test_coordinates_are_longitude_first` (asserts `lng < 0 < lat` — catches a silent `[lat,lng]` swap).
- **AC32 ✓** — `PlotSensorCountTests.test_sensor_count_ignores_inactive_sensors` (3 active + 2 inactive → `3`)
  and `test_query_count_does_not_grow_with_the_number_of_plots`: **2 queries measured for a
  2-plot farm and 2 for a 12-plot farm** (farm ownership lookup + annotated plot list).
  `PlotDetailTests.test_detail_is_a_single_query`: **1 query**.
  `FarmWeatherTests.test_query_count_does_not_grow_with_the_number_of_stations`: **2 queries with
  1 station and 2 with 3 stations** (ownership lookup + one `DISTINCT ON`). All four numbers are
  **unchanged by `label_point`** — re-verified after adding it.
- **AC-A11Y-3 (backend half) ✓** — `PlotListOrderingTests` creates `Lote Sur`, `Lote Ancla`,
  `Lote Norte` in that order (deliberately not alphabetical, so the test fails if the `ORDER BY`
  is dropped) and asserts the response is `["Lote Ancla", "Lote Norte", "Lote Sur"]`, plus
  `test_the_annotated_queryset_carries_an_explicit_order_by` (`queryset.ordered`,
  `query.order_by == ('name',)`) and `test_the_farm_list_is_ordered_by_name` for the sidebar's
  default-farm pick. Both plot assertions were confirmed red with the `.order_by` removed.
  The frontend does no client-side sorting, so this is the only ordering guarantee.
- **`label_point` (contract §2/§3) ✓** — `PlotLabelPointTests` builds a deliberately **concave**
  L-shaped plot (`an_l_shaped_polygon()`, the classic 7-vertex L) and asserts the returned
  `label_point` is `contains()`-inside the polygon while the returned `centroid` — and the
  bounding-box centre — are **outside**; confirmed red by swapping `point_on_surface` for
  `centroid` (`assertTrue(shape.contains(label_point))` fails). Plus `label_point` is `null`
  exactly when `geometry` is, coordinates are longitude-first, and detail matches the list row.
- **AC33 ✓** — `PlotDetailTests.test_another_farmers_plot_is_404_and_leaks_nothing` (asserts the
  plot name is absent from the body), `FarmWeatherTests.test_another_farmers_farm_is_404`,
  `FarmAPITestCase.test_plot_list_hides_farms_owned_by_someone_else`, plus unknown-id and
  unauthenticated cases on each endpoint.
- **Data prerequisites made possible** (verified by `SeedDataContractTests`, which loads the real
  fixtures and runs the real command): AC2/AC3 (farm 1 boundary set, farm 2 null), AC8/AC-A11Y-13
  (plot 29 `Lote Sin Mapear`, geometry null, description `""`), AC9/AC13 (farm 13 `Finca Sin
  Lotes`, location set, zero plots), AC18/AC11 (`sensor_count` per plot), AC19 (farm 2 configures
  `air_temperature` only → `solar_radiation` absent; farm 13 → `{}`), AC20/AC21 (farm 1 newest
  reading < 30 min, farm 2 > 30 min), AC22 (two active + one inactive station on farm 1).
  AC1/AC10/AC27–AC29 depend on frontend rendering; the data and endpoints are in place.

## Gotchas

- **`make loaddata` resets `juan.perez`'s password to the fixture hash.** The E2E password
  (`E2eSmoke_2026!`) must be re-set afterwards via the manual step in `e2e/README.md`. I ran
  `make loaddata`, so the dev database needs that step now.
- **The seed changed counts E2E asserts today**: `juan.perez` now owns **3** farms (Finca Sin
  Lotes is third alphabetically) and farm 1 has **3** plots, returned alphabetically as
  `Lote El Abrevadero`, `Lote La Colina`, `Lote Sin Mapear`.
  `e2e/frontend/helpers.ts` `T.plotCount = '2 lotes'` and the "owns both farms" comment are stale.
- **`label_point` is derived, never stored** — `geometry.point_on_surface` computed in Python on the
  already-loaded GEOS geometry, so there is **no model field and no migration**, and no per-row
  `ST_PointOnSurface` round trip (the 12-plot `assertNumQueries(2)` test is the guard). It is the
  only anchor guaranteed to sit *on* the plot; `centroid` and `getBounds().getCenter()` fall outside
  a concave shape.
- `area_hectares` is a JSON **string** (`"8.42"`), `value` in the weather payload is a JSON
  **number**. `COERCE_DECIMAL_TO_STRING` was not touched; the weather dict is built by hand.
- Weather `recorded_at` is DRF ISO-8601 UTC ending in `Z`, with microseconds. Parse it.
- No pagination anywhere; lists are bare arrays. No endpoint returns 204 or an empty body.
- The weather query uses `DISTINCT ON`, which is PostgreSQL-only (this project is PostGIS).
- Wagtail: the farm edit page now renders the wagtailgeowidget point picker **and** a
  django-leaflet polygon drawing widget, in separate panel groups. The **wiring** is tested
  (`FarmAdminFormTests`: `WagtailFarmAdmin().get_form_class() is FarmAdminForm` for create and
  update, `boundary` is an optional `PolygonField` on a `LeafletWidget`, a bound polygon saves at
  SRID 4326, and a farm still saves with no boundary). Only the **visual** half stays manual —
  someone must open `/admin/snippets/farm/farm/edit/1/` once and confirm both maps init and save.
- `farm/forms.py` trips `ruff DJ007` (`fields = '__all__'`) twice — once for the pre-existing
  `PlotAdminForm` and once for the new `FarmAdminForm` that mirrors it. Left as-is: the snippet
  edit form needs every model field, and the repo is not ruff-clean today (177 findings). Every
  file I touched passes `ruff check`; I did not run `ruff format`, which would rewrite the whole
  repo's quote style.

## Decisions

- No `djangorestframework-gis`, no new Python package at all. Geometry is one module-level
  `to_geojson()` helper used by both serializers; it drops a `crs` key if GEOS ever emits one.
- `sensor_count` lives on `PlotQuerySet.with_sensor_count()` so the list and detail views cannot
  diverge; no `distinct=True` (single multi-valued join), commented at the definition.
- Fixtures hold everything time-independent; `seed_weather_readings` owns everything with a
  timestamp, because a frozen JSON date makes every card read "hace 7 meses" forever. It is
  delete-then-create per station, so re-running is safe. Flags: `--count` (12),
  `--interval-minutes` (5), `--lag-minutes` (3), `--stale-minutes` (95), `--stale-farm` (2),
  `--farm`. `--stale-farm` is the one flag not in the plan: hardcoding "farm 2 is the stale one"
  made the command untestable outside the seed's primary keys.
- Fixture rows must carry `created_at`/`updated_at` explicitly: `loaddata` is a raw save and does
  not fill `auto_now_add`, which fails the NOT NULL constraint.
- Out of scope: any write endpoint, an `api/sensors/` mount, an `is_stale` flag (the frontend owns
  staleness per contract Decision 7), and the frontend/E2E updates listed under Gotchas.

## How to load the seed

From `backend/`: `make loaddata` (now also loads `sensors/fixtures/initial_sensors.json` and runs
`seed_weather_readings`). The root `Makefile` target is kept in sync. `make seed-weather` re-stamps
just the weather timestamps when a dev database has been sitting for hours.

## For next agent

- **Frontend**: anchor the plot's map **pin and its permanent name label to `label_point`** — never
  to `centroid` and never to `getBounds().getCenter()`; both land off the plot for an L/U/crescent.
  `centroid` stays on the wire (stored field) but is not an anchor.
- **Frontend**: shapes are exactly `contract.md`. Coordinates are `[lng, lat]` — feed them to
  `L.geoJSON()`, never to `L.polygon`/`L.marker`. `sensor_count` is always present and an integer;
  `description` is `""`, never `null`; `area_hectares` is a string to `Number(...)`. The weather
  object omits keys entirely — never test for `null`/`0`.
- **QA**: re-set the E2E password after `make loaddata` (see Gotchas), and expect the seed to have
  3 farms for `juan.perez` and 3 plots on Finca El Tesoro, in that alphabetical order. The dev DB
  was **not** re-seeded in the fix pass, so the E2E password set after the first pass still stands.
  Manual check owed on the Wagtail farm edit page (two Leaflet widgets on one form render and save).
- **Frontend/E2E**: row order is now a backend guarantee — assert it directly, and do not add
  client-side sorting.

## Proposed improvements

Proposals only — I did not edit any `CLAUDE.md`.

1. `backend/CLAUDE.md`, **replacing** the now-false line *"Geometry fields (`PointField`/
   `PolygonField`) do not serialize through a plain `ModelSerializer`; exposing them needs
   `djangorestframework-gis`, which is not installed yet"*:
   > Expose geometry read-only with a `SerializerMethodField` returning `json.loads(value.geojson)` (`None` when null) — GeoJSON `{"type", "coordinates"}` in `[longitude, latitude]` order. `djangorestframework-gis` is only warranted if geometry ever becomes writable through the API.
2. `backend/CLAUDE.md`, under the DRF API layer:
   > Ownership-scoped lookups must not use `get_object_or_404`: DRF echoes Django's message, which names the model, so a 404 for someone else's row differs from a 404 for a missing one. Use `farm.api.get_owned_or_404` (scoped `.get()` → DRF `NotFound`), and assert the body `{"detail": "Not found."}` in tests, not just the status.
3. `backend/CLAUDE.md`, new "Fixtures" section:
   > Fixture rows must set `auto_now_add`/`auto_now` columns explicitly — `loaddata` saves raw and does not fill them, so the insert fails on NOT NULL. Anything time-relative (readings, "3 minutes ago") belongs in a management command wired into both `loaddata` targets, never in a fixture: a frozen date makes every "age" label wrong the day after it is written.
4. `backend/CLAUDE.md`, under DRF API layer (merge with the reviewer's proposal 1 — same rule):
   > `annotate()` discards `Meta.ordering`: Django does not apply default ordering to `GROUP BY` queries, so every annotated list queryset needs an explicit `.order_by(...)`. Pin it with a test whose insertion order differs from the expected order — asserting `response[0]` on rows created in the expected order passes either way.
5. `backend/CLAUDE.md`, under DRF API layer:
   > Assert `assertNumQueries` at two different row counts with the *same* expected N (e.g. a 2-plot and a 12-plot farm), and comment what each query is — a single-count assertion passes with a hardcoded wrong number and hides an N+1.
6. Root `CLAUDE.md`, under Tests (or `e2e/CLAUDE.md`):
   > `make loaddata` overwrites the seeded user's password with the fixture hash; the E2E password must be re-set afterwards (`e2e/README.md`). Changing seed row counts breaks the counts pinned in `e2e/frontend/helpers.ts` `T` — update both together.
7. Root `CLAUDE.md`, under Tests:
   > A regression test must be seen failing against the unfixed code before it counts as a regression test — temporarily revert the fix, run it, restore. A test written after the fix and never seen red usually pins the wrong thing.
8. `backend/CLAUDE.md`, new "Wagtail admin" section:
   > Custom `ModelForm`s and `SnippetViewSet.get_form_class()` overrides need a test — assert the viewset returns the form class, that each custom field keeps its widget and `required`, and that a bound submit persists. Only the "does the map/widget render" half is manual; the wiring failing is a 500 on the edit page, and without a test deleting the override leaves the suite green.
9. `backend/CLAUDE.md`, under the DRF API layer (geometry):
   > Never anchor a marker or label to a polygon's `centroid` or bounding-box centre — neither is
   > inside a concave shape. Expose `geometry.point_on_surface` (GEOS, computed in Python on the
   > already-loaded geometry — no per-row `ST_PointOnSurface` query) as a derived, unstored field.
   > Test it with a concave (L-shaped) polygon: a rectangle passes either way and proves nothing.
