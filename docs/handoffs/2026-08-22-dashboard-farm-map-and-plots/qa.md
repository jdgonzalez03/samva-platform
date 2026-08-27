# qa handoff — Dashboard farm map and plots (MINIMAL scope)

**Summary:** Repair-only pass, per the user's explicit reduced scope. The feature broke the
farm-switcher spec (new seed data + the plot-count card replaced); `farm.spec.ts` and the `T`
map were repointed at the new UI. No new coverage of the map/list/plot-detail feature was
written — see **Deferred coverage**.

## Files changed

- `e2e/frontend/helpers.ts`
  - **removed** `T.plotCount` (`'2 lotes'`) — that string no longer renders anywhere; the
    dashboard shows a bare number under the `Lotes` stat-card label.
  - **added** `T.statPlots` (`'Lotes'`) — the visible stat-card label the count is read from.
  - updated the seed comment on the farm entries: juan.perez owns **three** farms, name-ordered,
    so `Finca El Tesoro` is still the default selection.
  - **added** `statCardValue(page, title)` helper: climbs from the visible card label to the
    card root (`[data-slot="root"]`) and reads the value paragraph. The label and the value live
    in sibling subtrees, so no single descendant locator reaches both.
- `e2e/frontend/farm.spec.ts` — all five assertions repointed from `T.plotCount` to
  `statCardValue(page, T.statPlots)`; seed counts pinned as named constants (`PLOTS_FIRST = '3'`,
  `PLOTS_SECOND = '2'`).

## Assertions rewritten (and why)

1. **Default farm** — `Lotes` card now reads `3` (El Tesoro gained a third plot, `Lote Sin
   Mapear`, with null geometry).
2. **Farm switch** — the stale comment/logic at the old `farm.spec.ts:29` (both farms have 2
   plots, count cannot prove the refetch) is **no longer true**: El Tesoro has 3 and San Vicente
   2. The `page.on('request')` URL-collection workaround was **dropped** and replaced by a direct
   `3 → 2` assertion on the card, which proves the refetch on its own and asserts the user-visible
   outcome rather than network traffic. Comment now states the current fact.
3. **Persistence after reload** — same repoint, expects `2`.
4. **Plots-error fallback** — the Retry button is now located as
   `getByRole('alert').filter({ hasText: T.plotsLoadError }).getByRole('button', { name: T.retry })`.
   `Reintentar` is **not** a unique accessible name (both weather cards render their own retry),
   so an unscoped `getByRole('button', { name: T.retry })` would be strict-mode ambiguous.
   Note `getByRole('alert')` alone is also not enough: Nuxt UI's `USkeleton` renders
   `role="alert" aria-label="loading"`, so loading skeletons match the alert role too — the
   `hasText` filter is load-bearing.
5. **Farms-error fallback** — unchanged (`.first()` still valid: with farms failing there is no
   selected farm, so the plots/weather queries stay disabled and no other retry renders).

Nothing was weakened. The third farm (`Finca Sin Lotes`) appears in the switcher menu but no
existing assertion enumerates the farm list, so nothing else needed changing.

## Suite result

`cd e2e && npx playwright test` (headless, `workers: 1`): **46 passed, 0 failed** — back to the
pre-feature baseline of 46. Dev server was warmed before the run. Re-run as the last action after
the parallel frontend fix pass; none of my assertions touch the two strings that pass is editing
(plot-detail `<h1>`/title, the `"1 sensores"` map `aria-label`).

## Deferred coverage

The user explicitly deferred a full QA pass for this feature. **No e2e test covers any of the new
surface.** What a complete pass would still need:

- **Map view (AC1–AC10, AC-A11Y-3/4/5/6/7/13/14):** polygon + casing + boundary path counts per
  farm, hover/focus info card, Escape keeps focus on the path, Enter/click navigation to
  `/dashboard/plots/<id>`, `Sin descripción` fallback, unmapped-plots note and its link,
  basemap radiogroup switching (`Calles`/`Satélite`) with attribution change.
- **List view (AC11–AC12, AC-A11Y-8):** three `role="listitem"` rows, row link accessible names,
  navigation.
- **View mode (AC14–AC17, AC-A11Y-2):** `?view=` on load, tab switch pushes history, Back
  restores, `localStorage` persistence, `?view=map` default with cleared storage, tab
  keyboard operability.
- **Stat cards (AC18–AC21, AC-A11Y-9):** the four tiles, units (`°C`, `W/m²`), `Sin datos` for
  absent solar radiation on San Vicente, `Actualizado hace …`, the `Desactualizada` badge.
- **Empty/error states (AC13, AC25, AC26, AC-A11Y-10):** `Finca Sin Lotes` empty state in both
  tabs, weather-error retry, `aria-busy` skeletons. (Only the plots-error path is covered, and
  only as a regression of the pre-existing test.)
- **Plot detail (AC27–AC30, AC-A11Y-11):** direct load, `Lote no encontrado` for a bad id,
  logged-out `/en/dashboard/plots/2` → `/en/login`, single `<h1>`, back link restores view mode.
- **Route-stubbed criteria (AC9, AC24):** the `Farm.location` fallback / `noLocation` empty state
  and the "no farms" state are unreachable with the current seed and need stubbed responses.
- **i18n (AC34):** `/en/dashboard` and `/en/dashboard/plots/<id>`.
- **a11y (AC-A11Y-1, AC-A11Y-12):** the existing `a11y.spec.ts` axe scan of `/dashboard` does
  pass and now covers the map view incidentally, but there is no scan of **list** mode, the
  **satellite** basemap, the plot-detail page, the error/empty states, or the 320 px viewport.
- **Backend-only (AC22, AC31–AC33):** not reachable through the UI; verified in the backend slice.

Everything above is currently attested only by the frontend author's manual self-check in
`frontend.md`, not by an automated test.

## For reviewer

- `statCardValue` depends on Nuxt UI's `UPageCard` emitting `data-slot="root"`/`data-slot="title"`.
  That is the only structural coupling introduced; if `UPageCard` changes markup, this one helper
  is the single place to fix.
- The seed counts (`3` / `2`) are spec-local constants, not `T` entries — they are fixture data,
  not locale-dependent copy, and `T` is documented as the locale seam.
- `make loaddata` was **not** run (it would reset the e2e user's password).

## Proposed improvements

Propose only — I edited no `CLAUDE.md`.

1. **`e2e/CLAUDE.md`** —
   > Nuxt UI's `USkeleton` renders `role="alert" aria-label="loading"`, so `getByRole('alert')`
   > matches loading placeholders as well as real error blocks — always narrow an alert locator
   > with `.filter({ hasText: … })`.
2. **`e2e/CLAUDE.md`** —
   > Retry/close/edit style controls repeat across cards; never locate them by accessible name
   > alone. Scope to the owning alert/card/region first, and prefer that over `.first()`, which
   > silently binds to whichever control renders first.
3. **`e2e/CLAUDE.md`** —
   > Assert user-visible outcomes over network traffic: reach for `page.on('request')` URL
   > collection only when no rendered value distinguishes the states. Re-check such workarounds
   > when the seed changes — they outlive the ambiguity that justified them.
