# Acceptance criteria — Dashboard farm map, plot list, stat cards, plot detail placeholder

Slug: `2026-08-22-dashboard-farm-map-and-plots`

This is the **behaviour source of truth** for this feature. Every role verifies its work
against it: engineers self-check the criteria their slice owns, reviewers verify those
self-checks are honest, and QA signs off the full list end-to-end in `qa.md`.

The feature is **complete only when every criterion below is ✓**.

Context: [`spec.md`](spec.md) · [`contract.md`](contract.md) · [`discovery-ba.md`](discovery-ba.md) · [`discovery-ux.md`](discovery-ux.md)

---

## Functional

### Map view

- [ ] **AC1** — Given a farmer whose selected farm has plots with geometry, When they open
  `/dashboard`, Then a map is shown fitted to that farm's plots, with each plot drawn as a
  distinctly coloured shape.
- [ ] **AC2** — Given the selected farm has a `boundary` polygon, When the map renders, Then
  the farm boundary is drawn in a colour and stroke style distinct from the plots.
- [ ] **AC3** — Given the selected farm has no `boundary` polygon, When the map renders, Then
  no farm outline is drawn, the map is fitted to the plots instead, and no error appears.
- [ ] **AC4** — Given the map is shown, When the farmer hovers or keyboard-focuses a plot, Then
  an info card shows that plot's **name and description**.
- [ ] **AC5** — Given a plot has no description recorded, When its info card is shown, Then the
  description line shows an explicit "sin descripción" / "no description" message rather than
  being blank.
- [ ] **AC6** — Given the map is shown, When the farmer clicks a plot, presses Enter/Space on a
  focused plot, or taps "Ver lote" in the info card, Then they navigate to
  `/dashboard/plots/<that plot's id>`.
- [ ] **AC7** — Given the farmer is on a touch device, When they tap a plot shape once, Then the
  info card opens with a "Ver lote" action and they are **not** navigated away by that first tap.
- [ ] **AC8** — Given some plots of the farm have no geometry, When map mode renders, Then those
  plots are not drawn, and a visible note states how many plots could not be placed on the map
  and links to each of them by name.
- [ ] **AC9** — Given the farm has no plot geometries at all, When map mode renders, Then the map
  centres on `Farm.location`; and if that is also null, an explicit empty state is shown instead
  of a grey world map.
- [ ] **AC9b** — Given the map is shown, When a plot with geometry is drawn, Then a Google-Maps-style
  pin marker is visible **at rest**, before any hover or focus, anchored at the plot's `label_point`.
- [ ] **AC9c** — Given a plot with a **concave** outline (an L, a U, a crescent), When its pin and its
  permanent name label are drawn, Then both sit **inside** the plot polygon — never over adjacent land
  and never over a neighbouring plot. Neither may be anchored to `centroid` or to
  `getBounds().getCenter()`, both of which fall outside such a shape.
- [ ] **AC10** — Given the map is shown, When the farmer uses the basemap selector, Then the
  basemap switches between the muted street basemap and satellite imagery, the plot and boundary
  shapes remain drawn, and the required tile attribution for the active provider is visible.

### List view

- [ ] **AC11** — Given the dashboard is open, When the farmer activates the list tab, Then the
  same plots are shown as a list with, per row, the plot **name**, **description**, **area in
  hectares**, and the **number of active field sensors at the far end of the row**.
- [ ] **AC12** — Given list mode is shown, When the farmer activates a row, Then they navigate to
  that plot's detail page.
- [ ] **AC13** — Given the selected farm has no plots, When either view renders, Then an explicit
  empty state is shown (not a blank panel and not a zero-row list).

### View mode persistence

- [ ] **AC14** — Given the farmer opens `/dashboard?view=list`, When the page loads, Then list
  mode is active; and the same for `?view=map`.
- [ ] **AC15** — Given the farmer switches view mode, When the mode changes, Then the URL's `view`
  query parameter updates and the browser Back button returns to the previous mode.
- [ ] **AC16** — Given the farmer previously chose list mode, When they later open `/dashboard`
  with no `view` query parameter, Then list mode is restored from `localStorage`.
- [ ] **AC17** — Given a farmer who has never chosen a mode, When they open `/dashboard` with no
  `view` query parameter, Then map mode is active.

### Stat cards

- [ ] **AC18** — Given the dashboard is open, When the stat cards render, Then they show the
  farm's number of plots, its number of active field sensors, its air temperature and its solar
  radiation, each with a visible label and its unit.
- [ ] **AC19** — Given the farm has no weather station, or its stations have no readings, or a
  variable is not configured, When the stat cards render, Then the affected card shows an explicit
  "sin datos" state — never a zero, never an invented value, never a broken card — while the plot
  and sensor count cards still render normally.
- [ ] **AC20** — Given a weather reading exists, When its card renders, Then the age of the reading
  is shown alongside the value.
- [ ] **AC21** — Given a weather reading is older than 30 minutes, When its card renders, Then it is
  marked "desactualizada" / "outdated" with text (not colour alone) in addition to its age.
- [ ] **AC22** — Given the farm has more than one active weather station, When a weather card
  renders, Then it shows the most recent reading across all of them.

### Farm switching, errors, auth

- [ ] **AC23** — Given the farmer switches farm in `FarmsMenu`, When the dashboard reloads its data,
  Then the map refits, and the list and every stat card show the newly selected farm.
- [ ] **AC24** — Given the farmer has no farms at all, When they open `/dashboard`, Then the existing
  no-farm state is shown and neither the map, the list, nor the weather cards error.
- [ ] **AC25** — Given the plots request fails, When the dashboard renders, Then an error message and
  a Retry control are shown (text, not colour alone), and Retry refetches successfully.
- [ ] **AC26** — Given the weather request fails, When the dashboard renders, Then the weather cards
  show an error state with Retry **and the plot/sensor count cards, the map and the list still
  render** — one failing request does not take down the page.

### Plot detail placeholder

- [ ] **AC27** — Given the farmer opens `/dashboard/plots/<id>` for one of their own plots, When the
  page loads, Then the plot's data is rendered serialized inside a `<code>` block, within the
  dashboard layout, with a link back to the dashboard.
- [ ] **AC28** — Given the farmer navigates directly to `/dashboard/plots/<id>` (fresh load, refresh
  or bookmark — not arrived at by click), When the page loads, Then it renders the plot correctly,
  fetched from the plot detail endpoint.
- [ ] **AC29** — Given the farmer opens `/dashboard/plots/<id>` for a plot belonging to another
  farmer, or a non-existent id, When the page loads, Then a not-found state is shown and no plot
  data is revealed.
- [ ] **AC30** — Given an unauthenticated visitor, When they open `/dashboard/plots/<id>`, Then they
  are redirected to login, preserving the locale prefix.

### API

- [ ] **AC31** — Given an authenticated farmer, When `GET farm/farms/<id>/plots/` is called for their
  own farm, Then each plot includes `geometry` (GeoJSON or `null`), `centroid`, `area_hectares` and
  `sensor_count`.
- [ ] **AC32** — Given a farm with plots and sensors, When the plots endpoint is called, Then
  `sensor_count` counts **active sensors only** and the endpoint issues a **constant number of
  queries regardless of the plot count** (no N+1).
- [ ] **AC33** — Given a farmer calls any of the farm, plots, plot-detail or weather endpoints for a
  farm they do not own, When the request is made, Then it returns **404** (not an empty result, not
  a 403 that confirms existence).

### i18n

- [ ] **AC34** — Given the page is used in English (`/en/dashboard` and `/en/dashboard/plots/<id>`),
  When it renders, Then every label, tab name, empty state, error message, unit label and staleness
  badge is translated — no hardcoded Spanish.

---

## Accessibility

WCAG 2.2 AA. Verified with `@axe-core/playwright` plus explicit keyboard and focus assertions.
Carried over from [`discovery-ux.md`](discovery-ux.md); "crop" has been replaced by "description"
per the resolved decision in [`spec.md`](spec.md), and AC-A11Y-7 now covers both basemaps.

- [ ] **AC-A11Y-1** — Given the dashboard in either view mode, When `@axe-core/playwright` runs with
  `['wcag2a','wcag2aa','wcag21aa','wcag22aa']` on `/dashboard`, `/en/dashboard` and
  `/dashboard/plots/<id>`, Then there are zero serious or critical violations. *(backstop)*
- [ ] **AC-A11Y-2** — Given the map/list toggle, When I Tab to it, Then it receives a visible focus
  ring, exposes `role="tablist"` with two `role="tab"` items named "Mapa"/"Map" and "Lista"/"List",
  the active tab has `aria-selected="true"`, Left/Right arrows move between tabs, and Enter/Space
  activates the focused tab. *(2.1.1, 2.4.7, 4.1.2)*
- [ ] **AC-A11Y-3** — Given map mode, When I Tab through the map, Then each plot shape is focusable
  in the same order as the list, shows a focus indicator with ≥3:1 contrast against both its fill
  and the map tiles, and exposes an accessible name of the form
  "&lt;plot name&gt;, &lt;description&gt;, &lt;n&gt; sensors". *(2.1.1, 2.4.7, 2.4.11, 4.1.2)*
- [ ] **AC-A11Y-3b** — Given the map with pin markers drawn, When I Tab through it, Then each plot
  contributes **exactly one** tab stop and a screen reader announces each plot **once**: the pin is
  decorative (`aria-hidden`, not focusable, not an interactive Leaflet layer), the polygon remains the
  single interactive target, and a click on the pin still activates the plot beneath it.
  *(2.1.1, 4.1.2, 1.3.1)*
- [ ] **AC-A11Y-4** — Given a focused plot shape, When I press Enter or Space, Then I navigate to
  `/dashboard/plots/<id>`; the same action is available with a single tap on touch and a single
  click with a mouse, with no drag, long-press or multi-point gesture required anywhere.
  *(2.1.1, 2.5.1, 2.5.7)*
- [ ] **AC-A11Y-5** — Given a plot, When I hover it **or** move keyboard focus to it, Then the same
  info card appears; it is referenced by `aria-describedby` on the plot control so its text is
  announced, it stays visible while the pointer moves from the plot onto the card, and `Escape`
  dismisses it without moving focus. *(1.4.13, 4.1.2)*
- [ ] **AC-A11Y-6** — Given a screen reader, When I reach the map, Then it is a labelled region
  ("Mapa de la finca, &lt;farm name&gt;") whose content is also available as text, and the list view
  — reachable from the toggle that precedes the map in DOM order — is announced as the equivalent
  alternative. *(1.1.1, 1.3.1, 2.4.3)*
- [ ] **AC-A11Y-7** — Given the map rendered in greyscale (colour removed), **on both the street and
  the satellite basemap**, When I look at it, Then each plot is still identifiable by its visible
  name label, each shape is still distinguishable from the farm boundary by stroke style, and plot
  outlines hold ≥3:1 against the tiles beneath them (this is what the stroke casing is for).
  *(1.4.1, 1.4.11)*
- [ ] **AC-A11Y-8** — Given list mode, When I Tab through the rows, Then each row is a single link
  named "&lt;plot name&gt;", its sensor count is exposed as text (not an icon alone), its interactive
  target is ≥24×24 px, and the list is announced as a list with its item count.
  *(1.3.1, 2.5.8, 4.1.2)*
- [ ] **AC-A11Y-9** — Given the stat cards, When they render, Then each value is preceded by its
  visible text label and unit, no state is signalled by colour alone (an "Outdated"/"No data" text
  or badge accompanies any such state), and all text meets 4.5:1 (3:1 for the ≥24px value) in dark
  mode. *(1.4.1, 1.4.3)*
- [ ] **AC-A11Y-10** — Given any pending query on the page, When it is loading, Then the placeholder
  carries `aria-busy="true"`; When it fails, Then the error text plus a keyboard-reachable Retry
  button named "Reintentar"/"Retry" is announced through a live region. *(4.1.3, 1.4.1)*
- [ ] **AC-A11Y-11** — Given `/dashboard/plots/<id>`, When it loads, Then the document title and a
  single `<h1>` name the plot, the serialized dump is inside a labelled `<pre>`/`<code>` region that
  is keyboard-scrollable, and a "Volver al panel" / "Back to dashboard" link returns to the previous
  view mode. *(2.4.2, 2.4.6, 2.1.1)*
- [ ] **AC-A11Y-12** — Given a 320px-wide viewport (and 200% zoom at 1280px), When I view the
  dashboard, Then the stat cards, the toggle, the basemap selector, the map and the list all reflow
  with no two-dimensional scrolling and no clipped content or controls. *(1.4.4, 1.4.10)*
- [ ] **AC-A11Y-13** — Given a plot without geometry, When map mode renders, Then it is still
  reachable — listed by name with a link in the visible "not shown on the map" note — so no plot is
  available only to sighted users of the map. *(1.3.1, 2.4.3)*
- [ ] **AC-A11Y-14** — Given the basemap selector, When I Tab to it, Then it is keyboard-operable,
  has an accessible name, and its current basemap is programmatically exposed. *(2.1.1, 4.1.2)*
