# frontend handoff — Weather stations
Summary: The home dashboard now shows one card per station of the selected farm. These cards replace the two old weather stat cards. A new sidebar entry "Estaciones" opens `/dashboard/stations` (the list) and `/dashboard/stations/<id>` (detail: conditions, 24 h/7 d/30 d charts, paginated readings, CSV/JSON export, and a not-found state). All of these use the live refresh from the history page.

Files changed:
- farm: `app/types/farm.ts`, `app/utils/api/farm.ts`, `app/constants/query-keys.ts`, `app/constants/stations.ts` (new), `app/composables/useFarmStationsQuery.ts` (new), `app/composables/useFarmWeatherQuery.ts` (deleted), `app/components/station/{Card,StatusBadge,Sparkline.client}.vue` (new), `i18n/locales/{es,en}.json`
- sensors: `app/types/sensors.ts`, `app/utils/api/sensors.ts`, `app/constants/query-keys.ts`, `app/utils/station-filters.ts` (new), `app/utils/history-export.ts`, `app/composables/{useStationQuery,useStationSeriesQuery,useStationReadingsQuery,useStationFilters}.ts` (new), `app/composables/useHistoryExport.ts`, `app/components/sensors/{HistoryTable,HistoryChartGrid}.vue`, `app/pages/dashboard/history.vue`, `app/pages/dashboard/stations/{index,[id]}.vue` (new), `i18n/locales/{es,en}.json`
- dashboard: `app/pages/dashboard/index.vue`, `app/layouts/dashboard.vue`, `i18n/locales/{es,en}.json`, deleted `app/components/dashboard/WeatherStatCard.vue` and `app/constants/weather.ts`
- e2e: `e2e/frontend/stations.spec.ts` (new), `dashboard.spec.ts`, `farm.spec.ts` (comment only), `helpers.ts` (T strings, `STUB_STATIONS`, `stubStationCard`, `stubStations`)
- `docs/ARCHITECTURE.md`

Routes/UI:
- `/dashboard/stations` (sidebar "Estaciones", after "Mis sensores", `i-lucide-cloud-sun`). The home "Estaciones meteorológicas" section also has a "Ver todas" link.
- `/dashboard/stations/<id>`: open it from "Ver detalle" on any card. The accessible name is "Ver detalle de <station>".

Gotchas:
- Dependency direction: the station list API, query, `WeatherStation` types and the card components live in **farm**, because dashboard may not import from sensors. Sensors keeps detail, series, readings and export. The new farm edges (`<StationCard>`, `<StationStatusBadge>`, `useFarmStationsQuery`, type-only `WeatherStation`) are recorded in ARCHITECTURE.md. The same list in `frontend/CLAUDE.md` still needs updating (see the proposals below).
- Detail: the series and readings queries wait until the detail query has returned (`isStationKnown`). An unknown or foreign station therefore makes only one 404. The detail poll stops on a 404 (`pollUnlessNotFound`).
- Every station range is a preset ending now, so it is always live. Polling uses the same span-keyed cache and sliding window as history (`historyCacheKey`/`historyRequestFilters`). Readings poll only on page 1. A page out of range is clamped in an `immediate` watcher.
- The range buttons use `aria-pressed` and neutral colours. Axe flagged white text on the light-mode primary at 2.21:1.
- The `HistoryTable` prop `farmName` was renamed to `subject`, and the table gained `showSensorColumn`. `buildExportFilename` takes `{ prefix, fallback }`, which gives `historial-estacion-<slug>-YYYYMMDD_YYYYMMDD.<ext>`. `useHistoryExport` also exposes `exportStation`.
- **The dev server on :3000 is stale** because new composables and utils were added. Restart `npm run dev` before using it.

Contract deviations: none. The sparkline is hidden when it is `null` or has fewer than 2 points. When the variable exists but has no data, the card shows a short text note instead.

AC self-check: brief items 1–7 ✓. Format, lint, typecheck and build are all green, with typecheck and build run in a scratch copy.
E2E: ran against a production build of this source on :3100.
- `stations.spec.ts` (9 tests) and the 2 new `dashboard.spec.ts` "Estaciones en el dashboard" tests passed, along with the existing stub-based live specs: 28/28 with `--repeat-each 2`.
- Real-backend smoke as hadid (farm 16, station 17) also passed, with no API errors or page errors: home card, Ver detalle, switch to 30 d, and the list.
- The `loginAs`-based specs (dashboard/farm/sensors/a11y) fail at login because juan.perez and the other seeded users are missing from the dev DB. This is pre-existing and unrelated.

Decisions: no variable filter on the station page, which is out of scope. Export is disabled when the range has 0 readings. The home station section sits outside the overview block, so it still renders when the farm overview fails.

For next agent (QA):
1. Sidebar "Estaciones" opens a card per station. Check that the status badge shows text ("En línea" / "Sin datos recientes" / "Sin reportar" / "Inactiva").
2. "Ver detalle de <name>" opens the detail page, which has these regions: "Condiciones actuales", "Gráficas" and "Lecturas".
3. In the "Periodo" group, "Últimos 7 días" sets `?range=7d` and sends a 7-day `date_from`/`date_to` on the series and readings requests.
4. Pagination button "Página 2" sets `?page=2`.
5. "Exportar" → "Descargar CSV" requests `/api/sensors/stations/<id>/export/csv/` with the range.
6. `/dashboard/stations/9999` shows "Estación no encontrada" with a "Ver todas las estaciones" link.
7. With seed data (`make loaddata`): farm 1 has online stations plus an inactive one, farm 2 is stale, and farm 13 shows the empty state.

## Proposed improvements
- Rule: in `frontend/CLAUDE.md` (Layers & file placement), extend the sanctioned-exceptions bullet. `dashboard` also consumes `<StationCard>` and `useFarmStationsQuery`. `sensors` also consumes `<StationCard>`/`<StationStatusBadge>`, `useFarmStationsQuery` and the type-only `WeatherStation`. Data that both the home dashboard and a sensors page render lives in `farm`.
- Rule: "A selected/pressed state never uses `color="primary" variant="solid"` with text: white on the light-mode primary green is 2.2:1 (fails 1.4.3). Use `neutral` solid, which is inverted and high contrast in both modes." This goes in `frontend/CLAUDE.md` (UI components). The same issue probably affects the current page of `HistoryTable`'s `UPagination` and the history view `UTabs` pill in light mode. No axe scan covers them.
- Rule: "To run the frontend e2e against a scratch production build, point a throwaway Playwright config in the scratchpad at `e2e/frontend` with `baseURL` set to the build's port. Never add a config file inside `e2e/`." This goes in the root `CLAUDE.md` E2E section.
