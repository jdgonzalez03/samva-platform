# frontend handoff — LoRaWAN ingest from The Things Network
Summary:        The 8 new SemanticKeys are known to every per-key map (type, history filter whitelist, icons, colours, plot-detail icons); the fuzzy irrigation view shows a per-input "field sensors / station / used" breakdown and the new 422 copy.
Files changed:  frontend/layers/sensors/app/types/sensors.ts
                frontend/layers/sensors/app/constants/history.ts
                frontend/layers/sensors/app/utils/history-filters.ts
                frontend/layers/sensors/app/composables/useVariableColor.ts
                frontend/layers/dashboard/app/constants/plot-detail.ts
                frontend/layers/predictions/app/types/predictions.ts
                frontend/layers/predictions/app/components/predictions/IrrigationInputs.vue
                frontend/layers/predictions/app/pages/dashboard/predictions/fuzzy.vue
                frontend/layers/predictions/i18n/locales/{es,en}.json
Routes/UI:      No new routes. Sidebar "Predicciones" → "Riego con lógica difusa" card (/dashboard/predictions/fuzzy); "Historial" (/dashboard/history); plot detail (/dashboard/plots/<id>).
Gotchas:        - Breakdown row is hidden when `input_sources[input]` is absent (old predictions carry `{}`), so the latest seeded history row may show no breakdown until "Calcular predicción" is clicked.
                - A null source renders a visible "—" (aria-hidden) plus sr-only "sin datos"/"no data"; the "·" separators are aria-hidden. A dd's DOM text is therefore e.g. "—sin datos·" — select by label text, not exact dd text.
                - "Usado:" repeats the headline average (`avg_*`) with unit.
                - 422 variable names fall back to the raw key if a key has no translation (only the 3 model inputs are translated).
                - `useVariableColor` falls back to the `other` colour for an unknown key (was a crash); it is now an arrow function.
Contract deviations: none (no contract.md; consumed backend.md's `input_sources` shape as-is).
AC self-check:  Plan §6 ✓ (all bullets). Format, lint, typecheck, production build green (typecheck/build run in a scratch copy because a dev server is up). No Vitest in this repo; e2e is QA's.
Decisions:      Colours: 8 new pairs appended after `other`, validated with the dataviz validator as one 13-slot ordered set (key order in VARIABLE_COLORS): both modes pass band, chroma, adjacent normal-vision ≥15; light adjacent CVD 7.2 (red↔green, floor band — legal because every figure has a title/label); dark all ≥3:1. 13 hues cannot be pairwise distinct, so colour stays decorative (each figure is single-variable and titled).
                Icons: leaf, thermometer-sun, shovel, wind (co2), battery-medium, battery-charging, solar-panel, zap. LEVEL_COLORS untouched (new keys get the existing neutral fallback).
                Out of scope: per-source breakdown in the history table; labelling the new keys anywhere (labels come from backend variable names).
For next agent: QA (es strings, exact):
                - Log in as maria.lopez@email.com (Finca La Montaña, plot "Lote El Rodeo"), go to /dashboard/predictions/fuzzy, pick "Lote El Rodeo", click button "Calcular predicción".
                - Each of the 3 cards ("Humedad del suelo", "Temperatura del aire", "Radiación solar") shows `<dt>` labels "Sensores de campo:", "Estación:", "Usado:"; null source shows "—" (accessible name "sin datos").
                - en (/en/...): "Field sensors:", "Station:", "Used:", "no data".
                - 422 alert (role="alert"): "No disponible en este momento: humedad del suelo, temperatura del aire, radiación solar" (subset as applicable); en "Not available right now: soil moisture, …".
                - /dashboard/history?variable=co2 (or any new key) is now accepted by the filter parser.

## Proposed improvements
- Rule: "Every per-`semantic_key` lookup (`VARIABLE_COLORS`, `CONDITION_ICONS`, i18n maps) falls back to a generic entry (`other`/`FALLBACK_*`/raw key) — the backend can ship a new key before the client knows it." → `frontend/CLAUDE.md` (UI components & icons).
- Rule: "Run `nuxt typecheck` in the same scratch copy as `nuxt build` when a dev server is up — it rewrites `.nuxt/` too." → `frontend/CLAUDE.md` (PWA bullet on `nuxt build`), merge into that rule.
