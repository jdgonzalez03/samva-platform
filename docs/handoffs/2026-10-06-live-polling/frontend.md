# frontend handoff — live polling of sensor readings
Summary:        Views of the latest readings now refetch every 30 s (`LIVE_REFRESH_INTERVAL_MS`) while the tab is visible. Background refetches keep the current data on screen, with no skeleton. No backend changes.
Files changed:
- frontend/layers/common/app/constants/live-refresh.ts (new), frontend/layers/common/nuxt.config.ts (auto-imports `app/constants`)
- frontend/layers/common/app/utils/api/errors.ts (`pollUnlessNotFound`)
- frontend/layers/farm/app/composables/useFarmsQuery.ts, usePlotQuery.ts
- frontend/layers/sensors/app/composables/useFarmSensorsQuery.ts, useHistoryReadingsQuery.ts, useHistorySeriesQuery.ts, useHistoryPlotAveragesQuery.ts, useHistoryFilters.ts
- frontend/layers/sensors/app/utils/history-filters.ts, types/sensors.ts, pages/dashboard/history.vue, pages/dashboard/sensors.vue
- frontend/layers/dashboard/app/pages/dashboard/index.vue, plots/index.vue, plots/[id].vue
- e2e/frontend/helpers.ts (`stubSession`, `LIVE_REFRESH_MS`, `STUB_FARM`/`STUB_PLOT`, T strings), dashboard.spec.ts, sensors.spec.ts
Routes/UI:      No new routes. Polled views: /dashboard (farm overview), /dashboard/plots (Mis lotes), /dashboard/plots/<id> (overview), /dashboard/sensors, and /dashboard/history (only for a live range).
Gotchas:
- History: a range is "live" when it ends at now (a 24h/7d/30d preset, or the preset that an invalid custom range falls back to). A live range is cached under its span, not under its instants. Each request slides `date_from`/`date_to` so the window ends at the moment of the request, which lets a poll reach readings that arrived after the page opened. The series result carries its own window (`HistorySeriesResult`), so the chart's time axis matches the polled data. Export also slides a live window to now.
- Readings table polls only page 1. On later pages a poll would shift rows under the reader.
- A failed background poll keeps the data on screen. The error/Retry state shows only when there is no data (`*Failed` computeds).
- The history `aria-live` status is refreshed only when a request the user caused settles, not when a poll changes the counts. This avoids an unprompted announcement every minute.
- Plot overview polling stops after a 404 (`pollUnlessNotFound`).
- Not polled: predictions, profile, CMS, irrigation definitions, weather, farm plot list.
AC self-check:  Brief items 1–5 ✓. Plot detail and history (live and fixed) are covered by e2e. The dashboard overview, Mis lotes and Mis sensores use the same `refetchInterval` with no spec of their own.
Decisions:      A custom range that ends today is not polled (it is not "ending at now"). Plot averages (the farm-wide history chart mode) poll under the same live rule as the series.
For next agent:
- The new specs ("Actualización en vivo …" in dashboard.spec.ts and sensors.spec.ts) stub the whole session via `stubSession` and do not need seeded users. They use `page.clock.install()` + `fastForward(LIVE_REFRESH_MS)` with `serviceWorkers: 'block'`.
- The running dev server on :3000 was stale after the new `common/app/constants` auto-import dir: the dashboard failed to hydrate with "Failed to fetch dynamically imported module …entry.js". **Restart `npm run dev`** before running them. They passed (3×3 repeats) against a production build of the same source served on :3100.
- The older dashboard/sensors specs use `loginAs` with seeded users, who are absent from the current dev DB, so they were not run.

## Proposed improvements
- Rule: "A polled query (`refetchInterval`) never lets a failed background refetch replace data on screen: gate the error branch on `isError && data === undefined`, and never key a sliding 'until now' window on its instants — key it on its span and resolve the instants inside `queryFn`." → `frontend/CLAUDE.md` (Vue Query section).
- Rule: "Specs that test frontend-only behaviour (polling, rendering) use `stubSession` instead of `loginAs`, so they run without seeded users; time-driven behaviour uses `page.clock.install()` + `fastForward`." → root `CLAUDE.md` E2E section.
