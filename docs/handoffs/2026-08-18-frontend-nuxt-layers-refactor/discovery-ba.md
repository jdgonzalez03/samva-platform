# ba discovery — frontend Nuxt Layers refactor + Vue Query + i18n

Summary: Assessed the ADR-0001 layers migration bundled with two new cross-cutting
capabilities (TanStack Vue Query, @nuxtjs/i18n) against the current frontend
(4 pages, ~15 components, 2 composables, 2 API modules). The refactor itself is
well-timed and cheap; the main risks are bundling three changes into one landing
and a thin test safety net.

## Concerns

- **Three features in one.** (1) File-move refactor (behavior-preserving), (2) a new
  data-fetching paradigm (Vue Query), (3) a user-visible capability (bilingual UI).
  If they land together, a regression can't be attributed to any one change and
  "behavior-preserving" can't be verified. All three are explicitly requested — this
  is sequencing advice, not a scope cut: land them as three sequential stages, each
  leaving tests green (layers → Vue Query → i18n).
- **Thin safety net.** Only two e2e specs exist (`e2e/frontend/landing.spec.ts`,
  `e2e/backend/api_cms.spec.ts`). Login, profile, and dashboard shell — the flows most
  disturbed by moving `useAuth`, middleware, and the fetcher — have **no** e2e
  coverage. There are no frontend unit tests at all (no Vitest configured). A
  whole-frontend file move with this net is risky; consider adding login/profile
  smoke e2e tests *before* the refactor (Open question 8).
- **Requirement 1 & 3 largely exist already** — this is relocation, not creation:
  `authApi` (`frontend/app/utils/api/auth/index.ts`) and `accountsApi` already export
  request objects over the shared `fetcher`; types already live per-domain in
  `frontend/shared/types/<domain>/`. The real gap is **cms**: the landing page calls
  `useFetch` directly (`frontend/app/pages/index.vue:10`), violating the existing
  fetcher rule — the refactor should give cms a proper `api.ts`.
- **Vue Query + SSR.** The landing page is server-rendered via `useFetch`. Migrating
  it to Vue Query requires the module's SSR hydration setup; keeping it on Nuxt's
  native SSR fetch is simpler and loses nothing today. Vue Query's real payoff is the
  upcoming sensors/predictions dashboards (polling, cache invalidation) — installing
  now is fine, but forcing it onto the SSR landing fetch is scope creep (Q5).
- **i18n reaches further than it looks.** Landing *content* comes from Wagtail in one
  language — translating it is backend work (e.g. wagtail-localize), not frontend
  i18n. Frontend i18n can only translate the "chrome" (header, footer, login form,
  toasts, zod validation messages — currently a hardcoded ES/EN mix). Route strategy
  (prefixes like `/en/login`) changes every URL and breaks hardcoded navigations
  (`navigateTo('/dashboard')`, middleware redirects) and e2e specs that assert
  Spanish text and unprefixed URLs.
- **Layer boundary gap in the ADR:** current code has a separate `accounts` domain
  (profile API + `useAccount`), but ADR 0001 only names `common/auth/cms/dashboard`.
  Where profile/accounts code lands must be decided, not improvised (Q9).
- Minor: root `CLAUDE.md` says e2e tests live in `e2e/tests/<module>/`; they actually
  live in `e2e/frontend/` and `e2e/backend/` — stale rule, see Proposed improvements.

## Recommendation

**Proceed** (ADR 0001 is accepted; all three pieces are explicitly requested), with
staged delivery: Stage A layers refactor (e2e green, zero visible change) → Stage B
Vue Query for client-side reads/mutations → Stage C i18n. Scope notes: keep the SSR
landing fetch out of Vue Query; declare CMS-content translation out of scope
(frontend translates chrome only); since the app has only ~4 pages, extract **all**
UI strings in Stage C — a hybrid translated/hardcoded state would cost more later.

## Open questions

1. Default locale: Spanish or English? (Today the UI is a mix — login is English,
   landing CMS content is Spanish.)
2. Locale routing: URL prefixes (`/en/login`) vs no prefix + cookie/browser
   detection? Prefixes are better for SEO on the public landing but touch every
   link, redirect, and e2e spec.
3. String extraction scope: confirm full extraction of all existing UI strings
   (recommended, small surface) vs scaffolding + key surfaces only?
4. Is translating Wagtail landing content explicitly **out** of scope for this
   feature (frontend chrome only)?
5. Vue Query scope: reads only, or also mutations (`useMutation` for login/profile
   update)? And confirm the SSR landing fetch stays on Nuxt `useFetch`/`useAsyncData`?
6. Where does the language switcher live — public Header only, or also the
   dashboard chrome? How is the choice persisted (cookie)?
7. Do existing e2e specs get updated for the chosen locale strategy, or must
   default-locale URLs/texts stay exactly as today so specs pass untouched?
8. Should login + profile smoke e2e tests be added *before* the refactor as a
   safety net? (Recommended.)
9. Which layer owns the `accounts`/profile code — `auth`, `dashboard`, or a new
   `accounts` layer mirroring the backend app?

## Proposed acceptance criteria

Provisional; criteria 6–10 hinge on the open questions noted.

1. Given the migration is complete, When inspecting `frontend/`, Then all domain code
   lives under `layers/common|auth|cms|dashboard` per ADR 0001 and root `app/` holds
   only the shell (`app.vue`, error page). (Q9 for accounts placement.)
2. Given any module needs the backend, When it issues a request, Then it goes through
   that module's `api.ts` object built on the common fetcher — including the landing
   page (no direct `useFetch`/`$fetch` for API calls).
3. Given the pre-refactor app, When Stage A lands, Then landing, login → dashboard
   redirect, logout, route protection (auth/guest middleware), and profile update
   behave identically and all existing e2e specs pass unmodified.
4. Given `npm run typecheck` and `npm run lint`, When run after each stage, Then both
   pass.
5. Given Stage B, When a component reads server data client-side, Then it uses a
   module composable wrapping `useQuery` with module-scoped query keys
   (`[<Module>QueryKey.ROOT, ...]`). (Scope of mutations/SSR per Q5.)
6. Given the app in the default locale (Q1), When a first-time visitor loads any
   page, Then all UI chrome strings render in that locale with no hardcoded strings
   remaining in migrated surfaces (Q3).
7. Given the language switcher (Q6), When the user selects the other language, Then
   all extracted strings switch — including toasts and form validation messages — and
   the choice persists across reloads.
8. Given the landing page in either locale, When CMS content renders, Then the body
   comes from Wagtail unchanged (content translation out of scope, Q4).
9. Given the chosen route strategy (Q2), When navigating any route including
   redirects from middleware, Then URLs follow the strategy consistently and no
   navigation 404s.
10. Given the feature is done, When reading `docs/ARCHITECTURE.md` and
    `frontend/CLAUDE.md`, Then both reflect the layers layout, Vue Query conventions,
    and i18n rules.

## Proposed improvements

- Root `CLAUDE.md` (E2E section): the rule says Playwright tests live in
  `e2e/tests/<module>/` and mentions helpers in `e2e/helpers/`; the repo actually
  uses `e2e/frontend/` and `e2e/backend/` and has no `e2e/helpers/`. Update the rule
  to match reality (or decide the layout and migrate) — stale paths misdirect every
  agent that writes e2e tests.
