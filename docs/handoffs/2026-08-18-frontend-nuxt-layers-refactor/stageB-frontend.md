# frontend handoff — Stage B: TanStack Vue Query (AC8–AC10, AC-A11Y-8)

Summary: Introduced `@tanstack/vue-query` (5.101.4) behind the existing composable APIs. Profile read is now a shared `useQuery` (single cache entry feeds sidebar, dropdown, and profile page); login/logout/profile-update are `useMutation`s with the same toasts and redirects. SSR landing untouched (`useAsyncData` + `cmsApi`). All gates green; behavior identical (23/23 e2e, two consecutive runs).

## Files changed

- `frontend/package.json` — `@tanstack/vue-query` added.
- `frontend/layers/common/app/plugins/vue-query.ts` — new universal plugin.
- `frontend/layers/accounts/app/constants/query-keys.ts` — new `AccountsQueryKey` enum.
- `frontend/layers/accounts/app/composables/useAccount.ts` — rewritten: `profileQueryOptions`, `useProfileQuery`, `useUpdateProfileMutation` (old `useAccount` removed; profile page was its only consumer).
- `frontend/layers/auth/app/composables/useAuth.ts` — rewritten around mutations + shared profile query.
- `frontend/layers/auth/app/plugins/auth-init.client.ts` — session restore via `prefetchQuery`.
- `frontend/layers/accounts/app/pages/dashboard/profile.vue` — `isPending` skeleton, error + retry state, mutation-driven save.
- `frontend/layers/accounts/app/components/dashboard/ProfileSkeleton.vue` — `aria-busy="true"` wrapper.
- `frontend/layers/dashboard/app/layouts/dashboard.vue` — footer skeleton on `profilePending` (+`aria-busy`), text "Profile unavailable / Retry" error fallback.

## Query-key design

- `AccountsQueryKey { ROOT = 'accounts', ME = 'me' }`; profile key = `[ROOT, ME]`; mutations invalidate `[ROOT]`.
- `profileQueryOptions()` in `layers/accounts/app/composables/useAccount.ts` is the single definition (key + `queryFn: accountsApi.getMe`) reused by `useProfileQuery`, login's `fetchQuery`, and auth-init's `prefetchQuery` — all hit one cache entry.
- No `AuthQueryKey` enum: auth has only mutations (no client reads), and mutations need no keys. Plan B.2 listed it "if needed" — add it when auth grows a query. cms/dashboard: none (no client reads).
- Plain object factory instead of the `queryOptions()` helper: its `DataTag`-branded queryKey does not survive `{ ...spread, enabled }` under vue-tsc (type error), and we get full inference without it.

## How auth state flows now

- `vue-query` plugin (common, universal, named): per-request `QueryClient` (`staleTime` 30s, `retry` 1), installs `VueQueryPlugin`, provides `$queryClient`. No SSR dehydration — every query is client-gated.
- `useProfileQuery` is `enabled: () => hasTokens()` (getter): SSR-inert (tokens are `null` on server) and token-fresh at observer creation.
- **Login** (`useAuth().login` → `mutateAsync`): `authApi.login` → `setTokens` → awaited `queryClient.fetchQuery(profileQueryOptions())` in `onSuccess`, so the button spinner covers the profile fetch and a failed fetch rejects `login()` exactly like before (login page toasts unchanged).
- **Logout** (mutation, client-side only per contract): `clearTokens()` → `router.push('/login')` → `queryClient.removeQueries()` (cache cleared after navigation so no observer refetches token-less).
- **Session restore** (`auth-init.client`, `dependsOn: ['api', 'vue-query']`): `hasTokens()` → awaited `prefetchQuery`; since `prefetchQuery` swallows errors, it then checks the query state — on `'error'` it clears tokens, empties the cache, and navigates to `/login` (preserves the old `fetchMe → logout` behavior for dead sessions).
- `user` / `isAuthenticated` are computeds over `profileQuery.data` — sidebar footer, `DropDownUser`, and profile page all read the same cache entry. `useAuth` also exposes `profilePending`/`profileError`/`refetchProfile` so the dashboard layout needs no direct accounts-layer dependency.
- **Profile update**: `useUpdateProfileMutation` `onSuccess` returns `invalidateQueries([ROOT])`, so `mutateAsync` resolves only after the refetch — the success toast fires over fresh data (replaces the old `await fetchMe()`).

## Routes/UI

No new routes or entry points. New user-visible states only: profile page and sidebar footer now render an accessible query-error fallback ("Could not load your profile" + Retry / "Profile unavailable" + Retry) where previously a failed fetch left a permanent skeleton or forced logout.

## Gotchas

- The `vue-query` plugin must keep its name: `auth-init` declares `dependsOn: ['api', 'vue-query']`.
- `nuxtApp.$queryClient` is `unknown` in the plugin context despite the typed provide — cast to `QueryClient` (import type) where consumed outside components; inside components use `useQueryClient()`.
- `refetch`/`refetchProfile` handlers are wrapped to return `void` — vue-tsc rejects `Promise<QueryObserverResult>` from `@click`.
- First e2e run after the edits failed on the login click: cold Vite on-demand compile made hydration lose the pre-hydration submit click (dev-server-only; disappears once warm and cannot occur on a production build). Re-runs: 23/23 twice.

## Contract deviations

None — Vue Query wraps the exact `authApi`/`accountsApi` methods; no request/response shape changed (contract "Notes" honored).

## AC self-check

- AC8 ✓ — profile read via `useProfileQuery` (module composable, `[AccountsQueryKey.ROOT, AccountsQueryKey.ME]`); profile skeleton binds to `isPending`, sidebar footer to `profilePending`.
- AC9 ✓ — login/logout/profile update are `useMutation`s in module composables; all four toasts preserved verbatim; update invalidates `[AccountsQueryKey.ROOT]`; logout clears the whole cache.
- AC10 ✓ — `layers/cms/app/pages/index.vue` untouched; SSR curl still returns the CMS content.
- AC7 (stage gate) ✓ — typecheck/lint/build/format:check all green.
- AC-A11Y-8 ✓ — both skeleton wrappers carry `aria-busy="true"`; error states are text + labeled Retry `UButton` (keyboard-operable, visible focus ring, ≥24px target), never colour/icon alone (icon is `aria-hidden`).
- AC5-equivalent behavior parity ✓ — 23/23 e2e unmodified, two consecutive runs.

## Verification outputs

- `npm run typecheck` → exit 0; `npm run lint` → exit 0; `npm run build` → "Build complete!"; `npm run format:check` → "All matched files use Prettier code style!".
- `curl -s http://localhost:3000/ | grep -io 'agricultura de precisi.n' | head -1` → `Agricultura de Precisión` (AC10).
- `npx playwright test` (e2e/) → **23 passed** (runs 2 and 3; run 1 had the cold-compile race above).
- No frontend unit-test runner exists (no Vitest script / `frontend-test` make target) — per Phase 0/Stage A precedent the stage gate is typecheck/lint/build/format + e2e.

## Decisions

- Kept `useAuth`'s public surface (`user`, `isAuthenticated`, `loading`, `login`, `logout`) so login page and `DropDownUser` needed zero changes; added `profilePending`/`profileError`/`refetchProfile` for the dashboard layout instead of letting the dashboard layer consume accounts composables directly (no new cross-layer edge beyond the contract-sanctioned ones).
- Invalidate-only on profile update (per plan) — no `setQueryData` priming; the awaited refetch keeps the old "toast after fresh data" timing.
- Sidebar footer got a compact error fallback too (AC-A11Y-8 "any query error state"), not just the profile page.
- Error/retry strings are English like the rest of the dashboard chrome — extracted in Stage C with everything else.
- Stage C (i18n) NOT started, per dispatch.

## For next agent

QA flow: login `juan.perez@email.com` → `/dashboard` + "Welcome back" toast (button spinner covers profile fetch); sidebar footer shows user dropdown (button "Pérez"); `/dashboard/profile` shows skeleton (`aria-busy`) then form; edit First Name → "Save changes" (button `aria-busy`/spinner while saving) → "Profile updated" toast → reload → persists; navigate Dashboard ↔ Profile — profile renders instantly from cache (< 30s staleTime, no skeleton flash); hard reload `/dashboard` → session restored (auth-init prefetch); "Log out" from dropdown → `/login`, `localStorage` tokens gone; with backend stopped, `/dashboard/profile` shows "Could not load your profile" + Retry button (keyboard-focusable).

## Proposed improvements

- Rule: "Vue Query: one `<x>QueryOptions()` factory per query (plain object + `as const` key, not the `queryOptions()` helper — its DataTag typing breaks on spread) shared by `useQuery`, `fetchQuery`, and `prefetchQuery`; keys come from the module's `<Module>QueryKey` enum; skeletons bind to `isPending`; template event handlers must wrap `refetch`/`mutateAsync` to return void." → `frontend/CLAUDE.md` (new Vue Query section — the Docs stage already plans one; fold this in).
- Rule: "Injections provided by named object plugins are typed `unknown` on `nuxtApp.$x` inside other plugins — cast via an imported type there; inside components prefer the library composable (e.g. `useQueryClient()`)." → `frontend/CLAUDE.md`.
- Rule: "After editing frontend code, warm the dev server (one page load) before running the e2e suite — cold Vite on-demand compile can swallow pre-hydration clicks and fail the first spec spuriously." → root `CLAUDE.md` (E2E section) or a future `e2e/CLAUDE.md`.
