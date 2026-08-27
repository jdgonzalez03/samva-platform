# Spec — Dashboard farm map, plot list, stat cards, plot detail placeholder

Slug: `2026-08-22-dashboard-farm-map-and-plots`

Upstream: [`discovery-ba.md`](discovery-ba.md), [`discovery-ux.md`](discovery-ux.md).
Behaviour source of truth: [`acceptance-criteria.md`](acceptance-criteria.md) — this spec
does **not** restate the criteria, it points at them.

## Goal

Turn `/dashboard` from a placeholder card into the farm home screen: farm-level stat cards
on top, and below them the selected farm's plots in two interchangeable views — a Leaflet
map with the farm boundary and each plot drawn as a shape, and a list view. Both views
navigate to `/dashboard/plots/[id]`, which ships as a deliberate placeholder that dumps the
plot record inside a `<code>` block.

## In scope

### Backend

- **`Farm.boundary`** — new nullable `PolygonField` (SRID 4326), drawn in the Wagtail admin
  with the same Leaflet panel workflow `Plot.geometry` already uses. Fixtures updated so the
  seeded farms have boundaries.
- **`PlotSerializer` extended** — adds `geometry` (GeoJSON), `centroid`, and `sensor_count`.
  Geometry is serialized by hand (`json.loads(...geojson)` in a `SerializerMethodField`); no
  new dependency. `sensor_count` is a single `annotate(Count('field_sensors', filter=Q(is_active=True)))`
  on the queryset — **active sensors only**, and never a per-row query.
- **`FarmSerializer` extended** — adds `boundary` (GeoJSON, `null` when unset) and `location`
  so the map can fall back to centring on the farm point.
- **`GET farm/plots/<id>/`** — new owner-scoped plot detail endpoint returning the full plot
  record. Ownership is part of the lookup (`farm__owner__user=request.user`), so another
  farmer's plot **404s** rather than returning an empty result — same posture as the existing
  farm endpoints. This exists so the detail page survives a refresh or a bookmark.
- **Weather endpoint** — returns, per `semantic_key`, the latest reading for the selected
  farm: `{ value, unit, recorded_at }` for `air_temperature` and `solar_radiation`. Sourced
  from the newest `WeatherSnapshot` of the farm's **active** stations; when a farm has more
  than one active station, take the **most recent reading across all of them**. A key with no
  data is **absent from the response** — never zero, never invented.
- **`sensors` fixtures** — the app has none today. Seed weather stations, variable
  configurations, snapshots, measurements and field sensors so the cards and counts are
  non-empty in dev and in e2e. Seeded `recorded_at` values must land **recent relative to
  load time**, not a frozen past date, or every card permanently reads "hace 7 meses".

### Frontend

- **Stat cards** — four `UPageCard` tiles in a `UPageGrid`: plot count, sensor count, air
  temperature, solar radiation. The two counts derive from the plots response (no extra
  request); the two weather values come from the weather endpoint.
- **View toggle** — `UTabs` with **real content panels** (`:unmount-on-hide="false"`), not
  `:content="false"`. It sits directly above what it controls and **precedes the map in DOM
  order**, because the list view is the accessible alternative to the Leaflet canvas.
- **Map view** — client-only Leaflet. Farm boundary in one colour, each plot in another, a
  **basemap selector** offering a muted street basemap and satellite imagery, hover/focus
  info card via `UPopover`, click/Enter/tap-through to the plot detail.
- **List view** — `UPageList` of `ULink` rows. Columns: plot **name**, **description**,
  **area in hectares**, and the **field-sensor count at the far end of the row**.
- **`/dashboard/plots/[id]`** — placeholder page in the dashboard layout behind `auth`
  middleware: an `<h1>` naming the plot, the record serialized inside a `<pre>`/`<code>`
  block, and a link back to the dashboard.
- **`FarmStats.vue` is deleted.** Its four values are `Math.random()` output with hardcoded
  Spanish strings, it is referenced by no page, and two of its cards (relative humidity, soil
  pH) have no possible backend source — there is no `soil_ph` semantic key. Its visual
  treatment is harvested into the new data-fed, translated cards; the file itself goes.
- **i18n** — every new string exists in both `es` and `en`. Pages and presentational
  components live in the `dashboard` layer; all data (types, api module, composables, query
  keys) lives in the `farm` layer, following the sanctioned one-way `dashboard → farm`
  dependency already recorded in `frontend/CLAUDE.md`.

### E2E

Extends `e2e/frontend/dashboard.spec.ts` and `e2e/frontend/a11y.spec.ts`; new plot-detail
coverage goes in the spec matching its frontend layer name. Every UI string a spec selects by
lives in the exported `T` map in `e2e/frontend/helpers.ts`.

## Out of scope

- **A crop (`cultivo`) field.** Explicitly decided against — see Resolved decisions. Nothing
  in this feature adds a crop field, a `Crop` model, or a planting history.
- A per-plot `address` field.
- A "Lotes" sidebar entry and a `/dashboard/plots` index route. A user who hand-edits the URL
  to `/dashboard/plots` lands on the existing designed 404 page; that is accepted.
- A general-purpose `sensors` CRUD API. Only the weather-reading endpoint above is built.
- Editing geometry through the API (which is why `djangorestframework-gis` is not added).
- Vector tiles, geometry simplification, real-time updates, and per-crop prediction
  parameters.

## UX notes

- **The list is the accessible equivalent of the map**, not a convenience. This drives the DOM
  order (toggle before map), the toggle's discoverability, and AC-A11Y-6/13.
- **`UPopover`, not `UTooltip`,** for the plot info card: a tooltip is non-interactive, so the
  pointer cannot travel into it and it cannot hold a "Ver lote" action — that fails WCAG
  1.4.13 (Content on Hover or Focus).
- **`UPageList` of `ULink` rows, not `UTable`** — each row is one link target, which keeps the
  keyboard path and the ≥24×24px target size simple.
- **Touch**: the first tap on a plot opens the info card with an explicit "Ver lote" action; it
  does not navigate immediately. A farmer tapping to identify a plot should not be thrown onto
  another page.
- **Basemap contrast is the sharp edge of the satellite decision.** Satellite imagery is a
  photographic, high-variance background, so a single-colour outline cannot guarantee ≥3:1.
  Polygon strokes must therefore carry a **casing** (a contrasting halo/underlay stroke) so the
  outline holds contrast against both basemaps, and plot identity must survive greyscale via
  its visible name label and a distinct stroke style for the farm boundary.
- Loading uses skeletons with `aria-busy="true"`; the client-only map needs a **same-height**
  `<ClientOnly>` fallback so the page does not jump on hydration.
- Errors render text plus a keyboard-reachable Retry — never colour alone.
- Switching farms in `FarmsMenu` refits the map and refetches plots and weather.

## Resolved decisions

Each of these was put to the user and answered; they override the discovery docs where they
disagree.

1. **No crop field.** The hover card and the list column show **`Plot.description`**, which
   already exists. The backend gains no crop field and no `Crop` model. *(Overrides BA Q1 and
   UX Q1, both of which had recommended adding a `CharField`.)* Wherever the discovery docs
   and their draft criteria say "crop", read "description".
2. **Farm boundary**: add the nullable `Farm.boundary` polygon, with automatic fit-to-plots
   when it is null. Deriving a convex hull from the plots was **rejected** — with one plot the
   hull is the plot itself, and with scattered plots it swallows land the farm does not own; it
   would be false data shown where a user reads a property line.
3. **Weather cards are in this feature**, endpoint and fixtures included.
4. **"Address" column shows `area_hectares`.** The farm address repeated on every row is noise,
   and a per-plot address field would go unmaintained.
5. **View mode**: `?view=map|list` in the URL is the source of truth (linkable, back/forward
   works, e2e can deep-link); the last choice is mirrored to `localStorage` and used only when
   the query param is absent — the same shape as `selected-farm.ts`. First-ever visit defaults
   to **map**.
6. **Basemap: both, with a selector** — muted street *and* satellite. *(This is the one place
   the user chose against a recommended default; the UX designer had recommended street-only
   precisely because satellite makes the ≥3:1 outline requirement harder. The casing
   requirement in UX notes above is how that is paid for, and AC-A11Y-7 is verified against
   **both** basemaps.)*
7. **No new navigation**: no sidebar entry, no `/dashboard/plots` index.
8. **Accepted at the agents' recommended defaults**: hand-serialized GeoJSON (no
   `djangorestframework-gis`); owner-scoped `farm/plots/<id>/` returning the full record;
   `sensor_count` as a single annotate counting active sensors only; plots without geometry are
   not drawn but are still listed, with a visible note stating how many could not be placed;
   weather cards show an explicit "sin datos" state and the reading's age, badged "desactualizada"
   past **30 minutes**; most recent reading across multiple active stations; recent-relative
   fixture timestamps; first tap opens the card with a "Ver lote" action; `UTabs` with real
   panels, `UPopover` for the info card, `UPageList` of `ULink` rows; toggle before the map in
   DOM order; `FarmStats.vue` deleted and rebuilt against real data; pages in the `dashboard`
   layer, data in the `farm` layer.

## Known risks carried into the plan

- **Leaflet is the app's first map**: it is installed but imported nowhere and its CSS is
  loaded nowhere. It touches `window` at import time, so the map component must be client-only
  and dynamically imported, and its CSS must not enter the shared bundle — the landing page
  must not pay for it.
- **N+1 on sensor counts** if `sensor_count` is computed per row instead of annotated.
- **Empty demo**: without the new `sensors` fixtures, every reviewer and every e2e run sees
  empty counts and empty weather cards. The fixtures are part of this feature.
