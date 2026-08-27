# frontend handoff — Dashboard farm map, plot list, stat cards, plot detail

**Summary:** `/dashboard` now renders four stat cards (plots, active sensors, air temperature,
solar radiation) plus a Map/List tab pair — a Leaflet map with focusable, casing-paired plot
polygons and a hoverable info popover, and an equivalent plot list — with the view mode kept in
`?view=`. `/dashboard/plots/[id]` is a new placeholder detail page fed by `GET farm/plots/<id>/`.

## Files changed

**farm layer (data only)**

- `frontend/layers/farm/app/types/farm.ts` — added `GeoJSONPolygon`, `GeoJSONPoint`,
  `PlotDetail`, `WeatherReading`, `WeatherSemanticKey`, `FarmWeather`; `Farm` gained
  `location`/`boundary`; `Plot` gained `geometry`/`centroid`/`sensor_count`.
- `frontend/layers/farm/app/utils/api/farm.ts` — `getPlot`, `getWeather`.
- `frontend/layers/farm/app/constants/query-keys.ts` — `PLOT`, `WEATHER`.
- `frontend/layers/farm/app/composables/usePlotQuery.ts` — new.
- `frontend/layers/farm/app/composables/useFarmWeatherQuery.ts` — new.

**common layer**

- `frontend/layers/common/app/utils/date.ts` — added `formatRelativeTime(iso, locale, now)`.

**dashboard layer**

- `frontend/layers/dashboard/app/pages/dashboard/index.vue` — rewritten.
- `frontend/layers/dashboard/app/pages/dashboard/plots/[id].vue` — new.
- `frontend/layers/dashboard/app/components/dashboard/PlotsMap.client.vue` — new.
- `frontend/layers/dashboard/app/components/dashboard/PlotsList.vue` — new.
- `frontend/layers/dashboard/app/components/dashboard/FarmStatCards.vue` — new.
- `frontend/layers/dashboard/app/components/dashboard/WeatherStatCard.vue` — new.
- `frontend/layers/dashboard/app/components/dashboard/StatCard.vue` — new (tile shell,
  harvested from the deleted `FarmStats.vue`).
- `frontend/layers/dashboard/app/components/dashboard/PlotInfoCard.vue` — new.
- `frontend/layers/dashboard/app/components/dashboard/UnmappedPlotsNote.vue` — new.
- `frontend/layers/dashboard/app/components/dashboard/BasemapSelector.vue` — new.
- `frontend/layers/dashboard/app/components/dashboard/FarmStats.vue` — **deleted**.
- `frontend/layers/dashboard/app/composables/useDashboardViewMode.ts` — new.
- `frontend/layers/dashboard/app/composables/useNow.ts` — new.
- `frontend/layers/dashboard/app/constants/map.ts` — new.
- `frontend/layers/dashboard/app/constants/weather.ts` — new.
- `frontend/layers/dashboard/app/utils/view-mode.ts` — new.
- `frontend/layers/dashboard/app/utils/plot-features.ts` — new.
- `frontend/layers/dashboard/nuxt.config.ts` — added `imports.dirs` for the layer composables.
- `frontend/layers/dashboard/i18n/locales/{es,en}.json` — new keys, `index.welcome` removed.
- `frontend/package.json` / `package-lock.json` — added `@types/leaflet` as a **direct**
  devDependency (it was only present transitively via the unused `@vue-leaflet/vue-leaflet`).

## Routes / UI

| Route (name) | Entry point |
| --- | --- |
| `/dashboard` (`dashboard`) — unchanged path, rewritten body | sidebar "Dashboard" |
| `/dashboard?view=map` / `?view=list` | the "Mapa"/"Lista" tabs |
| `/dashboard/plots/[id]` (`dashboard-plots-id`) | click/Enter a map polygon · "Ver lote" in the map info card · any list row · any link in the "no se muestran en el mapa" note |
| back from detail | "Volver al panel" link, returns to the stored view mode |

---

## ⚠️ Strings QA must put in `e2e/frontend/helpers.ts` (`T` / `T_EN`)

### REMOVED — these no longer render anywhere

| Old `T` entry | Value | Where it went |
| --- | --- | --- |
| `T.plotCount` | `2 lotes` | **Gone.** `farm.plots.count` is no longer rendered by the dashboard. The plot count is now the bare number `3` under the visible label `LOTES` (uppercased by CSS; the DOM text is `Lotes`). Re-point the five assertions in `farm.spec.ts` at the plot-count stat card, e.g. `page.getByText('Lotes').locator('..').getByText('3', { exact: true })` or a card-scoped locator. |
| (none in `T`) | `Bienvenido a tu panel. Muy pronto encontrarás aquí…` | `dashboard.index.welcome` deleted from both locale files. |
| (none in `T`) | `Temperatura Promedio` / `Humedad Promedio` / `pH del Suelo` / `Radiación Solar` | hardcoded Spanish in the deleted `FarmStats.vue`. |

### ADDED — Spanish (default locale, unprefixed)

| i18n key | `es` value |
| --- | --- |
| `dashboard.view.label` | `Vista de los lotes` |
| `dashboard.view.map` | `Mapa` |
| `dashboard.view.list` | `Lista` |
| `dashboard.stats.plots` | `Lotes` |
| `dashboard.stats.sensors` | `Sensores activos` |
| `dashboard.stats.temperature` | `Temperatura del aire` |
| `dashboard.stats.radiation` | `Radiación solar` |
| `dashboard.stats.noData` | `Sin datos` |
| `dashboard.stats.stale` | `Desactualizada` |
| `dashboard.stats.error` | `No se pudo cargar el clima.` |
| `dashboard.stats.updated` | `Actualizado {age}` → e.g. `Actualizado hace 16 minutos` |
| `dashboard.map.region` | `Mapa de la finca, {name}` → `Mapa de la finca, Finca El Tesoro` |
| `dashboard.map.alternative` | `La vista de lista muestra la misma información en texto.` |
| `dashboard.map.plotLabel` | `{name}, {description}, {count} sensores` → `Lote La Colina, Lote en la colina con vista a los cerros orientales, 3 sensores` |
| `dashboard.map.unmapped` | `{count} lote no se muestra en el mapa \| {count} lotes no se muestran en el mapa` |
| `dashboard.map.noLocation` | `Esta finca aún no tiene ubicación en el mapa.` |
| `dashboard.map.basemap` | `Mapa base` |
| `dashboard.map.street` | `Calles` |
| `dashboard.map.satellite` | `Satélite` |
| `dashboard.map.loading` | `Cargando el mapa` |
| `dashboard.plots.noDescription` | `Sin descripción` |
| `dashboard.plots.sensors` | `{count} sensor \| {count} sensores` |
| `dashboard.plots.area` | `{value} ha` → `11,12 ha` in `es-CO` |
| `dashboard.plots.viewPlot` | `Ver lote` |
| `dashboard.plots.listLabel` | `Lotes de la finca` |
| `dashboard.plotDetail.title` | `Lote {name}` |
| `dashboard.plotDetail.dump` | `Datos del lote` |
| `dashboard.plotDetail.back` | `Volver al panel` |
| `dashboard.plotDetail.notFound` | `Lote no encontrado` |
| `dashboard.plotDetail.notFoundBody` | `Este lote no existe o no pertenece a tu cuenta.` |
| `dashboard.plotDetail.error` | `No se pudo cargar el lote.` **(extra key, not in plan §0.2)** |

English mirrors are in `layers/dashboard/i18n/locales/en.json`; the E2E-relevant ones are
`Map`, `List`, `Plots`, `Active sensors`, `Air temperature`, `Solar radiation`, `No data`,
`Outdated`, `Basemap`, `Street`, `Satellite`, `No description`, `View plot`, `Farm map, {name}`,
`Plot {name}`, `Back to dashboard`, `Plot not found`.

### Two heads-up for selectors

1. **`Lote {name}` reads "Lote Lote La Colina"** on the detail page, because every seeded plot
   name already starts with `Lote`. This is the copy pinned in plan §0.2 and I did **not**
   change it — flagging it so the orchestrator can decide (the fix is one locale value:
   `dashboard.plotDetail.title` → `{name}`).
2. **`Reintentar` is not unique.** Both weather cards render their own Retry (one shared query,
   two visible failures), and the plots-error alert renders `farm.plots.retry` (also
   `Reintentar`). Scope Retry locators to the card/alert, or use `.first()`.

### DOM hooks shipped (plan §0.3, all verified in a real browser)

- `path[data-role="plot"]` — `data-plot-id`, `role="link"`, `tabindex="0"`,
  `aria-label`, `aria-describedby`
- `path[data-role="plot-casing"]` — `aria-hidden="true"`, no tabindex (same count as plots)
- `path[data-role="boundary"]` / `path[data-role="boundary-casing"]` — `aria-hidden="true"`
- `getByRole('region', { name: 'Mapa de la finca, <farm>' })`
- `getByRole('radiogroup', { name: 'Mapa base' })` with radios `Calles` / `Satélite`
- list rows: `[role="listitem"] > a[aria-label="<plot name>"]` inside `[role="list"]`

## Gotchas

- **`useDashboardViewMode` resolves storage only in `onMounted`.** Reading `localStorage`
  during setup would make the client pick a different tab than the SSR pass and produce a real
  hydration mismatch. Consequence: on a param-less `/dashboard` the map tab is rendered for one
  tick before `router.replace` writes the stored mode. Selectors should wait for the URL
  (`?view=list`) rather than assert immediately.
- **`setMode` is a no-op when the mode is unchanged**, so clicking the already-active tab does
  not write to `localStorage`. AC16 must be exercised by actually switching.
- **`:unmount-on-hide="false"`** means the map component stays mounted (and `hidden`) in list
  mode. A `ResizeObserver` on the map container calls `invalidateSize()` whenever the box
  regains a size — that covers the tab switch, the sidebar collapse and window resizes in one
  place, instead of a visibility prop.
- **Leaflet only realises a layer once the map has a view**, so the SVG `<path>` elements do not
  exist until after the first `fitBounds`/`setView`. All ARIA/`data-*` stamping therefore
  happens in `syncMap()` *after* the fit, never in `onEachFeature`. The map is created with a
  throwaway `center: [0,0], zoom: 2` for the same reason, and the first fit is non-animated.
- **Clicking a plot used to be swallowed** when the shape sat at the viewport edge: focusing an
  SVG path scrolls it fully into view, so the shape moved out from under the pointer between
  mousedown and mouseup and the `click` fired on the map container instead. Fixed with
  `mousedown → preventDefault() + element.focus({ preventScroll: true })`.
- **Touch:** `lastPointerType` is recorded on the container's capture-phase `pointerdown`. The
  first tap opens the card and returns before navigating; the browser's synthetic `mouseout`
  after a tap is ignored (`schedulePointerClose`) so the card survives long enough to reach
  "Ver lote".
- **Popover is `:dismissible="false"`** and fully controlled. Reka's own dismissal fires a
  `pointerdown`-outside on the *next* plot and would close the card the moment the user moved
  between shapes; Escape is handled on the path itself (`stopPropagation`, no blur) so focus
  stays put. `onOpenAutoFocus`/`onCloseAutoFocus` are both prevented.
- **`aria-describedby` points at one sr-only `<p>` per plot**, not at the popover content id.
  A single shared id would either dangle while the card is closed (axe risk) or lag a focus
  change by a tick.
- **No `aria-label` on `<UTabs>`.** Reka renders `TabsRoot` as a plain `<div>` with no role, so
  `aria-label` there is an `aria-prohibited-attr` violation. The tabs are wrapped in a
  `<section :aria-label="t('dashboard.view.label')">` instead.
- **Basemap selector lives at the top of the map panel**, not in the page section header — same
  requirement (outside `.leaflet-container`, keyboard-operable), better locality, and it
  disappears with the panel in list mode.
- **Pre-existing hydration mismatch** on every dashboard route, including `/dashboard/profile`
  which this feature does not touch. It originates in `DropDownUser` → `UDropdownMenu` in the
  dashboard layout. Not introduced here, not fixed here.
- **`@vue-leaflet/vue-leaflet` remains installed and unused** (raw Leaflet is used per the plan).
  It is removable, but I did **not** remove it — flagging for the orchestrator. Note that it was
  the only thing pulling in `@types/leaflet`, which is why that is now a direct devDependency.

## Contract deviations

None. Every field, type and nullability was consumed exactly as `contract.md` specifies —
`area_hectares` as a JSON string coerced with `Number(...)` before `Intl.NumberFormat`,
weather keys treated as absent-or-present with no null/zero handling, GeoJSON `[lng, lat]` fed
straight to `L.geoJSON()` with a single commented manual swap for the `Farm.location` fallback
`setView`. Verified live against the running backend (farms, plots, plot detail, weather all
matched the contract byte for byte, including `200 {}`-shaped absence for `solar_radiation` on
Finca San Vicente).

## AC self-check

Verified by driving the real app in headless Chromium against the running backend
(`localhost:3000` + `localhost:8000`, seeded `juan.perez@email.com`), plus `@axe-core/playwright`
scans. **No unit tests exist** — the orchestrator ruled Vitest out of scope for this feature.

| AC | Status | How |
| --- | --- | --- |
| AC1 | ✓ | 2 plot polygons drawn for Finca El Tesoro, distinct fill hue per plot, map fitted to them |
| AC2 | ✓ | `path[data-role="boundary"]` present for farm 1, dashed + own colour, distinct from plot strokes |
| AC3 | ✓ | Finca San Vicente: 0 boundary paths, 2 plot paths, no error, fitted to plots |
| AC4 | ✓ | hover and keyboard focus both open the card with name + description |
| AC5 | ✓ | `Sin descripción` rendered for plot 29 (empty `description`) in card, list and map label |
| AC6 | ✓ | mouse click, Enter on a focused path and "Ver lote" all land on `/dashboard/plots/<id>` |
| AC7 | ✓ | touch context: single tap opens the card and does **not** navigate; "Ver lote" then navigates |
| AC8 | ✓ | `1 lote no se muestra en el mapa` + a link named `Lote Sin Mapear` |
| AC9 | ⚠ partial | the `Farm.location` fallback and the `noLocation` empty state are implemented and reachable in code, but **no seeded farm can reach either branch** (all three farms have a location, and the only zero-geometry farm also has zero plots, so AC13 wins). Needs a seed with plots-but-no-geometry, or QA route-stubbing. |
| AC10 | ✓ | radiogroup switches CARTO ↔ Esri; attribution text updates; plot + casing paths unchanged |
| AC11 | ✓ | list rows show name · description · `11,12 ha` · sensor badge at `ms-auto` |
| AC12 | ✓ | row link navigates |
| AC13 | ✓ | Finca Sin Lotes → `Esta finca no tiene lotes.` in **both** panels |
| AC14 | ✓ | `?view=list` and `?view=map` both select on load |
| AC15 | ✓ | switching pushes `?view=`; Back returns to the previous mode |
| AC16 | ✓ | choose list, then open `/dashboard` → resolves to `?view=list` |
| AC17 | ✓ | cleared storage + no param → `?view=map` |
| AC18 | ✓ | 4 tiles with visible labels; units verbatim (`°C`, `W/m²`) from the response |
| AC19 | ✓ | Finca San Vicente solar radiation → `Sin datos` / `No data`, never `0`; count tiles unaffected |
| AC20 | ✓ | `Actualizado hace 16 minutos`, ticking every 30 s |
| AC21 | ✓ | farm 2 (95-min-old reading) shows `Desactualizada` / `Outdated` badge **with text** |
| AC22 | — | backend selection rule; frontend renders whatever the endpoint returns |
| AC23 | ✓ | switching farm in `FarmsMenu` re-renders map, list and all four cards for the new farm |
| AC24 | ⚠ not exercised | code path: farms loaded + no `selectedFarm` → `farm.plots.noFarm` only, stat cards/map/list not rendered, both queries stay disabled. The seeded user always owns farms, so QA needs a stubbed empty `farm/farms/` to confirm. |
| AC25 | ✓ | stubbed 500 on plots → `No se pudieron cargar los lotes.` + Retry in `role="alert"`; count tiles fall back to `Sin datos` |
| AC26 | ✓ | stubbed 500 on weather → both weather cards show error + Retry while counts, map and list keep rendering |
| AC27 | ✓ | detail page renders the record in `<pre><code>` inside the dashboard layout with a back link |
| AC28 | ✓ | direct `goto` of `/dashboard/plots/2` with a cold cache renders correctly |
| AC29 | ✓ | `/dashboard/plots/99999` → `Lote no encontrado` + body copy, no plot data in the DOM, no retry storm (404 short-circuits `retry`) |
| AC30 | ✓ | logged-out `/en/dashboard/plots/2` → `/en/login` (locale prefix preserved) |
| AC31–AC33 | — | backend slice |
| AC34 | ✓ | `/en/dashboard` and `/en/dashboard/plots/<id>` fully English incl. units, badges, empty and error states |

| A11y AC | Status | How |
| --- | --- | --- |
| AC-A11Y-1 | ✓ | axe `wcag2a/2aa/21aa/22aa`: **zero serious or critical** on `/dashboard` map, `/dashboard` list, satellite basemap, plots-error state, empty-farm state, 320 px viewport, `/en/dashboard`, `/dashboard/plots/<id>` and the not-found state |
| AC-A11Y-2 | ✓ | Reka `role="tablist"` + two `role="tab"` (`Mapa`/`Lista`), `aria-selected` flips, arrow keys and Enter/Space work, Nuxt UI focus ring intact |
| AC-A11Y-3 | ✓ | map tab order `[Lote El Abrevadero, Lote La Colina]` matches the list order; names are `"<name>, <description>, <n> sensores"`. Focus indicator is a 3 px `#facc15` `:focus-visible` outline **plus** a stroke-weight change — contrast against tiles/fill checked visually only, not measured |
| AC-A11Y-4 | ✓ | Enter and Space navigate; single mouse click and single tap both work; no drag/long-press/multi-point anywhere |
| AC-A11Y-5 | ✓ | same card on hover and focus; `aria-describedby` → per-plot sr-only description; card survives pointer travel (150 ms grace + `mouseenter` cancel); Escape closes and focus stays on the path (asserted) |
| AC-A11Y-6 | ✓ | `role="region"` named `Mapa de la finca, <farm>`, `aria-describedby` the visible alternative sentence; the tab list precedes the map in DOM order |
| AC-A11Y-7 | ⚠ partial | casing/core pairs ship on plots **and** boundary (`path[data-role="plot-casing"]` count equals plot count), boundary differs by dash pattern not hue, every plot carries a permanent halo'd name label. The **≥3:1 measurement against tiles** is not automatable and was not instrumented — needs a human greyscale check on both basemaps |
| AC-A11Y-8 | ✓ | one link per row named `<plot name>`, described by the rest of the row; sensor count is text in a badge; rows are `min-h-11` (44 px); `role="list"` + `role="listitem"` |
| AC-A11Y-9 | ✓ | every value preceded by its visible label and unit; `Sin datos` and `Desactualizada` are text, badge is `variant="subtle"` (no solid white-on-primary); axe contrast clean in the forced dark mode |
| AC-A11Y-10 | ✓ | every skeleton wrapper has `aria-busy="true"`; every error block is `role="alert"` with a keyboard-reachable `Reintentar`/`Retry`; the `<ClientOnly>` fallback is `role="status"` + `aria-busy` at the identical height |
| AC-A11Y-11 | ✓ | exactly **one** `<h1>` (the dashboard navbar title, repointed at the plot) matching `document.title`; dump is a `<pre tabindex="0" role="region" aria-label="Datos del lote">`; back link returns to the stored mode (verified: `?view=list`) |
| AC-A11Y-12 | ✓ | 320×720: `scrollWidth === clientWidth` (no horizontal scroll), axe clean. **200 % zoom at 1280 px not separately tested** |
| AC-A11Y-13 | ✓ | unmapped note lists `Lote Sin Mapear` as a link; it is also a list row |
| AC-A11Y-14 | ✓ | `radiogroup` named `Mapa base`, arrow-key operable, `aria-checked` on the active option |

## Decisions

- Raw Leaflet, dynamically imported inside `onMounted`, CSS imported inside
  `PlotsMap.client.vue` only. **Verified post-build:** `leaflet-container` appears in exactly one
  non-entry chunk (`.output/public/_nuxt/PlotsMap.*.css`, ~15 kB) and **zero times** in
  `entry.*.css`; the leaflet JS chunk is referenced by one lazily-loaded chunk.
- `@types/leaflet` promoted to a direct devDependency — we now import `leaflet` directly, so
  relying on `@vue-leaflet`'s transitive types would break the moment that dependency is dropped.
- Plot hue is decorative only (AC1); identification rests on the name label and stroke style.
- `UTable` rejected for the list (4 fields, one target per row) — `UPageList` + `ULink` per the plan.
- Out of scope: unit tests / Vitest setup (orchestrator ruling), any `e2e/` change (QA's slice),
  removing `@vue-leaflet/vue-leaflet`, the pre-existing `DropDownUser` hydration mismatch, and
  the pre-existing `I18n baseUrl is required` SSR warning.

## For next agent (QA)

Flow to exercise, default (Spanish) locale, seeded `juan.perez@email.com`:

1. `loginAs(page)` → `gotoHydrated(page, '/dashboard')` → URL settles on `?view=map`.
2. Stat cards: `Lotes` = `3`, `Sensores activos` = `4`, `Temperatura del aire` with `°C`,
   `Radiación solar` with `W/m²`, each with `Actualizado …`.
3. `page.getByRole('region', { name: 'Mapa de la finca, Finca El Tesoro' })`;
   `page.locator('path[data-role="plot"]')` → 2, `path[data-role="plot-casing"]` → 2,
   `path[data-role="boundary"]` → 1.
4. `page.getByRole('link', { name: /Lote La Colina/ })` resolves to the path. `.focus()` →
   `getByRole('link', { name: 'Ver lote' })` appears → `Escape` closes it and the path keeps
   focus → `Enter` navigates to `/dashboard/plots/<id>`.
   **Scroll the shape well inside the viewport before a raw `page.mouse.click`;** `locator.click()`
   is fine.
5. `getByRole('radiogroup', { name: 'Mapa base' })` → click `Satélite`: attribution text becomes
   the Esri string, `path[data-role="plot"]` still 2.
6. `1 lote no se muestra en el mapa` + link `Lote Sin Mapear` below the map.
7. Tab `Lista` → 3 `[role="listitem"]` rows; row link accessible name is exactly the plot name;
   URL becomes `?view=list`; Back returns to `?view=map`.
8. Switch to `Finca San Vicente` (reuse `farm.spec.ts`'s `selectFarm`): 0 boundary paths,
   2 plot paths, `Radiación solar` → `Sin datos`, `Temperatura del aire` → `Desactualizada`.
9. `Finca Sin Lotes` → `Esta finca no tiene lotes.` in both tabs.
10. `/dashboard/plots/<id>` direct load, `/dashboard/plots/99999` → `Lote no encontrado`,
    logged-out `/en/dashboard/plots/2` → `/en/login`.
11. `/en/dashboard` for AC34.

The dev server is left running on `http://localhost:3000`; log at
`…/scratchpad/frontend-dev.log`. After any frontend edit, warm one page before running the
suite — a cold Vite compile swallows pre-hydration clicks.

## Proposed improvements

Propose only — I did not edit any `CLAUDE.md`.

1. **`frontend/CLAUDE.md`** (map/HTTP rules) — also proposed by the contract author, worth
   keeping:
   > Backend geometry arrives as GeoJSON (`[lng, lat]`), the reverse of Leaflet's `LatLng` —
   > render it through `L.geoJSON()`, never by passing `coordinates` to `L.polygon`/`L.marker`.
2. **`frontend/CLAUDE.md`** (UI components) —
   > Never put `aria-label` on a Nuxt UI wrapper whose Reka root renders a plain `<div>`
   > (`UTabs`, `UPageGrid`, …): `aria-prohibited-attr` is a serious axe violation. Wrap the
   > component in a `<section :aria-label>` or a `role="group"` element instead.
3. **`frontend/CLAUDE.md`** (new "Third-party widgets that own their DOM" section) —
   > A library that builds its own DOM (Leaflet, chart libs) gets its CSS imported **inside** the
   > `.client.vue` component that uses it and its JS `await import()`ed in `onMounted` — never in
   > `nuxt.config.ts`'s `css: []`, which is the shared entry every SSR page pays for. Style its
   > generated nodes with `<style scoped>` + `:deep()`; they carry no scope attribute.
4. **`frontend/CLAUDE.md`** (Vue Query / SSR) —
   > Resolve `localStorage`-backed defaults in `onMounted` and `router.replace` the result into
   > the URL — reading storage during setup makes the client render a different tree than the
   > server and produces a real hydration mismatch.
5. **root `CLAUDE.md`** (Agent pipelines) —
   > When a slice changes user-facing copy, the handoff must list every string **added, renamed
   > and removed** with its i18n key, and name the selectors that break. That list, not the code,
   > is what the next agent actually consumes.
