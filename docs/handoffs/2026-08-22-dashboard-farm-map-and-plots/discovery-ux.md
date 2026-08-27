# ux discovery — dashboard farm map & plots

Summary: Analyzed `docs/ARCHITECTURE.md`, `frontend/CLAUDE.md`, the current dashboard index page,
the dead `FarmStats.vue`, the whole `farm` layer, and the backend `farm`/`sensors` models + API.
The UX is buildable on the existing `UDashboardPanel` pattern, but **most of the data the feature
displays does not exist yet** (no crop, no per-plot address, no plot geometry in the API, no farm
boundary polygon, no sensors API at all) — those are the decisions that must be settled before a
plan can be written.

## Surfaces touched

| Surface | Route | Status |
| --- | --- | --- |
| Dashboard home | `/dashboard`, `/en/dashboard` | exists — extended |
| Plot detail (placeholder) | `/dashboard/plots/[id]`, `/en/dashboard/plots/[id]` | **new route** |
| Dashboard sidebar farm switcher | `FarmsMenu.vue` | unchanged, but it now drives the map |
| a11y regression scan | `e2e/frontend/a11y.spec.ts` | must cover both view modes + the new route |

Routes the description doesn't name but the feature reaches: the **English mirrors** of both pages
(the `/en` prefix is a real, separately-rendered surface — see `i18n.spec.ts`), and the plot detail
route reached by **direct URL / refresh / bookmark**, not just by clicking a plot.

## Recommended page composition (inside the existing `UDashboardPanel`)

```
UDashboardPanel #header  → UDashboardNavbar (title "Dashboard", icon i-lucide-house)
UDashboardPanel #body    → UContainer (flex flex-col gap-4 p-4)
     1. Stat cards   → UPageGrid > 4× UPageCard      (farm-level KPIs)
     2. Section head → farm name + UTabs triggers    (map | list)
     3. Map / list   → UTabs content panels          (one data source, two renderings)
```

Put the mode toggle **immediately above the map/list**, in the same section header, not in a
`UDashboardToolbar`: the toolbar sits above the stat cards and would read as "filters the whole
page". The toggle only changes the plot rendering, so it must be visually adjacent to what it
controls (and, for screen readers, `aria-controls` the panel).

## Nuxt UI v4 components (all verified present in `node_modules/@nuxt/ui`)

- **Mode toggle** — `UTabs` with real content panels (`:items="[{ label: Map, icon: i-lucide-map,
  value: 'map' }, { label: List, icon: i-lucide-list, value: 'list' }]"`, `variant="pill"`,
  `:unmount-on-hide="false"`). Reka gives `role="tablist"`, roving tabindex, arrow-key navigation
  and `aria-selected` for free. Do **not** use `:content="false"` with a hand-rolled panel — the
  triggers still emit `aria-controls` pointing at an element that no longer exists, which axe flags.
  `unmount-on-hide="false"` also keeps the Leaflet instance alive across switches (a remount would
  need `map.invalidateSize()` and would refetch tiles).
  Rejected alternative: `UFieldGroup` + two `UButton`s with `aria-pressed` — works, but tabs are the
  correct pattern for "two renderings of one dataset" and cost less ARIA by hand.
- **Plot list rows** — `UPageList` of `ULink`-wrapped rows, **not** `UTable`. There are 4 fields and
  the whole row is a navigation target; `UTable`'s TanStack machinery buys nothing here, and a row
  that is a real `<a>` gives keyboard operability, middle-click, and copy-link for free.
  Sensor count as a trailing `UBadge` with a visible unit label, `i-lucide-radio-tower` icon.
- **Stat cards** — `UPageGrid` + `UPageCard variant="subtle"`, reusing the exact `:ui` treatment
  already written in `FarmStats.vue` (rounded leading icon, uppercase muted title, `text-2xl`
  value). `USkeleton` inside each card while pending.
- **Empty / error states** — `UEmpty` (icon + title + action) and `UError`, or the existing
  text + link-`UButton` Retry pattern already used on `/dashboard` and in `FarmsMenu.vue`. Pick one
  and use it everywhere; today the page hand-rolls it.
- **Hover card on the map** — `UPopover` (`:open` controlled by hover *and* focus), **not**
  `UTooltip`. The card must contain an actionable "View plot" link, and `UTooltip` is explicitly
  non-interactive (pointer can't enter it → fails 1.4.13 "hoverable").
- **Plot detail placeholder** — `UDashboardPanel` + `UDashboardNavbar` (with `UBreadcrumb`
  Dashboard › Plots › `<name>`) + a `UCard` containing `<pre><code>`. Same skeleton/error/not-found
  states as everything else.

## Reuse (cite before building)

- `frontend/layers/dashboard/app/pages/dashboard/index.vue` already models **skeleton → no-farm →
  error+Retry → empty → data**. Extend it; do not invent a second state vocabulary.
- `frontend/layers/dashboard/app/components/dashboard/FarmStats.vue` is **dead code** (zero
  references in `frontend/` or `e2e/`), hardcoded Spanish, and filled with `Math.random()` values.
  Harvest its visual treatment, then delete the file — leaving it invites someone to ship fake data.
- `useSelectedFarm` / `useFarmPlotsQuery` / `FarmQueryKey` are the data seam; the farm-id-in-the-
  query-key pattern means switching farms in `FarmsMenu` refetches the map with no extra wiring.
- `useSelectedFarm`'s reconcile-against-the-server-list rule and `selected-farm.ts`
  (`localStorage` + `import.meta.client` guard) are the template for persisting the view mode.

## Data gaps — the feature currently describes UI for data that does not exist

| UI element asked for | Backend reality |
| --- | --- |
| Plot **crop** (map card + list) | **No crop field anywhere** — `Plot` has `name`, `description`, `geometry`, `centroid`, `area_hectares` |
| Plot **address** (list) | Only `Farm.address` exists; every row would show the same string |
| Plot polygons on the map | `Plot.geometry` exists in the DB but **`PlotSerializer` does not expose it** (nor `centroid`) |
| **Farm boundary** polygon | `Farm` has only `location` (a single Point) — there is **no boundary geometry** |
| **Sensor count** per plot | `FieldSensor.plot` exists, but no serializer field and **no `sensors` API at all** (`sensors/views.py` is empty, no URL mount) |
| `air_temperature` / `solar_radiation` cards | Data exists (`WeatherMeasurement` via Celery), **no endpoint** |

Every one of these is an Open question below. The plan must not assume any of them.

## Context divergence

One `PlotCard` content model, three renderings: **map hover/focus card** (name + crop, compact),
**list row** (name + address + crop + sensor count), **detail page** (raw dump). Build one
`usePlotSummary`-shaped view model so the three never drift; the crop/address decision then lands
in one place.

## Interaction states (every one is required work)

| State | Map mode | List mode | Stat cards |
| --- | --- | --- | --- |
| Loading | `USkeleton` block at the map's final height (reserve the space — no layout shift), `aria-busy="true"` | 3 skeleton rows | skeleton per card |
| No farms at all | "Create/select a farm" `UEmpty`; **do not render the map** | same | cards show "—" |
| Farm with no plots | map centred on the farm boundary (or `Farm.location`) + empty overlay text | `UEmpty` "This farm has no plots" (reuse `farm.plots.none`) | plots = 0, sensors = 0 |
| Query error | text + Retry (reuse `farm.plots.error` / `farm.plots.retry`), `role="alert"` | same | per-card error text |
| **Plot with no geometry** | not drawable — must still appear, as a marker at `centroid` if present, otherwise **listed in an "N plots not on the map" note with links** so it is not silently lost | appears normally | counted normally |
| **Farm with no boundary** | fit bounds to the union of plot geometries; if none, centre on `Farm.location`; if that is null too, show a "location not set" empty map state | n/a | n/a |
| **No weather station** | n/a | n/a | card renders "No station" + a hint, not `0` |
| **Station but no data yet** | n/a | n/a | "No data yet" |
| **Stale data** | n/a | n/a | value + relative timestamp + a `UBadge` reading "Outdated" (text, not colour) |
| SSR / hydration | Leaflet is client-only: the map component must be `<ClientOnly>`-wrapped with a `#fallback` skeleton of the same height, or the first paint jumps | unaffected | unaffected |

Never render `0 °C` for "no data" — a zero reading and a missing reading must be visually and
programmatically distinct.

## Deep-link reachability (real risk here)

`/dashboard/plots/[id]` is reachable by **direct URL, refresh, and bookmark**, when no plot list is
in the Vue Query cache and the selected farm may not even be the plot's farm. Today the only way to
obtain a plot is `farm/farms/<farmId>/plots/` — which requires already knowing the farm. So the
detail page **cannot** be built by "find the plot in the cached list": it needs a single-plot,
ownership-scoped endpoint (`GET farm/plots/<id>/`, 404 for someone else's plot). It must also handle
"plot belongs to a farm that isn't the selected one" — recommendation: switch the selected farm to
the plot's farm on load, so the sidebar and a Back link stay coherent.

## Colour

The farm boundary and plot fills carry meaning over a **photographic, variable** tile background, so
colour alone can't do the work:

- Every plot gets a **permanent visible text label** (the plot name) at its centroid, not only a
  hover card — that is what makes the map readable without colour and at a glance.
- Plot **outlines** must be ≥3:1 against the tiles (1.4.11). Against arbitrary satellite/OSM imagery
  this cannot be guaranteed by a single stroke colour — use a **two-tone stroke** (a dark casing
  under a light core, the standard cartographic halo) or a solid fill at high enough opacity that
  the stroke contrasts with its own fill rather than with the tiles. Same for the plot-name labels:
  white text with a dark halo/`paint-order: stroke`.
- Farm boundary vs. plot must differ by **shape, not hue** — dashed boundary casing vs. solid plot
  outline, so the distinction survives greyscale and colour-blind viewing.
- Hover/focus/selected states must add a **visible thickness or pattern change**, not just a hue
  shift, and the keyboard focus ring on a plot needs its own ≥3:1 contrast (see AC-A11Y-3).
- The dashboard layout forces `colorMode.preference = 'dark'` (`layouts/dashboard.vue`) — pick a
  basemap that works in dark mode, and verify the stat-card and list contrast in dark mode, which is
  the only mode users will see.

## Responsive

- **Stat grid**: 1 column < `sm`, 2 at `sm`, 4 at `lg` (`UPageGrid` + `lg:grid-cols-4`, as in
  `FarmStats.vue`). The `lg:rounded-none first:rounded-l-lg` seam trick in that file only works in
  the 4-across row — it must not leak into the stacked breakpoints.
- **Map**: fixed viewport-relative height (e.g. `h-[60vh] min-h-80 lg:h-[520px]`), never `100vh`
  (mobile browser chrome) and never a height that collapses to 0 inside a flex parent — Leaflet
  needs a measurable box. Touch: keep one-finger pan but ensure the page is still scrollable past
  the map (`dragging` + `tap` are fine; avoid `scrollWheelZoom` hijacking page scroll on desktop).
- **List**: 4 columns on desktop collapse to a two-line row on mobile (name + crop on line 1,
  address + sensor count on line 2) — no horizontal scroll, and every row keeps a ≥24px target.
- At 320px / 200% zoom both modes must reflow; the toggle stays visible above the content.

## i18n

New strings split by ownership, both `es` and `en`, per layer:

- `dashboard.*` — `dashboard.view.map`, `dashboard.view.list`, `dashboard.view.label`
  (the toggle's group label), `dashboard.map.*` (region label, "not on the map" note, "location not
  set"), `dashboard.stats.plots|sensors|temperature|radiation`, `dashboard.stats.noStation`,
  `dashboard.stats.noData`, `dashboard.stats.stale`, `dashboard.stats.updatedAt`.
- `farm.plots.*` — extend the existing namespace: `farm.plots.crop`, `farm.plots.address`,
  `farm.plots.sensors` (pluralized, `{count} sensor | {count} sensors`), `farm.plots.detailTitle`,
  `farm.plots.notFound`, `farm.plots.back`, `farm.plots.viewPlot`.
- Units (`°C`, `W/m²`, `ha`) come from the backend `EnvironmentalVariable.unit` — don't hardcode
  them in locale files. Numbers/dates format via `Intl` with the active locale.
- The plot **name/crop are user data** and are never translated; only the labels around them are.

## Accessibility criteria

**AC-A11Y-1** — Given the dashboard in either view mode, When I run `@axe-core/playwright` with
`['wcag2a','wcag2aa','wcag21aa','wcag22aa']` on `/dashboard`, `/en/dashboard` and
`/dashboard/plots/<id>`, Then there are zero serious or critical violations. *(backstop)*

**AC-A11Y-2** — Given the map/list toggle, When I Tab to it, Then it receives a visible focus ring,
exposes `role="tablist"` with two `role="tab"` items named "Map" and "List", the active tab has
`aria-selected="true"`, Left/Right arrows move between tabs, and Enter/Space activates the focused
tab. *(2.1.1, 2.4.7, 4.1.2)*

**AC-A11Y-3** — Given map mode, When I Tab through the map, Then each plot shape is focusable in
the same order as the list, shows a focus indicator with ≥3:1 contrast against both its fill and
the map tiles, and exposes an accessible name of the form "<plot name>, <crop>, <n> sensors".
*(2.1.1, 2.4.7, 2.4.11, 4.1.2)*

**AC-A11Y-4** — Given a focused plot shape, When I press Enter or Space, Then I navigate to
`/dashboard/plots/<id>`; the same action is available with a single tap on touch and a single click
with a mouse, with no drag, long-press, or multi-point gesture required anywhere. *(2.1.1, 2.5.1,
2.5.7)*

**AC-A11Y-5** — Given a plot, When I hover it **or** move keyboard focus to it, Then the same info
card appears; it is referenced by `aria-describedby` on the plot control so its text is announced,
it stays visible while the pointer moves from the plot onto the card, and `Escape` dismisses it
without moving focus. *(1.4.13, 4.1.2)*

**AC-A11Y-6** — Given a screen reader, When I reach the map, Then it is a labelled region ("Farm
map, <farm name>") whose content is also available as text, and the list view — reachable from the
toggle that precedes the map in DOM order — is announced as the equivalent alternative.
*(1.1.1, 1.3.1, 2.4.3)*

**AC-A11Y-7** — Given the map rendered in greyscale (colour removed), When I look at it, Then each
plot is still identifiable by its visible name label and each shape is still distinguishable from
the farm boundary by stroke style, with plot outlines ≥3:1 against their background. *(1.4.1,
1.4.11)*

**AC-A11Y-8** — Given list mode, When I Tab through the rows, Then each row is a single link named
"<plot name>", its sensor count is exposed as text (not an icon alone), its interactive target is
≥24×24 px, and the list is announced as a list with its item count. *(1.3.1, 2.5.8, 4.1.2)*

**AC-A11Y-9** — Given the stat cards, When they render, Then each value is preceded by its visible
text label and unit, no trend/state is signalled by colour alone (a "Outdated"/"No data" text or
badge accompanies any such state), and all text meets 4.5:1 (3:1 for the ≥24px value) in dark mode.
*(1.4.1, 1.4.3)*

**AC-A11Y-10** — Given any pending query on the page, When it is loading, Then the placeholder
carries `aria-busy="true"`; When it fails, Then the error text plus a keyboard-reachable Retry
button named "Retry"/"Reintentar" is announced through a live region. *(4.1.3, 1.4.1)*

**AC-A11Y-11** — Given `/dashboard/plots/<id>`, When it loads, Then the document title and a single
`<h1>` name the plot, the serialized dump is inside a labelled `<pre>`/`<code>` region that is
keyboard-scrollable, and a "Back to dashboard" link returns to the previous view mode.
*(2.4.2, 2.4.6, 2.1.1)*

**AC-A11Y-12** — Given a 320px-wide viewport (and 200% zoom at 1280px), When I view the dashboard,
Then the stat cards, the toggle, the map and the list all reflow with no two-dimensional scrolling
and no clipped content or controls. *(1.4.4, 1.4.10)*

**AC-A11Y-13** — Given a plot without geometry, When map mode renders, Then it is still reachable —
listed by name with a link in a visible "not shown on the map" note — so no plot is available only
to sighted users of the map. *(1.3.1, 2.4.3)*

Beyond AA (recommended, not a gate): honour `prefers-reduced-motion` for Leaflet's fly-to/zoom
animations.

Recommendation: **adjust** — the composition and components above are sound and reuse what exists,
but roughly half the displayed data (crop, per-plot address, plot geometry in the API, farm
boundary, sensor counts, weather values) has no backend today. Settle Q1–Q7 before planning;
without them the plan will invent fields.

## Open questions

1. **Crop.** No crop field exists anywhere in the backend. Add `crop` (optional `CharField`, or FK
   to a `Crop` catalog) to `Plot`, or drop crop from this feature and show `description` instead?
   *Recommended default: add a nullable `crop` CharField to `Plot`, show "—" when empty.*
2. **Plot address.** `Plot` has no address (only `Farm` does), so an address column would repeat the
   farm's address on every row. Show the farm address anyway, add a per-plot address field, or
   replace the column with area (ha)? *Recommended default: replace it with `area_hectares`, which
   already exists and is genuinely per-plot.*
3. **Farm boundary.** `Farm` has only a `location` Point — no boundary polygon. Add a nullable
   `boundary` PolygonField to `Farm`, or derive the boundary from the plots' geometries?
   *Recommended default: add `boundary`, and fall back to fitting the map to the plots when it's
   null.*
4. **Geometry in the API.** `PlotSerializer` exposes no geometry. Add `geometry` (GeoJSON) and
   `centroid` to the existing `farm/farms/<id>/plots/` response, or a separate GeoJSON endpoint?
   *Recommended default: extend the existing endpoint — one request feeds both the map and the
   list, and the existing `useFarmPlotsQuery` cache entry keeps working.*
5. **Single-plot endpoint.** `/dashboard/plots/[id]` must survive a direct load/refresh, and no
   single-plot endpoint exists. Add `GET farm/plots/<id>/` (ownership-scoped, 404 for others)?
   *Recommended default: yes — without it the detail page only works when arrived at by click.*
6. **Sensor counts.** No sensors API exists at all. Expose `sensor_count` on the plot serializer
   (cheap, one annotate) or build a proper `sensors` API now? *Recommended default: `sensor_count`
   annotation on the plot serializer; a full sensors API is a separate feature.*
7. **Weather stat cards.** Also no endpoint. Add `GET farm/farms/<id>/summary/` returning plot
   count, sensor count and the latest `air_temperature` / `solar_radiation` with their
   `recorded_at` and units — or defer the weather cards to a later feature and ship only the two
   counts now? *Recommended default: build the summary endpoint now; the cards are half the
   feature's value.*
8. **Stale weather threshold.** Polling runs every 5–15 min. At what age does a reading render as
   "Outdated"? *Recommended default: 30 minutes; always show the relative timestamp underneath.*
9. **View mode persistence.** *Recommended default: `?view=map|list` in the URL is the source of
   truth (linkable, back/forward works, e2e can deep-link), with the last choice mirrored to
   `localStorage` and used only when the query param is absent — same shape as
   `selected-farm.ts`. Default on a first-ever visit: map.* Confirm, or prefer URL-only?
10. **Touch behaviour on a plot.** Should the first tap open the info card (requiring a second tap
    on "View plot" to navigate), or navigate immediately? *Recommended default: first tap opens the
    card with an explicit "View plot" action — a farmer tapping to identify a plot shouldn't be
    thrown onto another page.*
11. **Basemap.** Which tile provider, and satellite imagery or a muted street map? *Recommended
    default: a muted/greyscale OSM-based raster basemap — it maximises polygon contrast and keeps
    attribution simple; satellite imagery makes the ≥3:1 outline requirement much harder.*
    (Tile attribution is a licensing requirement, not optional, whichever is chosen.)
12. **`FarmStats.vue`.** It is unreferenced dead code with random fake values and hardcoded Spanish.
    *Recommended default: delete it and rebuild the cards as a translated, data-fed component,
    keeping its visual treatment.* Confirm deletion.
13. **Layer ownership.** Does the plot detail page live in the `dashboard` layer or the `farm`
    layer? *Recommended default: pages and presentational components in `dashboard`, all data
    (types, api, composables, query keys) in `farm` — this matches the sanctioned one-way
    `dashboard → farm` dependency already recorded in `frontend/CLAUDE.md`.*

## Proposed improvements

Two candidate rules for `frontend/CLAUDE.md` (orchestrator to confirm with the user — I did not
edit any `CLAUDE.md`):

1. **Client-only UI (Leaflet maps, canvas widgets) is wrapped in `<ClientOnly>` with a `#fallback`
   placeholder of the same fixed height** — a fallback-less `<ClientOnly>` causes a hydration
   layout jump, and a zero/auto-height parent leaves Leaflet with no box to measure.
   *(Section: "SSR".)*
2. **Any component that conveys state through colour on a variable background (map polygons, chart
   marks, badges over imagery) must also convey it through text, shape, or stroke style, and carry
   its own casing/halo so the ≥3:1 non-text contrast holds against arbitrary pixels.**
   *(Section: "UI components & icons".)*
