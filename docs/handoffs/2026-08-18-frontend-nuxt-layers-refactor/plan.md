# Plan — Frontend Nuxt Layers refactor + Vue Query + i18n

Slug: `2026-08-18-frontend-nuxt-layers-refactor`
Inputs (authoritative, not restated here): `spec.md`, `acceptance-criteria.md` (AC1–AC17, AC-A11Y-1..8), `contract.md`, `docs/adr/0001-frontend-modular-architecture-nuxt-layers.md`.

Everything in this feature is **frontend + e2e + docs**. **Backend: no changes of any kind** — no new endpoints, no serializer/fixture/URL edits; the existing API is consumed as-is per `contract.md`. There is therefore no backend/frontend parallelism to exploit: the stages are strictly sequential (Phase 0 → A → B → C → Docs), each ending green, and QA runs last against the full AC list.

## Verification commands (run at the end of every stage)

From `frontend/` (or via docker: `docker compose -f docker-compose.dev.yml exec frontend <cmd>`):
- `npm run typecheck`
- `npm run lint` (Makefile equivalent: `make lint-frontend`)
- `npm run build`

From `e2e/` (stack running via `make up-dev`, seed data via `make loaddata`):
- `npm test` (all) / `npx playwright test --project=frontend` (frontend only)

Dependency installs follow `frontend/CLAUDE.md`: `npm install <pkg>` without pin. Latest stable as of 2026-08-18 (from the npm registry): `@tanstack/vue-query` 5.101.4, `@nuxtjs/i18n` 10.6.0, `@axe-core/playwright` 4.13.0 (optional, e2e devDep for the a11y backstop).

---

## Phase 0 — e2e safety net + baseline repair (AC1)

### 0.1 Baseline audit (do this first)

Run typecheck/build/e2e on the current tree and expect three pre-existing problems; fix them minimally so a green baseline exists (ARCHITECTURE.md already lists the first as "in progress"):

1. **`frontend/app/pages/dashboard/index.vue` imports files that do not exist**: `import { mockFarms } from '../../utils/dashboard/mock'` and components `DashboardMapView`, `DashboardLotList`, `DashboardSensorCard` (only `FarmStats.vue`, `FarmsMenu.vue`, `ProfileSkeleton.vue` exist under `app/components/dashboard/`). The build cannot resolve the mock import. Minimal repair: strip the unresolved import and the map/list/sensor markup, keep `UDashboardNavbar` + a simple placeholder body (the unfinished map/stats work is explicitly out of scope). Do not create mock files.
2. **SSR-unsafe token access**: `app/utils/api/tokens.ts` calls `localStorage` unguarded, and `app/middleware/auth.ts`/`guest.ts` call `hasTokens()` — a direct browser load of `/dashboard` runs the middleware on the server and crashes. Minimal repair: guard token reads with `import.meta.client` (server → `null`) and have `auth`/`guest` middleware `return` early on `import.meta.server` (decision happens after hydration). Required for the route-protection smoke spec to pass by direct URL.
3. **`e2e/frontend/landing.spec.ts` last test** ("el botón Ir al Dashboard navega a /dashboard") asserts `URL(/\/dashboard/)` — for an anonymous user the auth middleware redirects to `/login`. Fix the assertion to expect the redirect (`/login`) for anonymous visitors.

### 0.2 Smoke specs (new, must pass pre-refactor)

Location matches the real layout (`playwright.config.ts` frontend project matches `frontend/**/*.spec.ts`, baseURL `http://localhost:3000`):

- `e2e/frontend/helpers.ts` (new)
  - `loginAs(page, email?, password?)` — fills `input[type="email"]` / `input[type="password"]`, clicks `button[type="submit"]`, waits for `/dashboard`.
  - Credentials from `process.env.E2E_USER_EMAIL` / `E2E_USER_PASSWORD` (document in `e2e/README.md`). Backend fixtures ship users (`juan.perez@email.com`, …) but no documented plaintext password — set one once via `make shell` (`User.objects.get(email=...).set_password(...)`); this is test setup, not a backend code change.
  - `export const T = { ... }` — a single string map (button/menu/toast names used by role-based selectors). **This map is the locale-stability seam**: Stage C changes only `T` (to the Spanish defaults) and no spec logic, satisfying resolved decision 11 ("pin locale, select by role").
- `e2e/frontend/auth.spec.ts` (new)
  - login → redirected to `/dashboard`, success toast visible.
  - invalid credentials → error toast, stays on `/login`.
  - logout: open sidebar user dropdown (role `menuitem` `T.logout`) → lands on `/login`, tokens cleared.
  - auth middleware: direct `page.goto('/dashboard')` and `/dashboard/profile` unauthenticated → `/login`.
  - guest middleware: authenticated `page.goto('/login')` → `/dashboard`.
- `e2e/frontend/profile.spec.ts` (new)
  - login → navigate to `/dashboard/profile` → edit `first_name` (role `textbox` by `T.firstName`) → save → success toast → reload → value persisted (restore original value at the end to keep specs idempotent).

Form inputs are selected by `type` attribute where labels will later be translated; buttons/menus/toasts by role + `T` names. Playwright frontend project gets `use: { locale: 'es-CO' }` now (harmless pre-i18n, load-bearing in Stage C).

**Gate**: all Phase 0 specs + existing specs green; typecheck/lint/build green.

---

## Stage A — Layers refactor (behavior-preserving) (AC2–AC7)

### A.1 Target tree and file-by-file mapping

Nuxt 4 auto-registers `frontend/layers/*`; each layer mirrors the v4 structure (`app/` srcDir) and gets a minimal `nuxt.config.ts` (`$meta: { name: '<layer>' }`) so registration is explicit. Component subfolder names are preserved so auto-import component names (`DashboardProfileSkeleton`, `CmsHeroSection`…) do not change.

**Root shell** (all that remains under `frontend/app/`):
- `app/app.vue` — stays.
- `app/error.vue` — **new** (see A.5).
- Delete after moves: `app/components/`, `app/composables/` (incl. barrel `app/composables/index.ts` — per-layer auto-imports replace it), `app/layouts/`, `app/middleware/`, `app/pages/`, `app/plugins/`, `app/utils/`, root `shared/`. `frontend/public/` and `frontend/server/` stay at root.

**`layers/common/`** (HTTP stack, shared UI, global layout):

| From | To |
| --- | --- |
| `app/utils/api/fetcher.ts` | `layers/common/app/utils/api/fetcher.ts` |
| `app/utils/api/tokens.ts` | `layers/common/app/utils/api/tokens.ts` |
| `app/utils/api/errors.ts` | `layers/common/app/utils/api/errors.ts` |
| `app/plugins/api.client.ts` | `layers/common/app/plugins/api.ts` (renamed — now universal, see A.2) |
| `app/components/Header.vue`, `Footer.vue`, `Logo.vue` | `layers/common/app/components/` |
| `app/components/icons/TractorIcon.vue` | `layers/common/app/components/icons/TractorIcon.vue` (used by login page and dashboard layout) |
| `app/layouts/default.vue` | `layers/common/app/layouts/default.vue` |
| `app/utils/image.ts` (`getImageUrl`) | `layers/common/app/utils/image.ts` |
| `app/assets/main.css` | `layers/common/app/assets/main.css` (root `nuxt.config.ts` `css:` path updated) |

**`layers/auth/`**:

| From | To |
| --- | --- |
| `app/pages/login.vue` | `layers/auth/app/pages/login.vue` |
| `app/layouts/login.vue` | `layers/auth/app/layouts/login.vue` |
| `app/middleware/auth.ts`, `guest.ts` | `layers/auth/app/middleware/` |
| `app/composables/auth/useAuth.ts` | `layers/auth/app/composables/useAuth.ts` |
| `app/plugins/auth-init.client.ts` | `layers/auth/app/plugins/auth-init.client.ts` |
| `app/utils/api/auth/index.ts` + `endpoints/login.ts` | `layers/auth/app/utils/api/auth.ts` — **collapsed**; `endpoints/` indirection deleted (contract drift #1) |
| `shared/types/auth/auth.ts` | `layers/auth/app/types/auth.ts` |

**`layers/accounts/`** (new layer, resolved decision 4):

| From | To |
| --- | --- |
| `app/pages/dashboard/profile.vue` | `layers/accounts/app/pages/dashboard/profile.vue` |
| `app/components/dashboard/ProfileSkeleton.vue` | `layers/accounts/app/components/dashboard/ProfileSkeleton.vue` (name `DashboardProfileSkeleton` preserved) |
| `app/composables/accounts/useAccount.ts` | `layers/accounts/app/composables/useAccount.ts` |
| `app/utils/api/accounts/index.ts` | `layers/accounts/app/utils/api/accounts.ts` |
| `shared/types/accounts/profile.ts` | `layers/accounts/app/types/profile.ts` — fields switched to `\| null` per contract drift #2 |

**`layers/cms/`**:

| From | To |
| --- | --- |
| `app/pages/index.vue` | `layers/cms/app/pages/index.vue` (rewritten fetch, A.3) |
| `app/components/cms/*.vue` (6 block components) | `layers/cms/app/components/cms/` |
| — | `layers/cms/app/utils/api/cms.ts` — **new** `cmsApi.getLanding()` per contract |
| `shared/types/cms/{landing,blocks,common}.ts` | `layers/cms/app/types/` |
| `shared/utils/block.ts`, `shared/utils/icons.ts` | `layers/cms/app/utils/` (only consumed by cms blocks) |

**`layers/dashboard/`**:

| From | To |
| --- | --- |
| `app/layouts/dashboard.vue` | `layers/dashboard/app/layouts/dashboard.vue` (sidebar edits in A.6) |
| `app/pages/dashboard/index.vue` | `layers/dashboard/app/pages/dashboard/index.vue` (post-Phase-0 simplified version) |
| `app/components/DropDownUser.vue` | `layers/dashboard/app/components/DropDownUser.vue` |
| `app/components/dashboard/FarmsMenu.vue`, `FarmStats.vue` | `layers/dashboard/app/components/dashboard/` |

### A.2 Isomorphic fetcher (contract "Common fetcher" §1–4)

- `layers/common/app/plugins/api.ts` (was `api.client.ts`): universal plugin; `baseURL: import.meta.server ? config.apiBaseServer : config.public.apiBase`; `onRequest` token injection guarded (Phase 0 already made `getAccessToken()` return `null` on server).
- `fetcher.ts` unchanged in shape (`get/post/put/patch/patchFormData/delete`, 401 → `refreshAccessToken()` → retry once → `RefreshTokenError`); `refreshAccessToken` keeps raw `$fetch` (never recurses).
- **`authApi.login` goes through the fetcher** (contract drift #1): `layers/auth/app/utils/api/auth.ts` exports `authApi = { login: (data: LoginPayload) => fetcher.post<AuthResponse>('accounts/login/', data) }`. Caller update in `login.vue`: catch reads `error.data?.error` / `error.status` (ofetch `FetchError`) instead of `Error.message` (drift #3: per-endpoint error shapes, no invented envelope).

### A.3 Landing via `cmsApi` + `useAsyncData` (AC3, AC10 groundwork, drift #4)

`layers/cms/app/pages/index.vue`: replace the direct `useFetch(\`${apiBase}/cms/landing/\`)` with
`const { data } = await useAsyncData('cms-landing', () => cmsApi.getLanding())` — SSR preserved through the now-isomorphic `$api` plugin. Delete the `useRuntimeConfig` fetch plumbing.

### A.4 Aliases (AC2/AC3)

Root `frontend/nuxt.config.ts`:
- `#api` → `./layers/common/app/utils/api` (contract: alias exposes only the common HTTP stack — `fetcher`, `tokens`, `errors`). All `#api/tokens` imports (middleware, plugins, useAuth) keep working.
- `#shared` → `./layers/common/shared` (created empty; reserved for genuinely cross-layer types). All current `#shared/types/...` imports are rewritten to in-layer relative imports (e.g. use relative `../types/profile` to stay unambiguous).
- **Cross-layer rule (AC4) with the contract-sanctioned exceptions, to be documented in the Docs stage**: layers never import each other's files; the only cross-layer consumption is (a) `useAuth`/`auth-init` calling auto-imported `accountsApi` (contract surfaces table: "auth (uses accountsApi)"), and (b) *type-only* imports of `Profile` from `layers/accounts` in `useAuth` and `DropDownUser` (type imports are erased at build; runtime dependency direction stays domain → common only).

### A.5 Root `error.vue` (AC6, AC-A11Y-7 groundwork)

New `frontend/app/error.vue`: designed 404/error page — props `error` (`NuxtError`), `useHead` title (`404 — Página no encontrada` / generic error), heading + short description, `UButton` "Volver al inicio" calling `clearError({ redirect: '/' })` (keyboard-operable by nature; Lucide icon per CLAUDE.md). Strings hardcoded Spanish in Stage A, extracted in Stage C.

### A.6 Hide dead sidebar links (AC6)

`layers/dashboard/app/layouts/dashboard.vue`: remove the `History` (`/dashboard/history`) and `Predictions` (`/dashboard/predictions`) entries from `links`. Also remove the dead `to="/dashboard/history"` on `FarmStats.vue` cards while moving it (component is currently unmounted, but the dead route shouldn't survive the refactor).

### A.7 Stage A gate (AC5, AC7)

`npm run typecheck && npm run lint && npm run build` green; full e2e green **with the Phase 0 specs unmodified**. Manual smoke: landing SSR (view-source shows CMS content), login→dashboard, logout, profile update, unknown route renders `error.vue`.

---

## Stage B — TanStack Vue Query (AC8–AC10, AC-A11Y-8)

### B.1 Install + plugin

- `cd frontend && npm install @tanstack/vue-query` (registry latest: 5.101.4).
- `layers/common/app/plugins/vue-query.ts` (universal): create `QueryClient` (sane defaults: `staleTime` ~30s, `retry: 1`), install `VueQueryPlugin` with `queryClient`. No SSR dehydration needed — all Vue Query usage is client-side (the SSR landing stays on `useAsyncData`, AC10: **no change to `layers/cms/app/pages/index.vue`**).

### B.2 Query keys (per-module enums)

- `layers/accounts/app/constants/query-keys.ts` — `export enum AccountsQueryKey { ROOT = 'accounts', ME = 'me' }`
- `layers/auth/app/constants/query-keys.ts` — `export enum AuthQueryKey { ROOT = 'auth', SESSION = 'session' }`
(cms/dashboard get none — no client reads yet.)

### B.3 Composable conversions (public APIs kept, internals wrapped)

- `layers/accounts/app/composables/useAccount.ts`:
  - `useProfileQuery()` → `useQuery({ queryKey: [AccountsQueryKey.ROOT, AccountsQueryKey.ME], queryFn: () => accountsApi.getMe(), enabled: hasTokens() })`.
  - `useUpdateProfileMutation()` → `useMutation({ mutationFn: accountsApi.updateProfile, onSuccess: invalidate [AccountsQueryKey.ROOT] })`; profile page keeps its success/error toasts, `saving` → `isPending`.
- `layers/auth/app/composables/useAuth.ts`:
  - `login` becomes `useMutation` (`authApi.login` → `setTokens` → prefetch/invalidate the profile query); `loading` exposed from `isPending` so the login button spinner is unchanged.
  - `logout` becomes `useMutation` per AC9 (no backend call — contract: client-side only): `clearTokens()` → `queryClient.removeQueries()` → reset state → `router.push('/login')`.
  - `user`/`isAuthenticated` derive from the shared profile query cache (single source with the sidebar).
  - `auth-init.client.ts`: `hasTokens()` → `queryClient.prefetchQuery` of the profile query (same session-restore behavior).
- Skeleton → `isPending` mapping (AC8, AC-A11Y-8):
  - `layers/dashboard/app/layouts/dashboard.vue` sidebar footer: `loading` → profile query `isPending`; skeleton wrapper gets `aria-busy="true"`.
  - `layers/accounts/.../profile.vue`: `v-if="!user"` → `v-if="isPending"` on `DashboardProfileSkeleton` (+ `aria-busy`); query `isError` renders a text alternative (retry link), not colour alone.

### B.4 Stage B gate

typecheck/lint/build green; all e2e (Phase 0 + landing) green unchanged — behavior identical, plus cached back-navigation.

---

## Stage C — i18n es/en (AC11–AC16, AC-A11Y-1..7)

### C.1 Install + config

- `cd frontend && npm install @nuxtjs/i18n` (registry latest: 10.6.0; v10 targets Nuxt 4).
- Root `nuxt.config.ts`: add module; `i18n: { defaultLocale: 'es', strategy: 'prefix_except_default', locales: [{ code: 'es', language: 'es-CO', name: 'Español' }, { code: 'en', language: 'en', name: 'English' }], detectBrowserLanguage: { useCookie: true, cookieKey: 'i18n_redirected', redirectOn: 'root', fallbackLocale: 'es' } }` → AC11: `/` = es, `/en/...` = en, browser detection on first visit, cookie persistence.
- Locale files follow the layers architecture (@nuxtjs/i18n merges layer i18n config): each in-scope layer ships `layers/<name>/i18n/locales/{es,en}.json` declared in that layer's `nuxt.config.ts` — `common` (switcher labels, error page, generic actions), `auth` (login), `accounts` (profile), `dashboard` (nav/index). `cms` ships none (landing fixed Spanish, AC14). Fallback if layer-merge misbehaves in v10: consolidate into root `frontend/i18n/locales/{es,en}.json` with per-module top-level namespaces (`auth.*`, `accounts.*`, …) — same keys, one file; note which was used in the Docs stage.

### C.2 String extraction inventory (full extraction — resolved decision 10)

- `layers/auth/app/pages/login.vue`: title "Welcome back", description, field labels/placeholders (Email/Password), submit "Sign in", zod messages ("Please enter a valid email address", "Password must be at least 6 characters long"), toasts ("Welcome back"/"You have been logged in successfully"/"Login Failed"/fallback), page title. Zod schema becomes a `computed(() => z.object({...}))` built with `t()` so messages switch live (AC13); Nuxt UI `UForm`/`UAuthForm` already wires `aria-describedby`/`aria-invalid` (AC-A11Y-5 — verify, don't rebuild).
- `layers/dashboard/app/layouts/dashboard.vue`: nav labels ("Dashboard", "Profile"), help links ("Feedback", "Help & Support").
- `layers/dashboard/app/pages/dashboard/index.vue`: navbar title, tabs ("Map"/"List"), "Sensores", "Todos los lotes", "Lote", page title.
- `layers/dashboard/app/components/DropDownUser.vue`: "Log out", "Appearance", "Light", "Dark" + new "Language".
- `layers/accounts/.../profile.vue`: navbar "My Profile", section headings ("Account Information", "Personal Information", "Location", "Organization", "No organization"), every `UFormField` label + placeholder, select items (Identity Card/Foreign ID Card/Passport → `computed`; Male/Female → `computed`), "Farmer" badge, "Member since", "Registered", "NIT", "Save changes", both toasts, page title.
- `frontend/app/error.vue`: title/heading/description/back-link (AC-A11Y-7).
- Out of scope, untouched: `Header.vue`, `Footer.vue`, cms block components (AC14).

### C.3 Switcher (AC13, AC-A11Y-1..4)

- `layers/dashboard/app/components/DropDownUser.vue`: add a "Language" submenu **mirroring the existing "Appearance" checkbox-children pattern exactly** — children "Español"/"English", `type: 'checkbox'`, `checked: locale.value === code`, `onUpdateChecked` → `navigateTo(switchLocalePath(code))` (URL prefix updates; module writes the cookie). `UDropdownMenu` (Reka) already provides menu semantics, arrow keys, Escape-returns-focus, `aria-checked` (AC-A11Y-1/2 — verify).
- `layers/common/app/components/LanguageSwitcher.vue` (new): `UDropdownMenu` with globe icon trigger, `aria-label: t('common.changeLanguage')`, ≥24 px target (AC-A11Y-4); placed top-right on `layers/auth/app/pages/login.vue`.
- `frontend/app/app.vue`: `useLocaleHead()` → bind `htmlAttrs.lang` via `useHead` so `<html lang>` tracks the locale (AC-A11Y-3); page titles already via translated `useHead` (C.2).

### C.4 Locale-aware formatting + navigation (AC15, AC16)

- `layers/common/app/utils/date.ts` (new): `formatMonthYear(iso, locale)` using `Intl.DateTimeFormat`. Profile page `memberSince` and organization "Registered" computeds use it with `useI18n().locale` — the two hardcoded `'en-US'` calls in `profile.vue` are removed.
- Locale-aware routing everywhere in scope: `const localePath = useLocalePath()` in `layers/auth/app/middleware/auth.ts` (`navigateTo(localePath('/login'))`), `guest.ts` (`localePath('/dashboard')`), `useAuth` logout, login page post-login `navigateTo(localePath('/dashboard'))`, dashboard layout sidebar `links` (`to: localePath(...)` in a `computed`), sidebar header `navigateTo(localePath('/dashboard'))`, `error.vue` back link, `Header.vue` "Ir al Dashboard" `to` (chrome text stays Spanish; the target must still carry the prefix).

### C.5 e2e updates (AC11–AC16 coverage; resolved decision 11)

- `e2e/playwright.config.ts`: frontend project `use.locale` already `es-CO` (Phase 0); add cookie pinning helper if detection redirects interfere (`context.addCookies([{ name: 'i18n_redirected', value: 'es', ... }])` in `helpers.ts`).
- `e2e/frontend/helpers.ts`: update the `T` string map to the Spanish defaults — the only change smoke specs need.
- `e2e/frontend/landing.spec.ts`: keep Spanish assertions; add one test: `page.goto('/en')` renders the Spanish landing content without errors (AC14).
- `e2e/frontend/i18n.spec.ts` (new): login-page switcher → URL becomes `/en/login`, form strings switch to English; login in `en` → redirect preserves `/en/dashboard` (AC16); dashboard dropdown Language submenu switches strings + URL and persists across reload (AC13/AC11); `<html lang>` assertion (AC-A11Y-3); optional `@axe-core/playwright` scan of login + dashboard in both locales.

### C.6 Stage C gate

typecheck/lint/build green; full e2e green (updated `T` map + new i18n spec).

---

## Docs stage (AC17)

- `docs/ARCHITECTURE.md`: rewrite the Frontend section — layers tree (common/auth/accounts/cms/dashboard + root shell), fetcher/alias rules (`#api` = common HTTP stack only), the documented cross-layer exceptions (auth→accountsApi per contract; type-only `Profile` imports), Vue Query conventions (query-key enums, `isPending` skeletons, SSR landing on `useAsyncData`), i18n rules (prefix_except_default, es default, per-layer locale files, landing es-only); refresh "Current state".
- `frontend/CLAUDE.md`: update paths (`layers/<domain>/app/...`), add the contract's proposed rule ("module `api.ts` paths are relative to the fetcher baseURL; auth endpoints live under `accounts/` — no `auth/` mount"), Vue Query rules, and the UX-discovery i18n rule ("all user-facing strings via `t()`; dates via active locale, never `'en-US'`").
- `e2e/README.md`: document `E2E_USER_EMAIL`/`E2E_USER_PASSWORD` and the locale-pinning convention (there is no `e2e/CLAUDE.md` today; optionally note the `e2e/frontend/` layout vs. the root CLAUDE.md's `e2e/tests/<module>/` wording).

## AC coverage map

| Plan section | ACs |
| --- | --- |
| Phase 0 | AC1 (+ enables AC5) |
| A.1 tree/moves | AC2, AC4 |
| A.2 fetcher + authApi | AC3 (contract §fetcher, drift 1–3) |
| A.3 cmsApi landing | AC3, AC10 |
| A.4 aliases | AC2/AC3/AC4 |
| A.5 error.vue | AC6, AC-A11Y-7 |
| A.6 sidebar | AC6 |
| A.7 / B.4 / C.6 gates | AC5, AC7 |
| B.1–B.3 | AC8, AC9, AC10, AC-A11Y-8 |
| C.1 | AC11 |
| C.2 | AC12, AC-A11Y-5/6 |
| C.3 | AC13, AC-A11Y-1/2/3/4 |
| C.4 | AC15, AC16 |
| C.5 | AC11–AC16 verification, AC14 |
| Docs | AC17 |

## Risks / open items

1. **Baseline is red today** (missing dashboard mock/components; SSR `localStorage` crash on direct protected-route loads) — Phase 0 repairs are prerequisites for AC1, not scope creep.
2. **AC4 vs. contract surfaces table**: auth consumes `accountsApi`; resolved as the documented exception above (Docs stage records it).
3. **@nuxtjs/i18n v10 per-layer locale merge**: verified pattern in the module's layers docs, but keep the single-root-file fallback (C.1) if merge misbehaves.
4. **e2e credentials**: fixture password hash has no documented plaintext — env-var creds + one-time `make shell` password set.
