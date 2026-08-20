# frontend handoff — Phase 0.1 baseline repair (frontend-nuxt-layers-refactor)

Summary: Repaired the red pre-refactor baseline: removed the unresolvable dashboard mock/component usage, made token access + auth/guest middleware SSR-safe, fixed the landing e2e assertion for anonymous users, and cleared 20 pre-existing lint errors so typecheck/lint/build are all green. No layers/ restructuring (Stage A not started).

Files changed:
- `frontend/app/pages/dashboard/index.vue` — stripped `mockFarms` import and `DashboardMapView`/`DashboardLotList`/`DashboardSensorCard` markup; kept `UDashboardNavbar` + placeholder body; added `useHead` title. No mock files created.
- `frontend/app/utils/api/tokens.ts` — `getAccessToken`/`getRefreshToken` return `null` unless `import.meta.client`.
- `frontend/app/middleware/auth.ts`, `guest.ts` — early `return` on `import.meta.server`; auth decision after hydration.
- `e2e/frontend/landing.spec.ts` — last test now expects redirect to `/login` for anonymous visitors.
- Lint-only baseline repairs (build gate, no behavior change intended):
  - `app/utils/api/fetcher.ts` — replaced `any`s with `NitroFetchOptions<NitroFetchRequest>` / `RequestBody` types; typed 401 catch.
  - `app/utils/api/auth/index.ts` — dropped unused `AuthResponse` import.
  - `app/pages/login.vue` — imports hoisted above `definePageMeta`; unused zod schema renamed `_schema` (still NOT wired into `UAuthForm` — intentionally no behavior change; Stage A/C wires it); typed catch.
  - `app/pages/index.vue` — imports hoisted; `v-if`+`v-for` on same `<template>` → `v-for="block in data?.body ?? []"`.
  - `app/layouts/default.vue`, `app/layouts/login.vue` — wrapped in single root div (Nuxt layout single-root rule).
  - `app/pages/dashboard/profile.vue` — removed root-level template comment breaking `vue/no-multiple-template-root`.
  - `app/components/cms/hero-section.vue` — dropped unused `StreamBlock` import; attribute order.
  - `app/components/cms/feature-highlight.vue` — `imagen` computed read via `.value` (`vue/no-ref-as-operand`); note: previously the ref object was always truthy, so `contentCenter` was always `''`; now text correctly centers when no image — a latent-bug fix, visual only when CMS block has no image.
  - `app/components/dashboard/FarmStats.vue` — `useAsyncData<any[]>` → typed `FarmStat[]` (component currently unmounted).

Routes/UI: no new routes. `/dashboard` now renders navbar + placeholder text instead of failing to build.

Verification (from `frontend/`): `npm run typecheck` ✓, `npm run lint` ✓ (0 problems), `npm run build` ✓ (exit 0), `npm run format:check` ✓. e2e not run per dispatch (orchestrator runs it; docker stack still building). No frontend unit-test runner exists yet (no Vitest/`test` script) — plan gate is typecheck/lint/build.

Gotchas:
- Auth/guest redirects now happen only client-side after hydration — a direct SSR load of `/dashboard` renders the shell first, then redirects. The route-protection e2e must assert the final URL (Playwright's `toHaveURL` auto-waits, so this is fine).
- The login zod schema is still dead code (`_schema`); client-side validation is NOT active — invalid-credential e2e flows will always reach the server and get the error toast.

Surprises:
- The lint baseline was red with 20 pre-existing errors in files outside the three planned repairs; fixed them minimally because the Phase 0 gate requires lint green. All fixes are behavior-preserving except the `feature-highlight.vue` latent-bug fix noted above.

Contract deviations: none (no API surface touched).

AC self-check: AC1 enabled (green typecheck/lint/build baseline + corrected landing spec; the 0.2 smoke specs are the orchestrator's next step). AC7 ✓ for this phase. All other ACs out of scope for Phase 0.1.

Decisions:
- Did not wire `_schema` into `UAuthForm` (would change submit behavior mid-baseline); left for Stage A/C.
- Kept `FarmStats.vue`/`FarmsMenu.vue` untouched behaviorally (unmounted; Stage A moves them).

For next agent (QA/orchestrator): run e2e — `landing.spec.ts` last test now expects `/login`; then add the 0.2 smoke specs per plan. Manual smoke: direct browser load of `http://localhost:3000/dashboard` while logged out must SSR without a 500 and land on `/login`.

## Proposed improvements
- Rule: "Browser-only APIs (`localStorage`, `window`) must be guarded with `import.meta.client`; route middleware that depends on them returns early on `import.meta.server` — auth decisions happen client-side after hydration." → `frontend/CLAUDE.md` (HTTP & API layer / new SSR section).
- Rule: "When typing wrappers around the `$api` (`$fetch.create`) instance, use `NitroFetchOptions<NitroFetchRequest>` from `nitropack`, not ofetch's `FetchOptions` (incompatible `method` union)." → `frontend/CLAUDE.md`.
