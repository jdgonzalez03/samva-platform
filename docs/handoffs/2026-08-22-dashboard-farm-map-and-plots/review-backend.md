# backend review — dashboard farm map, plot list, stat cards, plot detail

Slug: `2026-08-22-dashboard-farm-map-and-plots` · Reviewed against
[`contract.md`](contract.md) (authoritative), [`acceptance-criteria.md`](acceptance-criteria.md),
[`plan.md`](plan.md), `backend/CLAUDE.md`, `docs/ARCHITECTURE.md`.

Verdict:      **CHANGES REQUESTED**
Blocking:     3
Non-blocking: 6

## How this was verified

- `cd backend && make test` → **48 tests, OK** (matches the handoff's claim).
- All four endpoints exercised against the **running dev DB with the real seed** through the Django
  test client (`make shell`), as `juan.perez` and as an anonymous client: field names, JSON types,
  nullability, status codes, 404 bodies, and per-request query counts.
- Raw SQL inspected for `with_sensor_count()` and for the weather `DISTINCT ON`.
- `makemigrations --check --dry-run` → **No changes detected** (model state and migrations agree).
- `ruff check farm/ sensors/` (28 findings in these two apps, 26 of them pre-existing — see NB-1).

What is genuinely correct (verified live, not read):

- `area_hectares` is the JSON **string** `"4.94"`; weather `value` is a JSON **number** (`18.52`).
- GeoJSON is `{type, coordinates}` only, rings closed, `[lng, lat]` (`[-74.105, 4.595]`).
  `location`/`boundary`/`geometry`/`centroid` are `null` where the row is null.
- Weather absent-key semantics hold: farm 1 → both keys, farm 2 → `air_temperature` only,
  farm 13 → `200 {}`. No nulls, no zeros, no 204. `recorded_at` ends in `Z`.
- `DISTINCT ON` SQL is correct: it orders `semantic_key ASC, snapshot.recorded_at DESC,
  station_variable.station_id DESC` (the contract's tie-break), filters inactive stations,
  inactive variable configs and `value IS NULL`, excludes `other`, and `select_related` covers
  every attribute the response dict reads → no follow-up query.
- `get_owned_or_404` delivers an **identical** `404 {"detail": "Not found."}` for all six cases
  (unknown id and other farmer's id, on plots / plot-detail / weather), with no farm or plot name
  in the body. AC33 holds. All four endpoints 401 when anonymous.
- Query counts on real seed data: farms 1, plots 2, plot detail 1, weather 2. The N+1 tests do
  assert **two different row counts** (2 vs 12 plots; 1 vs 3 stations) at the same expected N, and
  `with_sensor_count()` counts active sensors only (`filter=Q(field_sensors__is_active=True)`,
  asserted 3 active out of 5).
- Migration `0004_farm_boundary.py` is a single nullable `AddField` — no data loss, reversible,
  and no manager/panel churn leaked into it.
- Seed data really contains the unhappy paths (farm 2 boundary `null`, farm 13 no plots + location
  set, plot 29 `Lote Sin Mapear` with null geometry/`""` description/0 sensors, farm 1 with 2 active
  + 1 inactive station, farm 2 configuring `air_temperature` only, farm 2 stale at ~92 min).
- The two `loaddata` targets (`Makefile:38-43` and `backend/makefile:19-24`) are **in sync**; both
  end with `seed_weather_readings`.
- No new Python dependency: `requirements.txt` untouched, no `djangorestframework-gis`, no inline
  `pip install`, no hardcoded versions in prose.

## Blocking

1. **`backend/farm/models.py:87-94` (surfaced at `backend/farm/api.py:47`) — the plots list is
   returned in arbitrary order; `Plot.Meta.ordering` is silently discarded by the annotation.**
   Since Django 3.1, `Meta.ordering` is *not* applied to `GROUP BY` (aggregate) queries, so
   `annotate(Count(...))` drops it. Verified on the dev DB:
   - generated SQL ends at `... GROUP BY "farm_plot"."id"` — **no `ORDER BY` clause at all**;
   - `qs.ordered` is `False`, `qs.query.order_by` is `()`;
   - `GET /api/farm/farms/1/plots/` returns `["Lote Sin Mapear", "Lote La Colina",
     "Lote El Abrevadero"]`, while the unannotated `farm.plots.all()` returns the correct
     `["Lote El Abrevadero", "Lote La Colina", "Lote Sin Mapear"]`.

   This contradicts `contract.md` §2 ("Ordered by `Plot.Meta.ordering = ['name']` — the map's tab
   order and the list order are therefore the same (AC-A11Y-3)"), and `plan.md:173`'s assumption
   that "`Plot.Meta.ordering = ["name"]` stays" is simply false for an annotated queryset. The
   frontend does no client-side sorting (no `sort` anywhere in `frontend/layers/farm` or
   `frontend/layers/dashboard/app`), so the dashboard list, the map draw/tab order and any E2E
   assertion on row order all read an order Postgres is free to change after any write.
   **Fix:** add an explicit `.order_by('name')` inside `PlotQuerySet.with_sensor_count()` (query
   count is unaffected), **and** add a test whose insertion order deliberately differs from
   alphabetical order (e.g. create `Lote Sur`, then `Lote Ancla`, then `Lote Norte`, assert
   `["Lote Ancla", "Lote Norte", "Lote Sur"]`). None of the 48 tests currently pins order: every
   assertion either indexes by insertion position or builds a dict keyed by name, which is exactly
   why this passed.

2. **`backend/farm/forms.py:23-33` and `backend/farm/wagtail_hooks.py:18-19` — new code with zero
   tests (coverage gate).** `FarmAdminForm` and `WagtailFarmAdmin.get_form_class()` are new
   behaviour and nothing in the suite touches them; `make test` would stay green if either were
   deleted or if `boundary` lost its `LeafletWidget`. The handoff labels the whole thing
   "not automatable", but only the *visual* "does the second map initialise" part is manual — the
   wiring is cheaply testable and its failure mode (a `ModelForm` over a model whose panels bind
   `LeafletPanel`/`GeoAddressPanel`, built with `fields = '__all__'`) is a 500 on the snippet edit
   page, not a cosmetic issue.
   **Fix:** add a small test asserting `WagtailFarmAdmin().get_form_class() is FarmAdminForm`, that
   `FarmAdminForm()` instantiates with `boundary` bound to a `LeafletWidget` and `required=False`,
   and that a bound form with a valid polygon saves `Farm.boundary`. Keep the manual admin check in
   the QA handoff for the rendering half.

3. **`backend.md` "Contract deviations: None" and the "For next agent" notes are inaccurate — the
   AC self-check overstates what was verified.** The handoff asserts "Every field name, type,
   nullability, status code and error body matches `contract.md`", and tells QA/frontend that
   "farm 1 has 3 plots (`Lote Sin Mapear` is **third by name**)". Both are false today: the
   contract's ordering guarantee is not met, and the seeded farm actually returns `Lote Sin Mapear`
   **first**. AC31/AC32/AC33 themselves check out honestly (I re-verified each), so this is scoped
   to the ordering claim — but a downstream agent reading "no deviations" will not re-check it.
   **Fix:** after finding 1, correct the deviations line and the ordering statement in `backend.md`
   (or state the deviation explicitly if ordering is deliberately dropped — it should not be).

## Non-blocking

- **NB-1 — `backend/farm/forms.py:33`: a *new* `ruff DJ007` violation** (`fields = '__all__'` on
  `FarmAdminForm`). The repo is not ruff-clean (`farm/` + `sensors/` alone report 28 findings), and
  the twin at `forms.py:53` is pre-existing, but this one was added by this slice. Listing the
  fields explicitly removes it and also bounds what the admin form can write.
- **NB-2 — `backend/farm/serializers.py:76`: `# Subclassing is what guarantees the shared fields
  cannot drift from a list row.`** This comment defends a decision rather than explaining
  non-obvious behaviour — the root `CLAUDE.md` litmus test ("it defends a decision … delete it")
  points at removing it. The rationale already lives in `contract.md` Decision 5.
- **NB-3 — `backend/sensors/management/commands/seed_weather_readings.py:108-110`: `random.uniform`
  with no seed.** Every `make loaddata` / `make seed-weather` yields different values, so an E2E or
  screenshot check can never pin a stat-card number. A `--seed` flag (or a fixed
  `random.Random(...)` instance) would make the dev seed reproducible at no cost.
- **NB-4 — the same command skips inactive stations entirely (`models.py` filter at
  `seed_weather_readings.py:59-61`), so the dev DB cannot exercise AC22's negative half** ("an
  inactive station holding the *newest* reading must be ignored"). The unit test
  `FarmWeatherTests.test_an_inactive_station_is_ignored_even_with_the_newest_reading` covers it, so
  this is only a gap for manual/E2E inspection; seeding the inactive station with a *newer* series
  would make the seed prove it too.
- **NB-5 — `backend/farm/api.py:50-59`: `PlotDetailAPIView.get_object()` bypasses
  `check_object_permissions()`.** Harmless today (only `IsAuthenticated`, and ownership is in the
  lookup), but if an object-level permission class is ever added to this view it will be silently
  skipped. A one-line `self.check_object_permissions(self.request, obj)` before returning removes
  the trap.
- **NB-6 — no test pins the farms-list order either** (`FarmSerializer` is unannotated so
  `Meta.ordering` does apply, and the live response is alphabetical). Worth one assertion in the
  same test pass as finding 1, since the sidebar's default-farm selection depends on it.

## Proposed improvements

Proposals only — I edited no `CLAUDE.md` or agent spec. The orchestrator puts these to the user.

1. **`backend/CLAUDE.md`, DRF API layer** (new — this is the bug this slice shipped, and it is a
   recurring Django trap, not a one-off):
   > `annotate()` discards `Meta.ordering`: Django does not apply default ordering to `GROUP BY`
   > queries, so any annotated list queryset must `.order_by(...)` explicitly. Prove it with a test
   > whose insertion order differs from the expected order — asserting `response[0]` on rows
   > created in the expected order passes either way.
2. **`backend/CLAUDE.md`, DRF API layer** (new):
   > Verify a wire contract against a real response (running stack or a test-client call), never
   > against the model/serializer definition — ordering, nullability and decimal-as-string are
   > properties of the emitted JSON, not of the field declaration.
3. I endorse, unchanged, the four `backend/CLAUDE.md` proposals in `backend.md` — geometry via
   `SerializerMethodField` + `json.loads(value.geojson)` (replacing the now-false
   `djangorestframework-gis` line), `get_owned_or_404` instead of `get_object_or_404` for
   ownership-scoped lookups (assert the `{"detail": "Not found."}` body, not just the status),
   the new "Fixtures" section (explicit `auto_now_add`/`auto_now` columns; time-relative data in a
   management command wired into both `loaddata` targets), and `assertNumQueries` at two different
   row counts. Proposal 4 there overlaps my 1 — merge them into one rule if both are approved.
4. I endorse the engineer's root-`CLAUDE.md`/`e2e` proposal about `make loaddata` resetting the E2E
   password and seed row counts pinned in `e2e/frontend/helpers.ts`.

Verdict: **CHANGES REQUESTED**
