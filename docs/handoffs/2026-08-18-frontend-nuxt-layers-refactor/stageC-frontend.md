# frontend handoff — Stage C: i18n es/en (AC11–AC16, AC-A11Y-1..7)

Summary: Installed `@nuxtjs/i18n` (10.6.0) with `prefix_except_default` (`/` = es, `/en/...` = en), browser detection + `i18n_redirected` cookie. Full string extraction for login + dashboard area + error page via **per-layer locale files**; language switcher in the dashboard user dropdown (mirrors "Appearance") and on the login page; all in-scope navigation is locale-aware (`useLocalePath`); dates via `Intl` per active locale. All gates green; e2e 28/28 (two consecutive runs).

## Files changed

Frontend:

- `frontend/package.json` — `@nuxtjs/i18n` added.
- `frontend/nuxt.config.ts` — module + i18n config (locale metadata, strategy, detection).
- `frontend/app/app.vue` — `useLocaleHead` → `<html lang>`; `UApp :locale` (Nuxt UI built-in strings follow locale).
- `frontend/app/error.vue` — translated title/heading/description/back link; own `<html lang>` + `UApp :locale` (error.vue replaces app.vue).
- `frontend/layers/{common,auth,accounts,dashboard}/nuxt.config.ts` — per-layer `i18n.locales` file declarations.
- `frontend/layers/{common,auth,accounts,dashboard}/i18n/locales/{es,en}.json` — 8 new message files (one namespace per layer: `common.*`, `auth.*`, `accounts.*`, `dashboard.*`).
- `frontend/layers/common/app/components/LanguageSwitcher.vue` — new (globe trigger + checkbox menu).
- `frontend/layers/common/app/utils/date.ts` — new `formatMonthYear(iso, locale)` (Intl.DateTimeFormat).
- `frontend/layers/common/app/components/Header.vue` — `:to="localePath('/dashboard')"` (text stays Spanish).
- `frontend/layers/auth/app/pages/login.vue` — full extraction; zod schema now a `computed` built with `t()` and **wired into `UAuthForm` via `:schema`**; post-login `navigateTo(localePath('/dashboard'))`; `LanguageSwitcher` top-right.
- `frontend/layers/auth/app/middleware/{auth,guest}.ts` — locale-aware redirects.
- `frontend/layers/auth/app/composables/useAuth.ts` — logout pushes `localePath('/login')`.
- `frontend/layers/auth/app/plugins/auth-init.client.ts` — locale-aware dead-session redirect; `dependsOn` now `['api', 'vue-query', 'i18n:plugin']`.
- `frontend/layers/dashboard/app/layouts/dashboard.vue` — nav/help links as `computed` with `t()` + `localePath`; header click + footer error strings.
- `frontend/layers/dashboard/app/components/DropDownUser.vue` — extracted labels + new "Language" submenu (mirrors Appearance checkbox pattern; `switchLocalePath`).
- `frontend/layers/dashboard/app/pages/dashboard/index.vue` — navbar/welcome/title extracted.
- `frontend/layers/accounts/app/pages/dashboard/profile.vue` — full extraction (headings, labels, placeholders, selects as `computed`, badge, toasts, error/retry, title); `formatMonthYear` with active locale (both `'en-US'` calls removed); a11y: `aria-label` on the icon-only avatar-upload input.
- `frontend/layers/accounts/app/components/dashboard/ProfileSkeleton.vue` — navbar title via `t()`.

E2E:

- `e2e/frontend/helpers.ts` — `T` map switched to Spanish defaults; new `T_EN`/`SWITCHER` maps for the i18n specs.
- `e2e/frontend/i18n.spec.ts` — new (5 tests, see AC check).
- `e2e/playwright.config.ts` — `workers: 1` (fullyParallel:false only serializes within a file; login-sharing spec files raced across workers).

## i18n architecture

**Per-layer locale files worked** (no fallback needed): root `nuxt.config.ts` holds locale *metadata* only (`code`/`language`/`name`), each in-scope layer declares `i18n: { locales: [{ code, file }] }` and ships `layers/<name>/i18n/locales/{es,en}.json`. @nuxtjs/i18n v10 merges entries by locale code and concatenates layer files (verified in the built server chunks and at runtime in both locales). `cms` ships no files (landing fixed Spanish, AC14). Each file only contains its own namespace, so merges never collide.

## Switcher implementation

- Dashboard: "Language" submenu in `DropDownUser` — `type: 'checkbox'` children built from `locales` (labels in their own language), `checked: locale === code`, `onUpdateChecked → navigateTo(switchLocalePath(code))`, `onSelect` preventDefault — exact mirror of "Appearance". Menu semantics/arrow keys/Escape/aria-checked come from `UDropdownMenu` (Reka).
- Login: `LanguageSwitcher` (common layer) — icon-only `UButton` trigger (globe, `aria-label` `common.changeLanguage`, ≥24px), same checkbox items, placed top-right of the login container.

## Routes/UI

New routes: `/en`, `/en/login`, `/en/dashboard`, `/en/dashboard/profile` (auto-generated `___en` variants). Entry points: globe button top-right on `/login`; "Idioma"/"Language" submenu in the dashboard user dropdown.

## Gotchas

- **`@` in messages crashes vue-i18n** ("Invalid linked format", SSR 500): literal `@` must be written `{'@'}` in locale JSON (email placeholders).
- The i18n runtime plugin is named `i18n:plugin`; `auth-init` depends on it — don't rename either.
- After a locale switch from the dashboard dropdown, the menu **stays open** (layout persists, strings switch in place) and its portal overlay aria-hides the page — e2e must press Escape before locating sidebar elements.
- The dev server needed a manual `touch nuxt.config.ts` to pick up newly added layer i18n configs/locale files (config-time additions aren't hot-reloaded reliably). Dev server survived; still running on :3000.
- Login client-side validation is now ACTIVE (schema was dead `_schema` since Phase 0): empty/invalid-format submissions are blocked client-side with translated messages; the invalid-credentials e2e still reaches the server (valid shape).
- `detectBrowserLanguage.redirectOn: 'root'`: cookie redirect only fires on `/` — `/en` deep links are never rewritten.

## Contract deviations

None — no API surface touched (frontend + e2e only, per contract).

## AC self-check

- AC11 ✓ — prefix_except_default; browser detection with cookie (`i18n_redirected`, fallback es); e2e: after choosing en, `goto('/')` redirects to `/en`.
- AC12 ✓ — full extraction: login (labels/placeholders/zod/toasts/title), dashboard layout (nav/help/footer states), dashboard index, DropDownUser, profile (everything incl. skeleton navbar, error/retry, selects, badge, dates labels), error.vue. No hardcoded copy remains in those surfaces (`en-US` grep clean).
- AC13 ✓ — both switchers switch strings immediately (dropdown re-labels in place), URL prefix updates, persists across reload (e2e) and via cookie.
- AC14 ✓ — `/en` renders the Spanish landing + Spanish chrome without page errors (e2e); Header/Footer/cms untouched.
- AC15 ✓ — `formatMonthYear` (Intl) with active locale for "member since" and organization "Registered".
- AC16 ✓ — auth/guest middleware, logout, post-login redirect, sidebar links, sidebar header, error back link, and landing-header target all `localePath`-aware; e2e: login at `/en/login` lands on `/en/dashboard`.
- AC-A11Y-1 ✓ — e2e: focus trigger → Enter opens, Escape closes and returns focus (Reka handles arrows/typeahead).
- AC-A11Y-2 ✓ — options are `menuitemcheckbox` with `aria-checked` on the active locale (asserted in e2e); labels "Español"/"English" in their own language.
- AC-A11Y-3 ✓ — `<html lang>` bound via `useLocaleHead` in app.vue and error.vue (asserted es→en in e2e); `<title>` translated per page (SSR-verified both locales).
- AC-A11Y-4 ✓ — icon-only triggers have `aria-label` (translated); default `UButton` target ≥ 24×24.
- AC-A11Y-5 ✓ — zod schema wired into `UAuthForm`; `UFormField` links translated errors via `aria-describedby` + sets `aria-invalid` (Nuxt UI built-in); messages rebuilt per locale (`computed` schema).
- AC-A11Y-6 ✓ — all four toasts fire with `t()` at call time inside the existing `UApp` live region; `UApp :locale` also localizes toaster built-ins.
- AC-A11Y-7 ✓ — error.vue: translated descriptive title + `<h1>`, keyboard-operable localized home button.
- AC7 (stage gate) ✓ — see below.

## Verification outputs

- `npm run typecheck` → exit 0; `npm run lint` → exit 0; `npm run build` → "Build complete!"; `npm run format:check` → "All matched files use Prettier code style!".
- `curl -s http://localhost:3000/ | grep -io 'agricultura de precisi.n' | head -1` → `Agricultura de Precisión`.
- SSR both locales: `/login` → `<title>Iniciar sesión</title>` + `lang="es-CO"`; `/en/login` → `<title>Sign in</title>` + `lang="en"`; 404 page → `404 — Página no encontrada` / `/en/...` → `404 — Page not found`.
- `npx playwright test` (e2e/) → **28 passed** (23 existing + 5 new i18n), two consecutive runs; suite also got faster serialized (~16s vs ~34s).
- No frontend unit-test runner exists (no Vitest script/`frontend-test` target) — per Phase 0/A/B precedent the gate is typecheck/lint/build/format + e2e.

## Decisions

- Per-layer locale files (plan's preferred option) — verified working in v10; no root-file fallback needed.
- es nav label/title kept as "Dashboard" (the app's Spanish chrome already uses the term — landing header "Ir al Dashboard" is fixed Spanish).
- Wired the login zod schema into `UAuthForm` (required for translated validation messages, AC12/AC-A11Y-5; the schema had been dead code since Phase 0).
- `UApp :locale` added (es/en from `@nuxt/ui/locale`) so Nuxt UI's own strings don't stay English in the es UI.
- `workers: 1` in playwright config — matches the config's stated serialization intent; `fullyParallel: false` alone does not serialize across files.
- Skipped optional `@axe-core/playwright` scan (plan marked optional; a11y ACs covered by targeted assertions).

## For next agent

QA flow: `/login` (es by default: "Bienvenido de nuevo", "Iniciar sesión") → globe button ("Cambiar idioma") → English → `/en/login` in English → login `juan.perez@email.com` / `E2eSmoke_2026!` → `/en/dashboard` ("Welcome back" toast) → user dropdown ("Pérez") → Language → Español → `/dashboard` in Spanish ("Cerrar sesión", nav "Perfil") → `/dashboard/profile` all-Spanish form, "Miembro desde agosto de 2025"-style date → edit Nombre → "Guardar cambios" → "Perfil actualizado" toast → switch to English on profile → date flips to "August 2025" style → reload keeps `/en` + English → logout → `/en/login` → `/ruta-x` 404 es / `/en/ruta-x` 404 en → `/en` shows Spanish landing. Keyboard: Tab to switcher, Enter, arrows, Escape returns focus.

## Proposed improvements

- Rule: "In locale JSON messages, escape literal `@` as `{'@'}` (and `|`/`{` similarly) — vue-i18n compiles messages and a bare `@` (linked-message syntax) crashes SSR with 'Invalid linked format'." → `frontend/CLAUDE.md` (i18n section the Docs stage adds).
- Rule: "Per-layer i18n: root `nuxt.config.ts` declares locale metadata only (`code`/`language`/`name`); each layer declares `i18n.locales` with `file:` entries and ships `layers/<name>/i18n/locales/*.json` under its own top-level namespace; @nuxtjs/i18n merges by locale code." → `frontend/CLAUDE.md`.
- Rule: "Playwright `fullyParallel: false` only serializes tests within one file — spec files still run on parallel workers. Suites sharing one backend user/login state must set `workers: 1`." → `e2e/README.md` (or future `e2e/CLAUDE.md`).
- Rule: "`UDropdownMenu` overlays aria-hide the rest of the page while open; in e2e, close the menu (Escape) before locating background elements — and note a locale switch does not close it." → `e2e/README.md`.

## Fix pass (2026-08-19, after review-frontend.md)

### Blocking 1 — avatar upload keyboard operability + accessible name — FIXED

`layers/accounts/app/pages/dashboard/profile.vue`:

- File input: `class="hidden"` → `class="sr-only"` (visually hidden but focusable and exposed
  to the accessibility tree), `:disabled="saving"` added so the disabled state is real, not
  label styling.
- Accessible name: existing `:aria-label="t('accounts.profile.changeAvatar')"` is now actually
  exposed ("Cambiar foto de perfil" / "Change profile photo" — keys already present in both
  `layers/accounts/i18n/locales/{es,en}.json`; no new keys needed).
- Visible focus: `focus-within:ring-2 focus-within:ring-primary` on the wrapping
  `UButton as="label"`.
- Empirically re-verified against the running app (Playwright script, logged in as the e2e
  user): input computed `display: block`; `getByRole('button', { name: 'Cambiar foto de
  perfil' })` resolves (name exposed); focused after **8 Tab presses**; label shows a 2px
  primary ring while the input is focused; **Enter opens the native file picker**
  (`filechooser` event fired).
- The keyboard assertion in `e2e/frontend/profile.spec.ts` was NOT added here — all e2e
  additions (blocking 2 and 3 included) are assigned to the QA stage per the fix-pass
  dispatch; frontend agent does not touch `e2e/`.

### Non-blocking items applied

- **NB1** `DropDownUser.vue` — `avatarUrl` is now `computed(() => getImageUrl(...))`; sidebar
  avatar updates after an upload refetch instead of staying stale until remount.
- **NB2** `layouts/dashboard.vue` — sidebar "SAMVA" header is now
  `<NuxtLink :to="localePath('/dashboard')">` (focusable, real link semantics) instead of a
  click-only `<div>`.
- **NB4 (typo half only)** `layouts/dashboard.vue` — local import name `TracktorIcon` →
  `TractorIcon`.
- **NB6 (label half only)** `FarmsMenu.vue` — collapsed trigger gets
  `:aria-label="collapsed ? selectedTeam?.label : undefined"` (farm name is data, no i18n key
  needed).
- **NB7** `layers/common/app/utils/api/tokens.ts` — refresh path `'/accounts/token/refresh/'`
  → `'accounts/token/refresh/'` (matches the contract's no-leading-slash convention).

### Non-blocking items skipped (debatable / assigned elsewhere)

- **NB3** cross-layer composables exception → Docs stage (`ARCHITECTURE.md`/`frontend/CLAUDE.md`).
- **NB4 (alias half)** `#common` alias for cross-layer icon imports — architectural choice, not
  a trivial edit; left for a dedicated decision.
- **NB5** cms landing error state — behavior change on an out-of-scope (untranslated Spanish)
  surface; skipped as debatable.
- **NB6 (data half)** FarmsMenu real farm data / FarmStats delete — deferred per the review's
  own "when the dashboard work resumes".
- **NB8** AC15/AC16 e2e additions — QA stage (e2e is out of frontend scope).
- **NB9** forced light→dark on dashboard mount — pre-existing, review says flag for later.
- **NB10** empty strings never clearing fields — pre-existing, future accounts iteration.

### Verification (fix pass)

- `npm run format:check` → "All matched files use Prettier code style!"
- `npm run typecheck` → exit 0; `npm run lint` → exit 0; `npm run build` → exit 0.
- `npx playwright test` (e2e/) → **28 passed** (16.3s).
- Manual a11y probe of the avatar control (see Blocking 1 above): reachable, named, ringed,
  Enter-activatable.
