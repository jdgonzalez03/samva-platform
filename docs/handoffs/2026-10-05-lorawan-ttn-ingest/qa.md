# qa handoff — LoRaWAN ingest from The Things Network
Summary:        Playwright coverage for the fuzzy view's per-source breakdown and the new 422 copy (stubbed and against the real backend), a LoRa history variable for maria, `input_sources` in the API, and an axe scan of the breakdown. Full suite: 91/91 green, twice in a row.
Files changed:  e2e/frontend/helpers.ts (T strings, LORA_USER, ingestReadings, selectFarm(currentFarm), sturdier loginAs)
                e2e/frontend/predictions.spec.ts (+3 tests; fixed the stale 422 copy)
                e2e/frontend/sensors.spec.ts (+1 test)
                e2e/frontend/a11y.spec.ts (+1 test)
                e2e/backend/api_predictions.spec.ts (input_sources assertions)
Covered flows:  - Stubbed fuzzy view: field / station / used rows, null station shows sr-only "sin datos", "Usado:" equals the card headline.
                - Real flow (juan): ingest the three inputs into SEED-0005, pick "Lote El Abrevadero", click "Calcular predicción" (201). Each of the 3 cards shows "Sensores de campo:" (a number), "Estación:" ("sin datos"), and "Usado:" (= headline).
                - Real flow (juan): pick "Lote Sin Mapear" (no sensors), calculate (422). Alert: "No disponible en este momento: humedad del suelo, temperatura del aire, radiación solar".
                - Stubbed 422: partial list with the new copy.
                - History (maria): switch to Finca La Montaña, choose plot "Lote El Rodeo" and variable "CO₂". URL gets variable=co2 and one chart is shown, captioned CO₂.
                - API: POST irrigation returns `input_sources[input].field` as a number and `.station` as null.
AC checklist:   (no acceptance-criteria.md for this slug; items come from plan §6 and §8, e2e part)
                ✓ §6 breakdown "Sensores de campo · Estación · Usado" on each input. Tests: predictions.spec "cada entrada desglosa…" and "tras calcular, cada entrada muestra su desglose por fuente".
                ✓ §6 "—" when a source is missing (accessible as "sin datos"). Tests: same two.
                ✓ §6 422 copy "No disponible en este momento: …". Tests: predictions.spec "sin lecturas recientes…" (stubbed) and "un lote sin lecturas avisa…" (real).
                ✓ §6 new SemanticKeys accepted by history (filter + chart). Test: sensors.spec "una variable nueva de las sondas se puede elegir y graficar".
                ✓ §4/§6 `input_sources` in the prediction response. Test: api_predictions.spec "con lecturas recientes crea una predicción…".
                ✓ a11y of the breakdown: axe scan of the fuzzy panel with a null source. Test: a11y.spec "desglose por fuente de la vista difusa…". It needed one known exclusion, see Findings.
                ✗ en strings ("Field sensors:", "Not available right now") are not asserted in e2e. Only es is covered, consistent with the other predictions specs.
Gaps:           - MQTT/TTN ingest has no UI and needs a broker. It is covered by backend unit tests and the simulator, not by Playwright.
                - Field + station averaging is not shown with both sources in the real flow. The seeded stations have use_in_predictions=False, and flipping it in the Django admin needs global-state restore. The stubbed test covers rendering both values.
                - "Mis sensores" showing probes 101–109 online is not asserted. It depends on `simulate-lora` having run recently.
Findings:       F1 (pre-existing, not caused by this feature): once a prediction is shown, the fuzzy view's UDashboardPanel body (`overflow-y-auto`) scrolls but contains nothing focusable. axe flags `scrollable-region-focusable` (serious, WCAG 2.1.1). It fires identically with or without the breakdown. It is excluded on that one scan as FUZZY_BODY_KNOWN_SCROLL in a11y.spec.ts; frontend should make the body keyboard-scrollable, then remove the exclusion.
                F2: loginAs flaked about once per full run. A late form re-render wiped the email field after fill (the snapshot showed the email empty and the password filled). loginAs now re-fills until both fields hold their values, with the same signature for all callers.
For reviewer:   - The real-backend tests rely on seeded readings: SEED-0005 is fresh-ingested by the test itself, and the CO₂ history test needs `make seed-sensors` within the default 7-day window.
                - The real breakdown test ingests values offset by the second-of-minute (30+x, 18+x, 600+x). The history table shows minutes, so equal values in one minute (same as api_predictions.spec's 30/18/600) render as identical rows and broke sensors.spec's "no row repeats across pages" check. I ran `make seed-sensors` once to purge the duplicates already stored.
                - The real-flow tests create IrrigationPrediction rows on plot 2 each run; nothing asserts on them.
                - Card lookup: h3 title → nearest `[data-slot="root"]`; value lookup: `dt` → following `dd` (dd text includes the sr-only and aria-hidden spans, so matches are loose).

## Proposed improvements
- Rule: "Specs that ingest readings must not post the same values into the same sensor as another spec: the history table renders minutes, so equal readings in one minute look identical and break text-based row comparisons — vary the value per run." → root `CLAUDE.md` (E2E section).
- Rule: "`make e2e-test` does not exist; the full suite runs with `npx playwright test` from `e2e/` (headless by default)." → root `CLAUDE.md` (E2E section) or the qa agent spec, which currently names `make e2e-test`.
- Rule: "The qa agent spec's paths (`e2e/tests/<module>/`, `createVerifiedUser`) are stale: the real layout is `e2e/frontend/<module>.spec.ts` with `loginAs`/`gotoHydrated`." → qa agent spec.
