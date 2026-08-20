# frontend review — Nuxt Layers refactor + Vue Query + i18n (Stages A–C)

Verdict: **CHANGES REQUESTED**

Reviewed: `frontend/app/`, `frontend/layers/**`, `frontend/nuxt.config.ts`, `e2e/frontend/**`,
`e2e/playwright.config.ts` against `spec.md`, `acceptance-criteria.md`, `contract.md`, `plan.md`,
the three stage handoffs, and ADR 0001.

Verification re-run by the reviewer (2026-08-19): `npm run typecheck` → exit 0,
`npm run lint` → exit 0, `npx playwright test` → **28/28 passed** (backend + frontend projects).
The blocking issues below are code/coverage findings, not gate failures.

Overall this is high-quality work: the layer split is clean (no leftover `#shared/types`,
`app/utils/api`, or `app/composables` references anywhere — grep-verified), the contract is
implemented exactly (relative paths, `accounts/login/`, per-endpoint error shapes read correctly
in `login.vue:59-62`), the isomorphic `$api` plugin is correct in both topologies, the query-key
design is hierarchical and shared through a single `profileQueryOptions()` factory, and the i18n
extraction is thorough with strong e2e assertions (keyboard, `aria-checked`, `<html lang>`,
cookie persistence).

## Blocking

1. **`layers/accounts/app/pages/dashboard/profile.vue:210-228` — avatar upload control is not
   keyboard operable and has no accessible name (WCAG 2.1.1 / 4.1.2, AA — touched surface).**
   The file input uses `class="hidden"` (`display: none`), and its parent is
   `UButton as="label"`. Empirically verified against the running app: the input computes to
   `display: none`, the rendered `<label>` has `tabIndex: -1`, its accessible name is empty
   (the `aria-label` sits on the display-none input, which is removed from the accessibility
   tree, so it exposes nothing), and 60 Tab presses never reach the control. Mouse users can
   change their avatar; keyboard and screen-reader users cannot at all. The Stage C handoff's
   claim that the `aria-label` on this input addresses the icon-only control is therefore not
   true in practice.
   **Fix:** make the input visually-hidden-but-focusable (`sr-only` instead of `hidden`) so it
   keeps focus, a visible focus ring (style the wrapping label via `:focus-within` or move the
   ring to the input), and its `aria-label`; Enter/Space on a focused file input opens the
   picker natively. Add the keyboard assertion to `e2e/frontend/profile.spec.ts`.

2. **`frontend/app/error.vue` — new user-facing 404/error page has zero automated test coverage
   (AC6, AC-A11Y-7).** Stage A verified it only with a manual `curl`; no Playwright spec visits
   an unknown route, asserts the heading/translated title, or exercises the "Volver al inicio /
   Back to home" link (root `CLAUDE.md`: every multi-step user-facing feature needs a Playwright
   test). AC6 and AC-A11Y-7 are currently signed off with no regression protection — a rename of
   a `common.error.*` key or a broken `clearError` redirect would ship silently.
   **Fix:** add an `e2e/frontend/error.spec.ts` (or fold into `i18n.spec.ts`): `goto('/ruta-x')`
   → `<h1>` "Página no encontrada" + working back-home link → lands on `/`; repeat for
   `/en/ruta-x` asserting the English strings and `/en` back-target.

3. **Vue Query error/retry states have zero test coverage (AC-A11Y-8).** The new fallbacks —
   `layers/accounts/app/pages/dashboard/profile.vue:135-165` ("Could not load your profile" +
   Retry) and `layers/dashboard/app/layouts/dashboard.vue:83-97` ("Profile unavailable" + Retry)
   — are new behavior added by Stage B and are exercised by no spec (Stage B's handoff verified
   them manually with the backend stopped). They are cheaply testable without touching the
   stack: intercept with `page.route('**/accounts/me/', route => route.abort())` after login,
   assert the text fallback renders, then unroute and click Retry to assert recovery.
   **Fix:** add that spec; it also locks in the AC-A11Y-8 "text alternative, not colour alone"
   guarantee.

## Non-blocking

1. `layers/dashboard/app/components/DropDownUser.vue:23` — `const avatarUrl =
   getImageUrl(props.user.farmer.avatar)` is computed once at setup; after an avatar upload the
   profile query refetches and `props.user` changes, but the sidebar avatar stays stale until
   remount. Make it `computed(() => getImageUrl(props.user.farmer.avatar))`.
2. `layers/dashboard/app/layouts/dashboard.vue:46-49` — the sidebar "SAMVA" header is a
   click-only `<div @click="navigateTo(...)">`: not focusable, no role. A keyboard path to
   `/dashboard` exists via the nav link, so functionality is not lost, but replace it with
   `<NuxtLink :to="localePath('/dashboard')">` to remove the mouse-only affordance.
3. Cross-layer exception widened beyond the contract wording: the auth layer now consumes the
   accounts layer's **composables** (`useProfileQuery`, `profileQueryOptions` — auto-imported in
   `layers/auth/app/composables/useAuth.ts:12,20` and `plugins/auth-init.client.ts:16`), not just
   `accountsApi`. Direction (auth → accounts) and rationale (single cache entry) are sound and
   documented in the Stage B handoff, but the Docs stage must record this exact exception in
   `docs/ARCHITECTURE.md`/`frontend/CLAUDE.md` so it doesn't silently grow.
4. Fragile cross-layer relative imports of the common icon:
   `layers/auth/app/pages/login.vue:4` and `layers/dashboard/app/layouts/dashboard.vue:2`
   (`../../../common/app/components/icons/TractorIcon.vue`; the latter also misspells the local
   name `TracktorIcon`). Direction is sanctioned (domain → common), but consider a `#common`
   alias or the auto-import name so a common-layer move doesn't break three layers.
5. `layers/cms/app/pages/index.vue:8-17` — no error/empty state: if `cmsApi.getLanding()`
   rejects, the landing renders an empty `<div>` with no message. Read `error` from
   `useAsyncData` and `throw createError(...)` (the designed `error.vue` would then render).
6. `layers/dashboard/app/components/dashboard/FarmsMenu.vue:8-31` — mounted in the sidebar with
   hardcoded mock farm names and third-party avatar URLs; when `collapsed`, the trigger has no
   accessible name (label becomes `undefined`, avatar only). Worth an `aria-label` and a
   `TODO`-free path to real data. Sibling `FarmStats.vue` is dead (unmounted) and carries
   comments that restate the code (`// Generar valor aleatorio…`, violates the comment litmus) —
   translate-or-delete when the dashboard work resumes.
7. `layers/common/app/utils/api/tokens.ts:42` — refresh path `'/accounts/token/refresh/'` keeps
   a leading slash, deviating from the contract's "no leading slash" convention (works via
   ofetch join, but it's the only inconsistent path).
8. AC15/AC16 gaps in e2e: no assertion on the locale-formatted "member since" date, and logout
   from `/en/dashboard` preserving `/en/login` is untested (only login-side prefix preservation
   is). Cheap one-line additions to `i18n.spec.ts`.
9. Pre-existing oddity preserved by the refactor (fine for a behavior-preserving stage, flag for
   later): `layers/dashboard/app/layouts/dashboard.vue:8-11` force-switches `light` → `dark` on
   every mount, fighting both the login layout (`layouts/login.vue:4-6` forces `light`) and the
   user's explicit "Appearance → Light" choice.
10. `profile.vue:101-111` maps empty strings to `undefined`, so a user can never clear a saved
    field (pre-existing behavior; note for a future accounts iteration).

## AC spot-check (reviewer-verified against code/tests, not just the handoffs)

- **AC2 ✓** tree verified: root `app/` = `app.vue` + `error.vue` only; all domain code under
  `layers/{common,auth,accounts,cms,dashboard}`.
- **AC3 ✓** grep-verified: no `useFetch`/raw `$fetch` outside the sanctioned
  `refreshAccessToken`; landing via `useAsyncData('cms-landing', () => cmsApi.getLanding())`.
- **AC4 ✓** per-layer types/constants in-layer; exceptions as documented (see non-blocking 3).
- **AC5/AC7 ✓** typecheck/lint exit 0 and 28/28 e2e re-run by reviewer.
- **AC6 ◐** code correct (links removed from `dashboard.vue`; designed `error.vue` with locale-
  aware home link) but **no automated test** — blocking 2.
- **AC8 ✓** `useProfileQuery` with `[AccountsQueryKey.ROOT, AccountsQueryKey.ME]`; skeletons on
  `isPending` (`profile.vue:134`, `dashboard.vue:72`), both with `aria-busy`.
- **AC9 ✓** login/logout/update are mutations; update `onSuccess` returns
  `invalidateQueries({ queryKey: [ROOT] })` (correct return-the-promise semantics); logout
  clears tokens then cache; all four toasts preserved and translated.
- **AC10 ✓** cms page untouched by Vue Query; SSR confirmed (curl 200, hero text in source).
- **AC11 ✓** config (`prefix_except_default`, `i18n_redirected`, fallback es) + e2e asserts
  `/` → `/en` after choosing English.
- **AC12 ✓** extraction complete on in-scope surfaces (greps for `en-US`, heroicons, hardcoded
  copy clean); FarmsMenu mock farm names are data, not chrome (non-blocking 6).
- **AC13 ✓** both switchers asserted in e2e (strings, URL prefix, reload persistence).
- **AC14 ✓** e2e: `/en` renders Spanish landing, zero page errors.
- **AC15 ✓ (code)** `formatMonthYear(iso, locale.value)` both call sites; no e2e assertion
  (non-blocking 8).
- **AC16 ✓** `localePath` in auth/guest middleware, logout, post-login, sidebar links/header,
  error back link, landing header; e2e covers login-side prefix preservation.
- **AC-A11Y-1/2/3 ✓** directly asserted in `i18n.spec.ts` (focus/Enter/Escape/focus-return,
  `menuitemcheckbox` + `aria-checked`, `<html lang>` es→en).
- **AC-A11Y-4 ✓** switcher triggers: `LanguageSwitcher.vue:29` `aria-label`, default `UButton`
  ≥ 24px. (The avatar control's failure is a separate surface — blocking 1.)
- **AC-A11Y-5 ✓** computed zod schema wired via `:schema` (`login.vue:39-44,82`); Nuxt UI
  `UFormField` supplies `aria-describedby`/`aria-invalid`; messages rebuild per locale.
- **AC-A11Y-6 ✓** toasts call `t()` at fire time inside the `UApp` live region; `UApp :locale`
  bound in both `app.vue` and `error.vue`.
- **AC-A11Y-7 ◐** code correct (translated title/h1, keyboard-operable button) — untested,
  blocking 2.
- **AC-A11Y-8 ◐** `aria-busy` skeletons + text-and-button error fallbacks present — untested,
  blocking 3.
- **AC self-check honesty:** overall accurate and unusually detailed; the one material misclaim
  is Stage C's assertion that the avatar-upload `aria-label` addressed that control's
  accessibility (blocking 1 shows it is not exposed at all).

## Proposed improvements

- Rule: "A visually hidden file input (or any hidden-but-interactive control) must use `sr-only`,
  never `hidden`/`display:none` — display-none removes it from tab order **and** the
  accessibility tree, so its `aria-label` is dead; keep the focus ring visible via the input or
  `:focus-within` on the wrapper." → `frontend/CLAUDE.md` (UI components section).
- Rule: "Values derived from props or query data must be `computed()` — never
  `const x = fn(props.y)` at setup, which freezes the first value (e.g. avatars/URLs going stale
  after a refetch)." → `frontend/CLAUDE.md` (Composables & state section).
- Rule: "Error/404 pages and failure-path UI states (query error fallbacks, retry affordances)
  count as multi-step user-facing features: they need a Playwright spec in the same stage —
  force the failure with `page.route(...)` interception; manual `curl`/backend-stopped smoke
  does not satisfy the test gate." → root `CLAUDE.md` E2E section (refines the existing rule) or
  `e2e/README.md`.
