# docs handoff — Docs stage (AC17)

Summary: Documentation-only stage. Rewrote the Frontend section + Current state of
`docs/ARCHITECTURE.md`, updated `frontend/CLAUDE.md` to the layers layout with new
Layers/SSR/Vue Query/i18n rule sections, and extended `e2e/README.md` (dev topology,
serialized suite, locale-seam details). No code touched.

Files changed:

- `docs/ARCHITECTURE.md`
- `frontend/CLAUDE.md`
- `e2e/README.md`

What each now covers:

- **ARCHITECTURE.md (Frontend)**: layers tree (common/auth/accounts/cms/dashboard + root
  shell `app.vue`/`error.vue`); isomorphic `$api` plugin (server `apiBaseServer` / client
  `public.apiBase`) + fetcher with relative module paths (auth endpoints under `accounts/`,
  no `auth/` mount); `#api` = common HTTP stack only, `#shared` reserved/empty; named
  plugins ordered via `dependsOn` (`api` ← `vue-query` ← `auth-init`, + `i18n:plugin`);
  the two sanctioned cross-layer exceptions (auth → auto-imported `accountsApi`; type-only
  `Profile` imports); Vue Query conventions (per-module query-key enums, shared
  `queryOptions` factory, `isPending` skeletons, SSR landing on `useAsyncData` — not Vue
  Query); i18n (prefix_except_default, es default + browser-detect cookie, per-layer locale
  files actually used, translated surfaces vs fixed-Spanish landing). Current state
  refreshed: layers migration done, dashboard index is a placeholder (map/stats moved to
  Planned), i18n moved to Working, dead sidebar-links note corrected. No dependency
  versions in prose — points at `frontend/package.json`.
- **frontend/CLAUDE.md**: new "Layers & file placement" (what goes in a domain layer vs
  `common`; root `app/` shell-only; named-plugin `dependsOn` rule; absolute `imports.dirs`
  rule), HTTP rules updated (relative-to-baseURL paths, `accounts/` mount, per-endpoint
  error shapes, `#api` scope), new SSR section (`import.meta.client` guards, both
  topologies), new Vue Query section (composable wrappers, `<Module>QueryKey` enums, plain
  queryOptions factory, invalidate on success, `isPending` binding, void-wrapped handlers),
  new i18n section (`t()` everywhere in scope, per-layer locale files/namespaces, landing
  stays Spanish, active-locale `Intl` — never `'en-US'`, `localePath` navigation, `{'@'}`
  escaping). Composables section updated to layer paths. All single-bullet rules; existing
  rules merged/refined, none duplicated.
- **e2e/README.md**: dev topology (backend compose from `backend/` + host `npm run dev`,
  seed + one-time password), warm-dev-server note, "Serialized suite" section
  (`workers: 1`, shared backend user, `fullyParallel` caveat), credentials table was
  already present (E2E_USER_EMAIL / E2E_USER_PASSWORD, defaults `juan.perez@email.com` /
  `E2eSmoke_2026!`), locale-pinning section extended (`es-CO`, `T` as the only
  locale-dependent seam, `T_EN`/`SWITCHER`, type-attribute input selectors, dropdown
  Escape gotcha), layout note (`e2e/frontend|backend/`, no `e2e/tests/`).

Contract deviations: none — docs describe the implemented contract exactly (relative
paths, `accounts/` mount, error shapes, sanctioned exceptions).

AC self-check:

- AC17 ✓ — `docs/ARCHITECTURE.md` and `frontend/CLAUDE.md` both reflect the layers layout,
  Vue Query conventions, and i18n rules; verified against the actual tree
  (`frontend/layers/*`), `frontend/nuxt.config.ts`, layer configs, and
  `e2e/playwright.config.ts`. `frontend/CLAUDE.md` passes `prettier --check`.

Decisions:

- Folded the Stage A/B/C handoffs' `frontend/CLAUDE.md` rule proposals into the new
  sections (plugin `dependsOn`, absolute `imports.dirs`, queryOptions factory, `$x`
  injection cast, `{'@'}` escaping, per-layer locale files) and the e2e proposals
  (`workers: 1`, dropdown Escape, warm dev server) into `e2e/README.md`.
- No `e2e/CLAUDE.md` created (README extension was in scope; a CLAUDE.md was not).

For next agent (QA/reviewer): read the three files above; check that nothing in them
contradicts the code (`frontend/nuxt.config.ts` aliases/i18n block, `layers/*/nuxt.config.ts`,
`e2e/playwright.config.ts`).

## Proposed improvements

- Root `CLAUDE.md` (E2E section) says Playwright tests live in `e2e/tests/<module>/`, but
  the real (and Playwright-config-matched) layout is `e2e/frontend/` and `e2e/backend/`,
  and the helpers named there (`createVerifiedUser`, `loginUser` in `e2e/helpers/`) don't
  exist — the actual helper is `loginAs` + `T` in `e2e/frontend/helpers.ts`. Proposed rule
  rewrite: "Any multi-step user-facing feature needs a Playwright spec in `e2e/frontend/`
  (API-only checks in `e2e/backend/`); reuse `loginAs` and the `T` string map from
  `e2e/frontend/helpers.ts`." → root `CLAUDE.md`.
