# Spec — Frontend Nuxt Layers refactor + Vue Query + i18n

Slug: `2026-08-18-frontend-nuxt-layers-refactor`
Upstream: [ADR 0001](../../adr/0001-frontend-modular-architecture-nuxt-layers.md) (Accepted, authoritative), `discovery-ba.md`, `discovery-ux.md`.
Acceptance criteria: see [acceptance-criteria.md](acceptance-criteria.md) — the behaviour source of truth.

## Goal

Complete the ADR 0001 migration: restructure `frontend/` into self-contained domain
modules under `layers/`, each owning its pages, components, composables, `api.ts`,
types, and constants — built on the common fetcher. Introduce TanStack Vue Query for
client-side data fetching and @nuxtjs/i18n for a bilingual (es/en) dashboard + login.

## In scope

### Stage A — Layers refactor (behavior-preserving)

- Restructure `frontend/` per ADR 0001 into `layers/common`, `layers/auth`,
  `layers/accounts`, `layers/cms`, `layers/dashboard`; root `app/` reduced to the
  shell (`app.vue`, `error.vue`).
- **`layers/accounts` is a new layer** (resolved decision) owning the profile page,
  `accountsApi`, `useAccount`, and accounts types — mirroring the backend Django app.
- Each domain layer owns its full vertical slice: pages, components, composables,
  middleware, `api.ts` (request object over the common `fetcher`), types, constants.
- `layers/common` owns the HTTP stack (`fetcher`, `$api` plugin, tokens, errors),
  shared UI (Header/Footer/Logo), global layouts, shared types/utils.
- cms gets a proper `api.ts` (`cmsApi`); the landing page stops calling `useFetch`
  directly (current violation of the fetcher rule) — SSR stays via
  `useAsyncData` wrapping `cmsApi`.
- A designed `error.vue` (404/error page) in the root shell.
- Hide the dead sidebar links (`/dashboard/history`, `/dashboard/predictions`) until
  those pages exist.
- Aliases (`#api`, `#shared`) re-mapped to the new locations.

### Stage B — TanStack Vue Query

- Install `@tanstack/vue-query`; module composables wrap `useQuery` for client-side
  reads and `useMutation` for writes (login/logout/profile update), with
  module-scoped query keys (`[<Module>QueryKey.ROOT, ...]` enums per module).
- SSR landing fetch stays on `useAsyncData` + `cmsApi` — **not** Vue Query.
- Existing skeletons/loading states map to `isPending`; errors surface accessibly.

### Stage C — i18n (es/en)

- Install `@nuxtjs/i18n`. Locales: `es` (default) and `en`.
- Routing: `prefix_except_default` — `/` = Spanish unprefixed, `/en/...` = English.
  Browser-language detection on first visit, persisted in a cookie.
- Translation scope: **dashboard area + login page** (labels, nav, toasts, zod
  validation messages, titles, error page). The public landing — including its
  Header/Footer — stays fixed Spanish; Wagtail CMS content translation is out of scope.
- Language switcher: "Language" submenu in the dashboard user dropdown (mirroring the
  existing "Appearance" pattern) + a switcher on the login page. Cookie persistence.
- Locale-aware date formatting (profile "member since" — no hardcoded `'en-US'`).
- Middleware redirects (`auth`/`guest`) and internal navigations must be
  locale-aware (use i18n route helpers).

### Safety net (before Stage A)

- Add e2e smoke specs first: login → dashboard redirect, logout, route protection
  (auth/guest middleware), profile update. They must pass on the current layout, then
  keep passing after each stage.

### Docs

- Update `docs/ARCHITECTURE.md` and `frontend/CLAUDE.md` to the layers layout, Vue
  Query conventions, and i18n rules once landed.

## Out of scope

- Translating Wagtail/CMS landing content (backend work, future feature).
- Translating the public landing chrome (Header/Footer stay Spanish).
- Building `/dashboard/history` and `/dashboard/predictions` pages.
- Persisting language preference to the backend user profile (cookie only).
- Migrating the SSR landing fetch to Vue Query.
- Backend changes of any kind — no new endpoints; existing API is consumed as-is.

## UX notes

- Switcher mirrors the existing `DropDownUser` "Appearance" submenu pattern — no new
  widget style. Options labeled in their own language ("Español", "English").
- Vue Query introduces cached back-navigation + background refetch; skeletons must
  bind to `isPending` so loading states don't regress.
- Accessibility ACs (WCAG 2.2 AA) are first-class: see the `Accessibility` section of
  `acceptance-criteria.md` (AC-A11Y-1 … AC-A11Y-8).

## Resolved decisions

1. **URL strategy**: locale prefixes, `prefix_except_default`, Spanish default
   (`/` = es, `/en/...` = en), browser detection + cookie.
2. **CMS content**: out of scope — landing stays Spanish in both locales.
3. **Translation boundary**: dashboard + login; public landing chrome excluded.
4. **Accounts placement**: new `layers/accounts` layer (not folded into auth or
   dashboard).
5. **Vue Query scope**: queries + mutations for client-side; SSR landing excluded.
6. **Switcher**: dashboard user-dropdown submenu + login page; cookie persistence
   only (no backend profile field).
7. **Dead sidebar links**: hidden until the pages exist.
8. **Safety net**: login/profile/route-protection e2e smoke specs added before the
   refactor.
9. **Delivery**: three sequential green stages — A layers, B Vue Query, C i18n; every
   stage ends with typecheck, lint, build, and e2e green.
10. **String extraction**: full extraction for all in-scope surfaces (dashboard +
    login) — no hybrid hardcoded/translated state there.
11. **e2e locale strategy**: specs pin the default locale explicitly and select by
    role; existing specs updated as needed for prefix routing.
