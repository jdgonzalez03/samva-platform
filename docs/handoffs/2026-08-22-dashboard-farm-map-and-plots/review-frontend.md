# frontend review — Dashboard farm map, plot list, stat cards, plot detail

Slug: `2026-08-22-dashboard-farm-map-and-plots` · Reviewed against
[`contract.md`](contract.md) (verified against the **running** backend on `:8000`),
[`acceptance-criteria.md`](acceptance-criteria.md), [`plan.md`](plan.md),
[`frontend.md`](frontend.md), `frontend/CLAUDE.md`, `docs/ARCHITECTURE.md`, and the
`accessibility` / `nuxt-ui` / `vue-best-practices` skills.

Method: read every file named in the handoff, drove the running dev server on `:3000` in headless
Chromium (keyboard, mouse, real touch emulation, route stubbing, pixel-level contrast sampling,
`@axe-core/playwright`), queried the live API directly, and inspected the **real production build
output**. No `git` was run. No code was edited. Nothing under `e2e/` was touched. The dev server on
`:3000` is left running.

**Verdict: CHANGES REQUESTED** — 5 blocking, 8 non-blocking.

The slice is, on the whole, strong and unusually well-instrumented: the contract is consumed
exactly as written, the `[lng, lat]` trap is genuinely avoided (proved three ways below), Leaflet is
truly out of the shared entry, and axe is clean on every surface. The five blocking items are all
small, localised fixes — three of them are one line — but two of them (B2, B3) are AC self-check
claims that do not survive measurement, which is what makes them blocking rather than nits.

---

## Blocking

### B1 — `Lote {name}` renders "Lote Lote La Colina" as the page title *and* the only `<h1>`

- `frontend/layers/dashboard/i18n/locales/es.json:55` — `"title": "Lote {name}"`
- `frontend/layers/dashboard/i18n/locales/en.json:55` — `"title": "Plot {name}"`
- consumed at `frontend/layers/dashboard/app/pages/dashboard/plots/[id].vue:36-40` → `:61`
  (`useHead`) and `:69` (`UDashboardNavbar :title`)

**Confirmed live.** On `/dashboard/plots/1`: `document.title === "Lote Lote La Colina"` and the
page's single `<h1>` is the same string. On `/en/dashboard/plots/1`: `"Plot Lote La Colina"`. Every
seeded plot name already begins with `Lote`, so the prefix is duplicated on 100 % of real records,
in both locales, in the browser tab, the heading, and the accessible page name (AC-A11Y-11 requires
the title and the `<h1>` to *name the plot* — they currently name it wrong).

**Fix:** make the heading the bare plot name — set `"title": "{name}"` in **both** locale files. No
component change is needed; the interpolation, the `useHead`/`<h1>` pairing and the not-found
fallback all keep working. (If a prefix is ever wanted it belongs on the *label*, not baked into
the record's own name.)

---

### B2 — Plot focus indicator measures **1.17:1** against the default basemap; AC-A11Y-3 requires ≥3:1

`frontend/layers/dashboard/app/components/dashboard/PlotsMap.client.vue:504-507`

```css
:deep(path[data-role='plot']:focus-visible) {
  outline: 3px solid #facc15;
  outline-offset: 2px;
}
```

**Measured**, not eyeballed: focused a plot with a real `Tab` press (so `:focus-visible` applies),
clipped the shape's bounding box, and sampled the rendered pixels.

| basemap | ring colour | adjacent pixel outward (tiles) | ratio | adjacent pixel inward | ratio |
| --- | --- | --- | --- | --- | --- |
| **Calles (default)** | `rgb(250,204,21)` | `rgb(232,232,231)` | **1.17:1** ❌ | `rgb(248,250,252)` (own core stroke) | ~1.6:1 ❌ |
| Satélite | `rgb(250,204,21)` | `rgb(108,110,99)` | 3.39:1 ✓ | `rgb(248,250,252)` | ~1.6:1 ❌ |

**User-visible failure:** on the basemap the app ships as `DEFAULT_BASEMAP`, a keyboard user's focus
ring is a pale yellow line on near-white CARTO tiles — it does not reach the contrast the AC
demands, and the shape's own white core stroke gives it nothing to sit against either. This is
precisely the case `constants/map.ts:36-41` already argues about for the strokes ("a single stroke
colour cannot hold 3:1 against both muted street tiles and photographic satellite imagery") — the
argument was applied to the shapes and then not applied to the focus ring.

**Honesty note:** the AC self-check marks AC-A11Y-3 **✓** while its own "How" column says
"contrast against tiles/fill checked visually only, not measured". An AC that states a numeric
threshold cannot be ticked on a visual impression; it should have been ⚠ (as AC-A11Y-7 correctly
was). The measurement now shows it is not merely unverified — it is unmet.

**Fix:** give the focus ring the same casing/core treatment the shapes and the labels already have.
The cheapest version reuses the halo technique that measures 8.56:1 on `.samva-plot-label`:

```css
:deep(path[data-role='plot']:focus-visible) {
  outline: 3px solid #facc15;
  outline-offset: 2px;
  filter: drop-shadow(0 0 2px #0a0a0a) drop-shadow(0 0 1px #0a0a0a);
}
```

Then **re-measure** on both basemaps rather than re-eyeballing. (The existing stroke-weight change
`PLOT_CORE_WEIGHT → PLOT_ACTIVE_WEIGHT` is a good second channel and should stay.)

---

### B3 — "Volver al panel" points at the wrong view mode on a direct load / refresh / bookmark

`frontend/layers/dashboard/app/pages/dashboard/plots/[id].vue:42-47`, reading
`frontend/layers/dashboard/app/utils/view-mode.ts:12-15`

```ts
const backTo = computed(() =>
  localePath({ path: '/dashboard', query: { view: getStoredViewMode() ?? DEFAULT_VIEW_MODE } }),
)
```

`getStoredViewMode()` returns `null` on the server (correctly guarded by `import.meta.client`), so
SSR emits `view=map`. Vue **does not patch mismatched attributes during hydration**, so the
server's `href` survives on the client even though the computed would now evaluate to `list`.

**Measured** with `localStorage.dashboardViewMode === 'list'`:

| how the page was reached | `href` of "Volver al panel" |
| --- | --- |
| client-side click from the plot list | `/dashboard?view=list` ✓ |
| full page load of `/dashboard/plots/1` | `/dashboard?view=map` ✗ |

The raw SSR HTML confirms it: `href="/dashboard?view=map"`. Left-clicking still *ends up* on
`?view=list`, but only because `useDashboardViewMode`'s `onMounted` re-`replace`s the URL a tick
later — so the user sees a map flash, and **middle-click, ⌘/Ctrl-click, "open in new tab" and "copy
link address" all yield the wrong mode**, because a fresh load with `?view=map` present short-circuits
the storage lookup entirely.

**Honesty note:** the self-check marks AC-A11Y-11 ✓ with "back link returns to the stored mode
(verified: `?view=list`)". That holds only for the arrived-by-click path — the direct-load path is
exactly the one AC28 exists to protect, and it is the one that fails.

**Fix:** use the pattern the layer already established in `useDashboardViewMode` — resolve storage
after mount into a ref so the href is reactive and updates post-hydration:

```ts
const storedMode = ref<ViewMode>(DEFAULT_VIEW_MODE)
onMounted(() => { storedMode.value = getStoredViewMode() ?? DEFAULT_VIEW_MODE })
const backTo = computed(() => localePath({ path: '/dashboard', query: { view: storedMode.value } }))
```

---

### B4 — The tab panel is keyboard-focusable with no visible focus indicator (WCAG 2.2 AA, 2.4.7)

`frontend/layers/dashboard/app/pages/dashboard/index.vue:135-141` (`<UTabs>`)

Reka's `TabsContent` renders `tabindex="0"`, and Nuxt UI's default content class is
`focus:outline-none w-full`. Measured on the focused panel: `outline-style: none`,
`box-shadow: none` — nothing at all.

**Confirmed in the real Tab sequence** on `/dashboard?view=map`:

```
… → BUTTON "Mapa"  (outline: solid 2px ✓)
   → DIV  [role=tabpanel]  (outline: none, box-shadow: none)   ← focus vanishes here
   → BUTTON "Calles"  (outline: solid 2px ✓)
   → DIV  .leaflet-container  (outline: auto — UA default ✓)
   → path[data-role=plot] ×2  (outline: solid 3px #facc15 — see B2)
```

**User-visible failure:** a keyboard user tabbing from the "Mapa" tab into the map loses sight of
the focus position for one stop. AC-A11Y-2 only names the tabs themselves, and axe cannot detect
this, which is why it slipped through — but 2.4.7 applies to *any* keyboard-operable element, and
`<UTabs>` is new in this slice.

**Fix (one line):**

```vue
<UTabs
  …
  :ui="{ content: 'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary' }"
>
```

---

### B5 — The map's accessible names hardcode the plural: "…, 1 sensores" / "…, 1 sensors"

- `frontend/layers/dashboard/i18n/locales/es.json:39` — `"plotLabel": "{name}, {description}, {count} sensores"`
- `frontend/layers/dashboard/i18n/locales/en.json:39` — `"plotLabel": "{name}, {description}, {count} sensors"`
- consumed at `frontend/layers/dashboard/app/components/dashboard/PlotsMap.client.vue:175-183`

**Confirmed live** on `Lote El Abrevadero` (`sensor_count: 1`):

```
es: aria-label="Lote El Abrevadero, Lote cercano al abrevadero natural, 1 sensores"
en: aria-label="Lote El Abrevadero, Lote cercano al abrevadero natural, 1 sensors"
```

The correctly pluralised key sits ten lines below in the same file
(`dashboard.plots.sensors` = `"{count} sensor | {count} sensores"`) and is used by the list, the
info card **and the sr-only description attached to this very same `<path>`** — so a screen reader
announcing that shape says "1 sensores" (the name) and then "1 sensor" (the description) back to
back. It is a shipped grammatical defect in the only text AT users get for the map, with a
correct implementation already sitting next to it.

**Fix:** compose the name from the pluralised key instead of duplicating the noun —
message `"{name}, {description}, {sensors}"`, call
`t('dashboard.map.plotLabel', { name, description, sensors: t('dashboard.plots.sensors', count) })`.

---

## Non-blocking

### N1 — `Reintentar` ×3 with two different actions: an AT ambiguity, not an AA failure

`frontend/layers/dashboard/app/components/dashboard/WeatherStatCard.vue:57-65` and
`frontend/layers/dashboard/app/pages/dashboard/index.vue:121-129`

Assessed as asked. **Stubbing both endpoints to 500 simultaneously yields 3 buttons named exactly
`Reintentar`**, driving 2 distinct actions (two of them refetch the *same* weather query, the third
refetches plots).

It is **not** an AA failure: each button sits inside its own `role="alert"` immediately after its
own message, so 4.1.2 (name exists) and 2.4.6 (label describes purpose *in context*) hold;
"Link Purpose (Link Only)" — the SC that would fail on out-of-context ambiguity — is **AAA**.

It *is* a genuine screen-reader usability problem (a user navigating by button list gets three
identical entries and cannot tell which card each belongs to) and a real e2e-selector nuisance.
Worth fixing, but it does not gate the slice.

**Suggested fix:** `:aria-label="`${t('dashboard.retry')} — ${title}`"` on the weather retry and the
equivalent on the plots alert; the visible text stays `Reintentar`, which also keeps QA's `T` map
honest.

### N2 — `FarmWeather` throws away the type safety the contract offers; `WeatherSemanticKey` is dead code

`frontend/layers/farm/app/types/farm.ts:44` and `:50`

`WeatherSemanticKey` is declared and never referenced anywhere in the codebase, while
`FarmWeather = Partial<Record<string, WeatherReading>>` accepts any key — so
`weather?.solar_radiaton` type-checks and silently renders `Sin datos` forever. Contract §4 fixes
the two keys the UI consumes; use `Partial<Record<WeatherSemanticKey, WeatherReading>>` and let the
compiler catch the typo.

### N3 — Cross-layer doc drift: the sanctioned-exception list is now stale

`frontend/CLAUDE.md:12` and `docs/ARCHITECTURE.md:73-76` still enumerate the `farm → dashboard`
surface as `<FarmsMenu>` plus `useSelectedFarm`/`useFarmPlotsQuery`. This slice widened it with two
more auto-imported composables (`useFarmWeatherQuery`, `usePlotQuery`) and **six deep relative
type-only imports** of `../../../../farm/app/types/farm` (`plot-features.ts:2`,
`WeatherStatCard.vue:2`, `UnmappedPlotsNote.vue:2`, `PlotsList.vue:2`, `PlotsMap.client.vue:6`,
`PlotInfoCard.vue:2`). The imports are type-only and erased at build, so the **runtime** dependency
direction is intact and this is not an architecture violation — but neither doc was updated, and
`ARCHITECTURE.md`'s layer tree still does not list `farm/` at all. A stale allow-list is
indistinguishable from a violation at review time.

### N4 — The info card's "Ver lote" link is effectively pointer/touch-only

`PlotsMap.client.vue:461-488`. Verified: from a focused shape, `Tab` goes to the *next shape*; the
popover content is portalled to the end of `<body>`, so the link is only reachable after tabbing the
entire page — and by then the 150 ms `scheduleClose` timer has closed the card. No functional loss
(Enter/Space on the shape performs the same navigation — AC6 and AC-A11Y-4 both verified), and it is
what keeps the card from trapping focus. Worth one line of comment in the component so a future
reader does not "fix" the tab order and break AC-A11Y-5.

### N5 — `fitBounds` leaves the farm at ~55 % of the panel height

Deterministic across six runs (CSR and SSR entry alike): the 13-vertex boundary of *Finca El Tesoro*
renders 289×259 px inside a 976×520 panel, because Leaflet snaps to integer zoom (z15; z16 would
overflow the padded box). Correct behaviour, but a lot of dead map. `L.map(el, { zoomSnap: 0.25 })`
in `PlotsMap.client.vue:377` would tighten the fit with no other change. Cosmetic.

### N6 — Dead keys, dead export, dead dependency

- `farm.plots.count` and `farm.plots.title` (`layers/farm/i18n/locales/{es,en}.json`) are no longer
  referenced by any component.
- `getMappedPlots` (`plot-features.ts:16`) is exported but consumed only inside its own module.
- `@vue-leaflet/vue-leaflet` is still in `dependencies` and unused (the engineer flagged this —
  confirmed; it is the sole reason `@types/leaflet` had to be promoted to a direct devDependency,
  so removing it now is free).

### N7 — Hand-built DOM ids where every sibling uses `useId()`

`PlotsList.vue:31` / `:37` build `plot-row-${plot.id}` by hand, while `PlotsMap.client.vue:35`,
`UnmappedPlotsNote.vue:11` and `index.vue:35` all use `useId()`. Harmless today (one list per page),
inconsistent, and it silently breaks if the list is ever rendered twice.

### N8 — `usePlotQuery` triples the global retry budget as a side effect

`usePlotQuery.ts:18-19` replaces the client default `retry: 1` with `failureCount < 3` for every
non-404 failure. The comment only justifies the 404 short-circuit, so the widening reads as
accidental. If it was not intended: `retry: (n, e) => e.status !== 404 && n < 1`.

---

## Verified — the known issues, resolved

The five items surfaced by the orchestrator, confirmed / quantified / refuted:

1. **`Lote {name}` → "Lote Lote La Colina"** — **confirmed**, both locales, title *and* `<h1>`. See
   **B1** for the concrete fix (bare `{name}`).
2. **`Reintentar` not unique** — **quantified**: 3 buttons, 2 distinct actions, when both queries
   fail. **Not an AA failure** (the AAA SC is the one it would breach); it *is* a real AT ambiguity
   plus a selector nuisance. See **N1**.
3. **AC9 and AC24 unreachable with the seed** — **both code paths verified by stubbing**, so QA
   inherits a tested implementation:
   - AC9 (location fallback): stripped `boundary` from farm 1 and all `geometry` from its plots →
     the map centres at tile `z14/4819/7982`, which is **exactly** `Farm.location`
     `[-74.104, 4.596]` recomputed independently. The single hand-written `[lng,lat] → [lat,lng]`
     swap at `PlotsMap.client.vue:344-349` is correct.
   - AC9 (empty state): additionally stripping `location` → `Esta finca aún no tiene ubicación en el
     mapa.`, and **no Leaflet container is created at all** (no grey world map).
   - AC24: stubbed `farm/farms/` → `[]` → `Selecciona una finca para ver sus lotes.`, **zero** plots
     requests, **zero** weather requests, zero page errors.
4. **AC-A11Y-12 at 200 % zoom on 1280 px** — **verified** (the untested half). At 640×400 CSS px
   (= 1280×800 @ 200 %), map *and* list: `scrollWidth === clientWidth === 640`, no two-dimensional
   scrolling. Same at 320×720 and at 250 % zoom. The only overflow anywhere is inside
   `.leaflet-container`, i.e. the map's own pan surface.
5. **Hydration mismatch** — **confirmed pre-existing and unrelated, and not made worse.** The
   `PopperRoot`/`MenuRoot` mismatch (`DropDownUser` → `UDropdownMenu`) reproduces **identically** on
   `/dashboard/profile`, which this feature does not touch, and on `/dashboard` and
   `/dashboard/plots/1`. `/dashboard/profile` additionally carries `UForm` and `UContainer`
   mismatches that the two new routes do **not**. This slice introduced no new mismatch — notably,
   the deliberate `onMounted` deferral in `useDashboardViewMode` does its job.

## Verified — focus areas

**Contract fidelity, against the live API on `:8000`** (not against prose). Handoff's "Contract
deviations: None" is accurate.

- `area_hectares` is consumed as the **string** the wire carries — `PlotsList.vue:11-22` does
  `Number(...)` then `Intl.NumberFormat(locale)`, with a `Number.isNaN` guard and an em-dash for
  `null`. Renders `11,12 ha`, `4,94 ha`, `—` in `es-CO`; `11.12 ha` in `en`. No silent coercion, no
  mis-format, no `toFixed`.
- **Weather absent-key handling is correct and crash-free**: *Finca San Vicente* omits
  `solar_radiation` → `Sin datos` / `No data`, never `0`; *Finca Sin Lotes* returns literal
  `200 {}` → both weather cards render `Sin datos` while the count cards still render `0`, the map
  panel shows its empty state, no error anywhere. Units come verbatim from the payload (`°C`,
  `W/m²`) — nothing is hardcoded.
- **`[lng, lat]` vs `[lat, lng]` — plots really do land in the right place**, proved three ways
  rather than "the map rendered":
  1. Tile arithmetic: the fitted view resolves to lng ≈ −74.107, lat ≈ 4.609 (Bogotá), not the
     Indian Ocean.
  2. Relative geometry: in the data *El Abrevadero* is west **and** south of *La Colina*; on screen
     it renders left of and below it, and the 0.003°/0.002° extent ratio matches the measured
     140 px/93 px ratio to within 0.5 %.
  3. The one hand-written swap (`:344-349`) lands on the exact `Farm.location` tile (see above).
- `L.geoJSON()` is fed the backend objects unmodified (`plot-features.ts:22-42`), and the frontend
  does **no sorting of its own** — order is the backend's `['name']`.

**Vue / reactivity pitfalls**

- **`:unmount-on-hide="false"` stale-dimension trap: not present.** map → list → map returns the
  identical container size *and* identical path geometry; resizing 1280 → 900 re-lays the map out
  (804×480, tiles still loaded, paths repositioned) — the `ResizeObserver` `invalidateSize()` at
  `:400-411` genuinely fires. No grey tiles.
- **`UPopover` does not steal focus.** `.focus()` on a path opens the card and `document.activeElement`
  stays the path; `Escape` closes the card and focus **still** stays on the path
  (`data-role="plot"`). `onOpenAutoFocus`/`onCloseAutoFocus` prevention works as documented.
- **AC23 farm switching genuinely refits and refetches**: El Tesoro (2 plots, 1 boundary, tile
  `16/19277/31930`) → San Vicente (2 plots, **0** boundary, tile `16/19285/31939`, `Sin datos` for
  solar radiation) → Sin Lotes (0 plots, `Esta finca no tiene lotes.` in **both** panels, both
  weather cards `Sin datos`). Region label, stat cards, map and list all follow.
- `useQuery` bags are destructured in `<script setup>`; `refetch` is wrapped to return `void`; the
  `farmId` ref is in the query key (`[ROOT, PLOTS|WEATHER, farmId]`) so switching refetches with no
  watcher — all per `frontend/CLAUDE.md`.

**Leaflet is out of the shared entry — verified against the real build, not the import statement**

`npm run build`, then inspected `.output/`:

- `leaflet-container` appears in `_nuxt/PlotsMap.DGIwPHZ5.css` (15 kB) and **0 times** in
  `entry.Cd7DnPls.css`.
- The Leaflet JS lives in `_nuxt/CjPBq9Bq.js` (150 kB), referenced by exactly one chunk
  (`Ws95vXbR.js`, the lazy `PlotsMap` chunk).
- Served `.output/server` and fetched the pages: the **landing HTML contains no reference** to
  `CjPBq9Bq.js`, `Ws95vXbR.js` or `PlotsMap.*` — and neither does the `/dashboard` SSR HTML. The
  landing pays nothing.

**Accessibility, hands-on** (everything below measured in a browser, not inferred)

| Check | Result |
| --- | --- |
| axe `wcag2a/2aa/21aa/22aa` on `/dashboard?view=map`, `?view=list`, `/en/dashboard`, `/dashboard/plots/1`, `/dashboard/plots/99999` | **0 violations of any impact** on all five |
| Plot tab order vs list order | `Lote El Abrevadero` → `Lote La Colina` in both — matches the backend's alphabetical order; frontend sorts nothing |
| Enter / Space on a focused shape | both navigate to `/dashboard/plots/2` |
| Hover **and** focus open the info card | both do; card survives pointer travel |
| `Escape` | closes the card, focus stays on the path |
| Touch (390×844, `hasTouch`) | one tap opens the card and does **not** navigate; "Ver lote" (232×32) then navigates — AC7 ✓ |
| Tablist | `role="tablist"` + 2 `role="tab"`, `aria-selected` flips, ArrowLeft/Right move **and** activate **and** push `?view=` |
| List | `role="list"` named `Lotes de la finca`, 3 `role="listitem"`, one link per row named exactly the plot name, rows 976×**48** px |
| Basemap selector | `role="radiogroup"` named `Mapa base`, `aria-checked` flips, `<label>` click works, Esri attribution appears, plots/casings/boundary all survive the swap |
| Target size (2.5.8) | radios are 16×16 with a separate clickable 40×20 / 50×20 `<label>` — **passes via the spacing exception** (24 px circles on the undersized targets do not intersect: radio centres 80 px apart, nearest label starts 8 px beyond the 12 px radius). Unmapped-note links 24 px tall ✓ |
| Reflow (1.4.4 / 1.4.10) | no 2-D scrolling at 320×720, at 200 % zoom on 1280, or at 250 % — see item 4 above |
| Plot **label** contrast (the unmeasured half of AC-A11Y-7) | glyph `#ffffff` vs darkest halo pixel `rgb(17,17,17)` = **18.9:1**; p5/p95 = **8.56:1**. Passes comfortably |
| Plot **stroke** contrast vs tiles (AC-A11Y-7) | passes **by construction**: no tile luminance can be within 3:1 of *both* `#0a0a0a` and `#f8fafc` (that would need L < 0.111 **and** L > 0.3). Only the human greyscale eyeball remains |
| Skeletons / errors | every skeleton wrapper has `aria-busy="true"`; every error block is `role="alert"` with a keyboard-reachable Retry; `<ClientOnly>` fallback is `role="status" aria-busy` at the identical height |
| Errors do not cascade | weather 500 → both weather cards error, map still draws 2 plots, counts intact. Plots 500 → alert + Retry, weather cards keep their values, counts fall back to `Sin datos` |

**i18n**

- `es.json` and `en.json` are **key-for-key identical**: 43 keys each, empty symmetric difference in
  both directions. 31 new keys under `view`/`stats`/`map`/`plots`/`plotDetail` — matches the
  handoff's count exactly. `dashboard.index.welcome` is gone from both.
- Every `t()` key used by the `dashboard` and `farm` layers resolves; `dashboard.retry` (used by the
  new weather card and detail page but absent from the handoff's table) is **pre-existing** — it was
  already consumed by `layouts/dashboard.vue:103`.
- No hardcoded Spanish on the new surfaces: `/en/dashboard` and `/en/dashboard/plots/1` render fully
  in English including units, `Outdated`, `No data`, `No description`, `Plot not found`. Switching
  locale in-app re-stamps the SVG `aria-label`s correctly. Correct per-layer namespace throughout.

**`frontend/CLAUDE.md` compliance**

`U`-prefixed components only; Lucide icons only; both pages set `useHead({ title })`; all HTTP
through `farmApi` → `fetcher` (no `$fetch`/`useFetch` anywhere in the slice); query keys from
`FarmQueryKey`, hierarchical; per-query `<x>QueryOptions()` factories with plain objects + `as const`;
`import.meta.client` guards on every `localStorage` touch; `useLocalePath()` on every `to`/`navigateTo`;
`useState` for the selected farm; **all composable/util functions are arrow functions**; `imports.dirs`
resolved with `fileURLToPath(new URL(...))`. Comments are *why*-only — no change narration, no
references to code that no longer exists.

**Reachability** — every new view is reachable by a visible link: `/dashboard/plots/<id>` from a map
polygon, from "Ver lote", from any list row, and from the unmapped-plots note (which is the only
route to `Lote Sin Mapear` in map mode — AC-A11Y-13 ✓). No orphan routes.

**Gates**

`npm run lint` ✓ · `npm run format:check` ✓ · `npm run typecheck` ✓ · `npm run build` ✓.
Per the orchestrator's ruling there is **no test runner** in `frontend/`, so the usual coverage gate
does not apply to this slice; see *Proposed improvements* #9.

## AC self-check audit

The self-check is **mostly honest and unusually detailed** — AC9, AC24 and AC-A11Y-7 are correctly
marked ⚠ with accurate reasons, the AC-A11Y-12 caveat is stated outright, and the "Contract
deviations: None" claim survives byte-level comparison with the live API. Two claims do not hold:

| AC | Claimed | Reality |
| --- | --- | --- |
| **AC-A11Y-3** | ✓ | **Overstated.** The AC states a numeric threshold (≥3:1); the "How" column admits it was "checked visually only, not measured". Measured: **1.17:1** against the default basemap. → **B2** |
| **AC-A11Y-11** | ✓ ("verified: `?view=list`") | **Overstated.** True only when the page is reached by a client-side click. On a direct load — the path AC28 exists for — the href is the SSR default. → **B3** |

Everything else in both tables reproduces as claimed.

---

## Proposed improvements

Proposed only — I edited no `CLAUDE.md` and no agent spec. Each is reusable and long-term; I checked
each against the current text to avoid duplicating an existing rule.

1. **`frontend/CLAUDE.md` → SSR** *(new; generalises B3 and the engineer's own view-mode gotcha into
   one rule, so the two are not learned twice)*
   > A `computed` that reads `localStorage` renders the **server's** fallback and then never
   > updates — Vue does not patch mismatched attributes during hydration. Resolve storage-backed
   > values into a `ref` inside `onMounted` and derive the template from that ref; an
   > `import.meta.client` guard prevents the crash, not the stale value.

2. **`frontend/CLAUDE.md` → i18n** *(new; B5)*
   > Never hardcode a plural next to an interpolated count. Use the `singular | plural` form with
   > `t(key, count)`, and when a longer message embeds a count, compose it from the pluralised key
   > rather than repeating the noun inline.

3. **`frontend/CLAUDE.md` → Accessibility / UI** *(new; B2)*
   > A focus indicator drawn over third-party imagery needs the same casing/core pair as the shapes
   > it marks — no single hue holds 3:1 against both a light street basemap and satellite tiles.
   > Pair the bright ring with a dark halo, and **measure** the ratio; an AC that names a number may
   > never be self-checked on a visual impression.

4. **`frontend/CLAUDE.md` → Layers & file placement** *(new; N3)*
   > When a slice widens the sanctioned cross-layer surface, update the exception list in
   > `frontend/CLAUDE.md` **and** `docs/ARCHITECTURE.md` in the same change — a stale allow-list is
   > indistinguishable from a violation at review time.

5. **`.claude/agents/frontend-engineer` spec** *(new; the pattern behind both honesty findings)*
   > Mark an AC ✓ only for the path you actually exercised. A criterion with a measurable threshold
   > (contrast ratio, px, ms) requires a measurement; a criterion about a link or a page state
   > requires exercising **both** the client-side-navigation and the full-page-load path. Otherwise
   > mark it ⚠ and say which path is untested.

6–8. **Endorsed as-is from the engineer's own list** (all three verified true during this review, so
   they are worth writing down rather than re-deriving): the `[lng, lat]` → `L.geoJSON()` rule; the
   "no `aria-label` on a Reka root that renders a plain `<div>`" rule; and the "third-party widgets
   that own their DOM get their CSS imported inside the `.client.vue` and their JS `await import()`ed
   in `onMounted`" rule — the build output confirms the last one keeps the landing page clean.

9. **`frontend/CLAUDE.md` → Tests** *(raised as a proposal per the orchestrator's ruling, not as a
   finding)*
   > This slice added ~1 400 lines of frontend logic — coordinate transforms, plural/locale
   > formatting, storage/URL reconciliation, staleness thresholds — with **no test runner in
   > `frontend/`**. Three of the five blocking findings above (B1, B3, B5) are the kind a
   > three-line unit test on `plot-features.ts`, `view-mode.ts` and the locale files would have
   > caught before review. Recommend standing up Vitest for the pure `utils/` and `composables/`
   > modules as its own follow-up slice, and adding the rule *"every `layers/*/app/utils` module
   > ships a `.spec.ts`"* once it exists.
