# ba discovery — dashboard farm map, plot list, stat cards, plot detail placeholder

Summary: Analysed turning the `/dashboard` placeholder into the real farm home
(map + list toggle of plots, farm-level stat cards, `/dashboard/plots/[id]` stub).
The UI work is well-supported by what exists; the real cost is in **four data gaps**
(crop, farm boundary, plot address, any sensors API at all) that the description
assumes are already there and are not.

## Value / who benefits

The farmer, on the page they land on after login. Today `/dashboard` shows one card
with a plot count — the platform collects sensor data and shows almost none of it.
This is the first screen that makes S.A.M.V.A. look like the product `docs/ARCHITECTURE.md`
describes, and it is already the top item under "Planned" there. Building it is right.

## What already exists (reuse, don't rebuild)

- `frontend/layers/farm/`: `useFarmsQuery`, `useFarmPlotsQuery`, `useSelectedFarm`
  (persisted farm choice), `FarmsMenu.vue`. The map, the list and the stat cards should
  all read **one** plots query — extend `PlotSerializer`, don't add a second plot endpoint
  that forks the cache.
- `backend/farm/api.py`: owner-scoped list endpoints with the correct 404-not-empty-list
  security posture. Reuse the `owner__user=request.user` lookup pattern for the new
  plot-detail endpoint.
- `leaflet`, `@vue-leaflet/vue-leaflet`, `@unovis/*` are installed but **never imported
  anywhere yet** (grep: zero references, Leaflet's CSS is not loaded). This is the app's
  first map.
- `frontend/layers/dashboard/app/components/dashboard/FarmStats.vue` renders **four
  random fake values** (temperature, humidity, soil pH, solar radiation) and is not used
  by any page. Two of its four cards (humidity, **pH**) have no data source in the
  backend at all — there is no `soil_ph` semantic key. This component should be
  **replaced and its fake values deleted**, not "wired up": half of it cannot be.

## Data-model gaps and what each costs

**1. Crop (`cultivo`) — does not exist.** No field on `Plot`, no `Crop` model anywhere.
The feature only needs to *display a crop name* in a tooltip and a list cell.
- Cheapest: `crop = CharField(max_length=100, blank=True)` on `Plot` + one Wagtail panel
  line + fixture values. One migration, no admin CRUD, no new snippet.
- Corner-painting check: promoting a `CharField` to a foreign key (FK — a pointer from
  one table row to another) later is a routine data migration (match rows by name). It is
  not a trap.
- When the FK *is* worth it now: if the `predictions` app (fuzzy-logic irrigation) will
  soon need per-crop parameters — water need, thresholds — then crops must be real rows
  an admin edits in Wagtail, and doing it twice is wasteful.
- "One crop or a history?" A planting history (crop + sowing date + harvest date, rotation
  across seasons) is a **separate feature**, not a field. It changes the tooltip from
  "the crop" to "the current planting". Out of scope here; the choice above should just
  not block it.
- Recommendation: **CharField now**, unless the answer to Q1 is that predictions-per-crop
  is next up.

**2. Farm boundary polygon — does not exist.** `Farm` has only a nullable `location`
point. Three options:
- (a) Add `boundary = PolygonField(null=True, blank=True)` to `Farm`, drawn by the admin
  in the same Leaflet panel workflow already used for `Plot.geometry`. Cost: one
  migration, one panel entry, polygons in the fixture for the 12 seeded farms, and a
  one-time drawing chore per farm forever. Benefit: the line on the map is **true**.
- (b) Derive it on the fly from the union/convex hull of the farm's plots. Cost: zero
  schema. But it is a fabricated shape shown in the position where users read a property
  line; with one plot the hull equals the plot (visually pointless), with scattered plots
  it swallows land that is not the farm's. **This is wrong data presented as fact — do
  not do it.**
- (c) No boundary at all; fit the map viewport to the plots.
- Recommendation: **(a) with (c) as the automatic fallback** when `boundary` is null. The
  user explicitly asked for a highlighted farm boundary, so (a) honours the ask honestly;
  (c) is needed anyway because the field is nullable and farms will exist without it.

**3. Plot address for list mode — does not exist.** Only `Farm` has `address`. Showing the
farm address on every row repeats the identical string down the column — noise, not
information. `Plot.area_hectares` is already auto-computed per plot and is genuinely
per-row. Recommendation: **column = name · crop · area (ha) · sensor count**, and add a
real `Plot.address` only if plots are legally/postally distinct (Q3).

**4. Weather values — the `sensors` app has no API whatsoever.** Confirmed: no `api.py`,
no `serializers.py`, no `urls.py` under `backend/sensors/`, and **no fixtures** (only
`accounts`, `farmer`, `farm` have any). So the stat cards need a new endpoint *and* seed
data, or the feature cannot be demoed or e2e-tested.
- Cheapest correct shape: the plots endpoint gains `sensor_count` per plot (one
  `annotate(Count(...))`), so **"number of plots" and "number of sensors" need no new
  endpoint at all** — the page already has the list. Only weather is new: one small
  `GET .../latest-weather/` returning, per `semantic_key`, `{ value, unit, recorded_at }`
  from the newest snapshot of the farm's active station(s).
- No station / no snapshot / missing variable → the key is simply absent; the card renders
  an explicit empty state ("Sin datos"), never a zero and never a random number.
- Staleness, cheapest correct behaviour: **always render the reading's relative timestamp**
  ("hace 7 min"). It is self-documenting, needs no configurable threshold, and degrades
  gracefully. A "stale" badge can key off the station's own `polling_interval_minutes`
  later; it is not needed for correctness (Q5).
- Fixture wrinkle: a seeded `WeatherSnapshot.recorded_at` is a frozen date, so in dev the
  card will always read "hace 7 meses". Decide between a relative-timestamp seeding
  command and simply accepting it in dev (Q6).

**5. Plots without geometry.** `Plot.geometry` is nullable, though all 28 seeded plots do
have polygons. Rule needed so they are not silently invisible: map mode draws only plots
with geometry and shows a count of the ones it could not place; list mode always shows
every plot. Farm with zero plot geometries → fall back to centring on `Farm.location`;
if that is null too, show an empty-state card instead of a grey world map.

## Surfaces & routes implied (decisions needed on each)

| Surface / route | Decision |
| --- | --- |
| `/dashboard` (index) | Which mode is the default, map or list? Is the choice persisted per user like the selected farm? (Q7) |
| `/dashboard/plots/[id]` | Placeholder `<code>` dump. Needs `auth` middleware + dashboard layout + a back link, and a **new owner-scoped detail endpoint** (`farm/plots/<id>/`) — a plot of another farmer must 404, exactly as farms do today. |
| `/dashboard/plots` (parent) | Does not exist. A user editing the URL hits the 404 page. Acceptable, or add a plots index? (Q8) |
| Sidebar nav (`layouts/dashboard.vue`) | Today only Dashboard + Perfil. Add a "Lotes" entry? (Q8) |
| Farm switcher (`FarmsMenu`) | Switching farms must refit the map, refetch plots and stats. Confirm this is the expected behaviour. |
| Row / polygon → detail | Both list rows and map polygons should navigate to the detail page (the map must not be the only route in — see a11y below). |
| i18n (es/en) | Every new string needs both locales. Which layer owns them: plot map/list in `farm`, weather cards in a new `sensors` layer (ARCHITECTURE says new domains are born as layers), page composition in `dashboard`. (Q9) |
| e2e | `e2e/frontend/dashboard.spec.ts` and `a11y.spec.ts` already exist and will both need to cover this page. |

## Cheaper alternatives considered

- **Derive stat cards from data already on the page** rather than a summary endpoint —
  **take it** (see gap 4). Removes an entire endpoint.
- **Extend `PlotSerializer` instead of a new GeoJSON endpoint** — **take it**. One query,
  one cache entry, one loading state.
- **Skip `djangorestframework-gis`** (not currently installed): for read-only output,
  `json.loads(plot.geometry.geojson)` in a `SerializerMethodField` is two lines. Per the
  build-vs-reuse rule in `CLAUDE.md`, the library only earns a dependency when we accept
  geometry *writes* over the API, which we don't. Surfacing rather than deciding (Q10).
- **List first, map second.** The list + stat cards + detail stub need no new frontend
  dependency, no SSR handling and no boundary decision; they are most of the daily value.
  The map is the differentiator and should still ship — this is **sequencing advice on an
  explicitly requested feature, not a scope cut**: if the work is time-boxed, land list +
  cards + detail as stage 1 and the map as stage 2, each leaving tests green.
- **Not recommended:** deriving the farm boundary from a convex hull (option 2b) — cheap
  but dishonest.

## Risks / concerns

- **N+1 queries** on per-plot sensor counts: must be a single
  `annotate(Count('field_sensors', filter=Q(is_active=True)))`, not a loop. Also decide
  active-only vs all sensors for the displayed count (Q4).
- **Leaflet + SSR**: Leaflet touches `window` at import time. The map must be client-only
  (`<ClientOnly>` / `.client.vue` + dynamic import) and its CSS added to the owning layer —
  no Leaflet CSS is loaded anywhere today. Keep it out of the shared entry bundle so the
  landing page does not pay for it.
- **Payload size**: seeded polygons are 5 points and trivial, but real hand-drawn
  boundaries can be large. Ship geometry inline on the plots response and revisit only if
  it actually grows — no vector tiles, no simplification, yet.
- **Fake data going live**: `FarmStats.vue`'s pH and humidity cards have no backend source.
  Shipping them "looking real" would mislead a farmer about their field. Delete them.
- **Accessibility**: an SVG polygon map is not keyboard- or screen-reader-navigable. The
  list mode is the accessible equivalent — the toggle must be keyboard-reachable, hover
  tooltips must have a focus equivalent, and no plot may be reachable *only* by clicking
  the map. `a11y.spec.ts` should cover both modes.
- **Empty demo**: with no `sensors` fixtures, every reviewer and every e2e run sees empty
  sensor counts and empty weather cards. Seed data is part of this feature, not a follow-up.

## Recommendation

**Proceed**, with the scope discipline above: crop as a plain `CharField` (unless Q1 says
otherwise), a real nullable `Farm.boundary` with fit-to-plots fallback (never a convex
hull), area-in-hectares instead of a per-plot address, `FarmStats.vue`'s invented pH and
humidity deleted rather than migrated, `sensors` fixtures added as part of the work, and
stat-card counts derived from the plots response instead of a new summary endpoint.

## Open questions

1. **Crop model shape.** Plain text field on the plot (cheapest, recommended default), or a
   real `Crop` entity managed in the Wagtail admin? Choose the entity only if the
   predictions/irrigation feature will soon need per-crop parameters. Is that next up?
2. **Farm boundary.** Confirm option (a): add a `boundary` polygon to `Farm` that you draw
   in the admin per farm, falling back to auto-fitting the map around the plots when it is
   empty. (Recommended default: yes.)
3. **Plot address.** Is the "address" column satisfied by area in hectares (recommended
   default), or do plots genuinely need their own address field the admin fills in?
4. **Sensor count.** Should the number shown per plot and in the stat card count *active*
   sensors only, or all installed sensors? (Recommended default: active only.)
5. **Staleness.** Is showing the reading's age ("hace 7 min") enough (recommended default),
   or do you want an explicit "outdated" warning badge past some threshold? Also: if a farm
   has more than one active weather station, take the most recent reading across all of
   them, or nominate a primary station?
6. **Seed data.** Should the seeded weather reading always look recent (a small command
   that stamps it "now") or is a fixed old timestamp in dev acceptable?
7. **Default view mode.** Does `/dashboard` open in map mode or list mode, and should the
   user's choice be remembered between visits (like the selected farm)? (Recommended
   default: map by default, remembered.)
8. **Routes/nav.** Do you want a "Lotes" entry in the dashboard sidebar and a
   `/dashboard/plots` index listing, or is the detail page reachable only from the
   dashboard? (Recommended default: no new sidebar entry and no index route for now.)
9. **Layer ownership.** Create a new `sensors` frontend layer for the weather cards (matches
   the architecture rule that new domains are born as layers, recommended default), or keep
   them inside `dashboard`?
10. **GeoJSON dependency.** Serialize geometry by hand — two lines, no new dependency
    (recommended default) — or add `djangorestframework-gis` now in anticipation of editing
    plot boundaries through the API later?
11. **Detail placeholder.** Should `/dashboard/plots/[id]` dump exactly the same fields the
    dashboard already has, or should it fetch the full plot record (including geometry and
    description) so the later real page has its endpoint ready? (Recommended default: the
    full record.)

## Proposed acceptance criteria

1. Given a farmer with a selected farm whose plots have boundaries, When they open
   `/dashboard`, Then a map is shown fitted to that farm's plots, with each plot drawn as a
   coloured shape.
2. Given the selected farm has a boundary polygon, When the map renders, Then the farm
   boundary is drawn in a distinct colour from the plots. *(Depends on Q2.)*
3. Given the selected farm has no boundary polygon, When the map renders, Then no farm
   outline is drawn and the map is fitted to the plots instead, with no error.
4. Given the map is shown, When the farmer hovers or keyboard-focuses a plot, Then a small
   card shows that plot's name and crop.
5. Given a plot has no crop recorded, When its card is shown, Then the crop line reads an
   explicit "not recorded" message rather than being blank or showing a placeholder value.
6. Given the map is shown, When the farmer activates a plot, Then they navigate to
   `/dashboard/plots/<that plot's id>`.
7. Given some plots of the farm have no boundary recorded, When map mode renders, Then those
   plots are not drawn and the page states how many plots could not be placed on the map.
8. Given the farm has no plot boundaries at all, When map mode renders, Then the map centres
   on the farm location, or an explicit empty state is shown if the farm has no location.
9. Given the dashboard is open, When the farmer activates the view toggle, Then the same
   plots are shown as a list with, per row, name, crop, area, and the number of field
   sensors at the end of the row. *(Column set depends on Q3/Q4.)*
10. Given the farmer switched view mode, When they return to `/dashboard` later, Then their
    chosen mode is still selected. *(Depends on Q7.)*
11. Given list mode is shown, When the farmer activates a row, Then they navigate to that
    plot's detail page.
12. Given the dashboard is open, When the stat cards render, Then they show the farm's number
    of plots, number of field sensors, air temperature and solar radiation with their units.
13. Given the farm has no weather station, or the station has no readings yet, When the stat
    cards render, Then the affected cards show an explicit "no data" state — never a zero,
    an invented value, or a broken card — while the plot and sensor counts still render.
14. Given a weather reading exists, When its card renders, Then the age of the reading is
    shown alongside the value. *(Wording/badge depends on Q5.)*
15. Given the farmer switches farm in the sidebar switcher, When the dashboard reloads its
    data, Then the map, the list and every stat card show the newly selected farm.
16. Given the plots request fails, When the dashboard renders, Then an error message and a
    Retry control are shown (text, not colour alone), and Retry refetches.
17. Given the farmer opens `/dashboard/plots/<id>` for one of their own plots, When the page
    loads, Then the plot's data is rendered inside a `<code>` block, within the dashboard
    layout, with a way back to the dashboard.
18. Given the farmer opens `/dashboard/plots/<id>` for a plot belonging to another farmer,
    or a non-existent id, When the page loads, Then a not-found state is shown and no plot
    data is revealed.
19. Given an unauthenticated visitor, When they open `/dashboard/plots/<id>`, Then they are
    redirected to login, preserving the locale prefix.
20. Given the page is used in English (`/en/dashboard`), When it renders, Then every label,
    empty state and error message is translated — no hardcoded Spanish.
21. Given either view mode is active, When the automated accessibility check runs, Then there
    are no violations, the mode toggle is keyboard-operable, and every plot is reachable
    without using the map.

## Proposed improvements

- Rule for `frontend/CLAUDE.md`: "Never render invented, random or hardcoded stand-in values
  as if they were real data — a surface with no data source ships as an explicit empty state
  or not at all." (`FarmStats.vue` shipped four random numbers, two of which can never have a
  backend source; the rule prevents the recurrence.)
- Refinement of the existing browser-API rule in `frontend/CLAUDE.md` (line 29): extend it
  from browser *APIs* to browser-only *libraries* — components wrapping them (Leaflet) must
  be client-only and dynamically imported so they never enter the shared bundle.
