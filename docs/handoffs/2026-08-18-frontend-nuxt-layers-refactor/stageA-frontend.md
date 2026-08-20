# frontend handoff — Stage A: Nuxt Layers refactor (behavior-preserving)

Summary: Restructured `frontend/` into `layers/{common,auth,accounts,cms,dashboard}` per ADR 0001, made the `$api` plugin isomorphic (fixes the docker SSR double-`/api` 404), collapsed `authApi` onto the common fetcher, introduced `cmsApi` + `useAsyncData` for the SSR landing, added the designed root `error.vue`, and hid the dead sidebar links. All gates green; behavior identical (23/23 e2e).

## Final tree

```
frontend/
├── app/                        # shell only
│   ├── app.vue
│   └── error.vue               # new (A.5)
├── layers/
│   ├── common/                 # HTTP stack + shared UI
│   │   ├── nuxt.config.ts      # $meta.name: 'common'
│   │   ├── shared/.gitkeep     # reserved for cross-layer types (#shared)
│   │   └── app/
│   │       ├── assets/main.css
│   │       ├── components/{Header,Footer,Logo}.vue, icons/TractorIcon.vue
│   │       ├── layouts/default.vue
│   │       ├── plugins/api.ts            # universal (was api.client.ts)
│   │       └── utils/{image.ts, api/{fetcher,tokens,errors}.ts}
│   ├── auth/
│   │   └── app/{pages/login.vue, layouts/login.vue, middleware/{auth,guest}.ts,
│   │        composables/useAuth.ts, plugins/auth-init.client.ts,
│   │        utils/api/auth.ts, types/auth.ts}
│   ├── accounts/
│   │   ├── nuxt.config.ts      # + imports.dirs exposing accountsApi (see Gotchas)
│   │   └── app/{pages/dashboard/profile.vue, components/dashboard/ProfileSkeleton.vue,
│   │        composables/useAccount.ts, utils/api/accounts.ts, types/profile.ts}
│   ├── cms/
│   │   └── app/{pages/index.vue, components/cms/*.vue (6),
│   │        utils/{api/cms.ts (new), block.ts, icons.ts}, types/{landing,blocks,common}.ts}
│   └── dashboard/
│       └── app/{layouts/dashboard.vue, pages/dashboard/index.vue,
│            components/{DropDownUser.vue, dashboard/{FarmsMenu,FarmStats}.vue}}
├── public/, server/            # unchanged at root
└── nuxt.config.ts              # aliases + css path updated
```

Deleted: root `app/{components,composables,layouts,middleware,pages,plugins,utils,assets}`, root `shared/`, `app/utils/api/auth/endpoints/` indirection, `app/composables/index.ts` barrel.

## Isomorphic `$api` plugin design (A.2)

- `layers/common/app/plugins/api.ts` is now **universal** and a **named object plugin** (`name: 'api'`): `baseURL = import.meta.server ? config.apiBaseServer : config.public.apiBase`; Bearer injection guarded (`getAccessToken()` returns `null` on server — Phase 0.1 behavior preserved).
- All module `api.ts` paths are **relative** (`accounts/login/`, `cms/landing/`) so no double-`/api` occurs in either topology; verified SSR on host dev (`curl http://localhost:3000/` shows CMS content).
- `authApi.login` now goes through `fetcher.post<AuthResponse>('accounts/login/', payload)` (contract drift #1 fixed); `login.vue` catch reads ofetch `FetchError` → `error.data?.error` with a generic fallback (drift #3).
- Landing: `useAsyncData('cms-landing', () => cmsApi.getLanding())` (drift #4 fixed); `Profile` types switched to `| null` (drift #2 fixed).
- `fetcher.ts`/`tokens.ts`/`errors.ts` unchanged in shape; `refreshAccessToken` keeps raw `$fetch`.

## Routes/UI

No new routes; same entry points (`/`, `/login`, `/dashboard`, `/dashboard/profile`). New: any unknown route renders `app/error.vue` (Spanish, `useHead` title, `UButton` "Volver al inicio" → `clearError({ redirect: '/' })`, keyboard-operable, semantic color tokens). Sidebar no longer shows History/Predictions; `FarmStats.vue` dead `to="/dashboard/history"` removed (component still unmounted).

## Gotchas

- **Plugin ordering across layers**: auto-registered layers load alphabetically (accounts→auth→cms→common→dashboard), so `auth-init` registered BEFORE the `$api` plugin and cleared tokens on hard loads (fetchMe → throw → logout). Fixed with named object plugins: `auth-init` declares `dependsOn: ['api']`. Do not rename the `api` plugin without updating `dependsOn`.
- **`accountsApi` auto-import**: `layers/accounts/nuxt.config.ts` adds `imports.dirs` (absolute path via `fileURLToPath`) exposing `app/utils/api` — this is how the auth layer consumes `accountsApi` without a runtime cross-layer import. Relative `imports.dirs` in a layer config are NOT layer-relative; use absolute.
- Auth/guest redirects still happen client-side after hydration (Phase 0.1 behavior preserved).
- Added `useHead` titles to login ("Sign in"), profile ("My Profile"), and landing (CMS `data.title`) — required by `frontend/CLAUDE.md` (every page sets its tab title); no spec asserts titles, behavior otherwise identical.
- Nitro serves the JSON error for 404s unless the request has `Accept: text/html` — smoke-test error.vue with that header.

## Contract deviations

None — all endpoints, shapes, and the four drift fixes implemented exactly per `contract.md`.

## Cross-layer exceptions (sanctioned by contract, to be recorded in Docs stage)

- `useAuth`/`auth-init` call auto-imported `accountsApi` (surfaces table: "auth (uses accountsApi)").
- Type-only imports of `Profile` from `layers/accounts/app/types/profile` in `useAuth.ts` and `DropDownUser.vue` (erased at build; runtime deps stay domain → common).
- `TractorIcon` imported from common by auth login page, cms hero, and dashboard layout — domain → common, allowed.

## AC self-check

- AC2 ✓ — all domain code under `layers/*`; root `app/` = `app.vue` + `error.vue` only.
- AC3 ✓ — all HTTP via module `api.ts` over the common fetcher incl. `cmsApi` + `useAsyncData` (no direct `useFetch`/`fetch` remain).
- AC4 ✓ — per-layer types/constants in-layer; only the sanctioned exceptions above cross layers.
- AC5 ✓ — 23/23 e2e pass unmodified (landing, login→dashboard, logout, route protection, profile update).
- AC6 ✓ — History/Predictions hidden; unknown route renders designed `error.vue` with working home link (SSR-verified).
- AC7 ✓ — typecheck/lint/build all exit 0 (plus `format:check`).
- AC-A11Y-7 (groundwork) ✓ — error page has descriptive title + `<h1>`, keyboard-operable home button with visible focus ring (Spanish for now; translated in Stage C).

## Verification outputs

- `npm run typecheck` → exit 0; `npm run lint` → exit 0; `npm run build` → exit 0; `npm run format:check` → "All matched files use Prettier code style!".
- `curl -s http://localhost:3000/ | grep -io 'agricultura de precisi.n'` → `Agricultura de Precisión` (SSR through isomorphic fetcher).
- `curl -s -H 'Accept: text/html' http://localhost:3000/ruta-inexistente` → renders `404 — Página no encontrada` / `Volver al inicio`.
- `npx playwright test` (e2e/) → **23 passed** (backend + frontend projects).
- No frontend unit-test runner exists (no Vitest script) — per Phase 0.1 precedent the stage gate is typecheck/lint/build + e2e.

## Decisions

- Named plugins + `dependsOn` over renaming files to force order (explicit > implicit alphabetical ordering).
- Relative in-layer imports for types/utils/api (no per-domain aliases added); auto-imports only where the contract requires (`accountsApi`) or Nuxt provides by default (components, composables, top-level utils).
- Stage B (Vue Query) and Stage C (i18n) NOT started, per dispatch.

## For next agent

QA flow: `/` (SSR content in view-source), header "Ir al Dashboard" → `/login` (anon), login `juan.perez@email.com` → `/dashboard` + "Welcome back" toast, sidebar shows only Dashboard/Profile (+ Feedback/Help), `/dashboard/profile` edit First Name → "Save changes" → "Profile updated" toast → persists on reload, user dropdown (button "Pérez") → "Log out" → `/login` with tokens cleared, direct `/dashboard` anon → `/login`, `/cualquier-ruta-404` → error page → "Volver al inicio" → `/`.

## Proposed improvements

- Rule: "Nuxt plugins that consume another plugin's injection must be named object plugins with `dependsOn: ['<name>']` — auto-registered layers load alphabetically, so cross-layer plugin order is otherwise accidental." → `frontend/CLAUDE.md` (new Layers section).
- Rule: "In a layer's `nuxt.config.ts`, resolve `imports.dirs` (and any path option) to absolute paths with `fileURLToPath(new URL(..., import.meta.url))` — relative paths are not layer-relative." → `frontend/CLAUDE.md`.
- Rule: "When smoke-testing Nuxt pages with `curl`, send `Accept: text/html` — Nitro returns a JSON error body for 404/error routes otherwise." → `frontend/CLAUDE.md` (or e2e docs).
