# ux discovery — frontend Nuxt Layers refactor (+ i18n, Vue Query)

Summary: Analyzed ADR 0001, `frontend/CLAUDE.md`, and every current UI surface. The layers
refactor itself is behavior-preserving; the user-visible work is i18n (language switcher, locale
routing, translated strings), Vue Query loading/caching behavior, and a currently missing
error/404 surface.

## Surface inventory (what i18n must cover)

| Route / surface | Layout | Current copy language |
| --- | --- | --- |
| `/` landing (`app/pages/index.vue` + 6 `cms/*` blocks) | default (Header + Footer) | Spanish — content from Wagtail API |
| `/login` (`UAuthForm`, zod messages, toasts) | login (no Header/Footer) | English |
| `/dashboard` (navbar "Dashboard", tabs Map/List, "Sensores") | dashboard sidebar | Mixed EN/ES |
| `/dashboard/profile` (form labels, select items, toasts, "member since" date) | dashboard | English; date hardcoded `toLocaleDateString('en-US')` |
| `/dashboard/history`, `/dashboard/predictions` | — | **Sidebar links exist, pages do not** → default Nuxt 404 |
| Error/404 page | — | **Does not exist** (`app/error.vue` is in the ADR target shell but absent today) |
| Header ("Ir al Dashboard"), Footer (contact, copyright), sidebar nav labels, DropDownUser ("Log out", "Appearance", Light/Dark), skeletons, page titles (`useHead`) | shared | Mixed EN/ES |

The app is currently *inconsistently bilingual* (login/profile English, landing/footer Spanish) —
i18n is a fix, not just a feature. Email-driven pages (verify email/reset) don't exist in this
frontend yet, so no surface there.

## Concerns

- **Language switcher has no home yet.** Three contexts need it: public Header (`#right` slot has
  room), the `/login` page (its layout has *no* header — the switcher must be added there
  explicitly or login is untranslatable-by-user), and the authenticated dashboard.
  **Reuse:** `DropDownUser.vue` already has an "Appearance" submenu with checkbox items — a
  "Language" submenu should mirror that exact pattern, not introduce a new widget.
- **URL strategy decides everything downstream.** Localized prefixes (`/en/...`, Spanish default
  unprefixed via `prefix_except_default`) give shareable/SEO-correct links and `hreflang`, but
  change every route, the `auth`/`guest` middleware redirects, and all e2e specs. Cookie-only (no
  prefix) is cheaper but loses SEO/shareability for the landing. Must be decided before the plan.
- **Wagtail landing content is a separate translation system.** `/api/cms/landing/` serves one
  language; frontend i18n cannot translate it. Either the backend adds CMS translation
  (out of scope for a frontend refactor?) or the landing stays Spanish in both locales — the
  English UX would then show a Spanish hero under an English header, which needs explicit sign-off.
- **Vue Query changes perceived behavior**: back-navigation renders cached data instantly and
  refetches in the background (content may visibly update after render), and errors surface via
  query state instead of ad-hoc try/catch toasts. Existing skeletons (sidebar footer,
  `ProfileSkeleton`) must map to `isPending`, not disappear. The landing is SSR-rendered for SEO
  via `useFetch` (a documented TODO that also violates the "always use `fetcher`" rule) — whether
  it moves to Vue Query with SSR hydration or stays on `useAsyncData` is an architecture call.
- **Dead sidebar links** (`/dashboard/history`, `/dashboard/predictions`) currently land on an
  unstyled, untranslated default error page. The refactor creates `app/error.vue` anyway — it must
  be translated and designed, and the dead links should be hidden or marked "coming soon".
- **Locale-aware formatting**: profile "member since" date (and future sensor data/dates) must
  format per active locale, not `en-US`.
- **e2e impact**: `e2e/frontend/landing.spec.ts` asserts Spanish text (`/ir al dashboard/i`,
  `/nuestra visión/i`); route prefixes and/or translated copy will break it — tests need a
  locale-stable strategy (pin locale in test setup, or select by role + per-locale fixtures).
- Not applicable: no deep links into paginated lists in scope.

## Accessibility (WCAG 2.2 AA)

- **AC-A11Y-1** — Given the language switcher (any placement), When I Tab to it, Then it shows a
  visible focus ring, opens with Enter/Space, arrow keys move between language options, `Escape`
  closes and returns focus to the trigger.
- **AC-A11Y-2** — Given the switcher options, Then each is exposed as a menu item/radio with the
  current language checked (`aria-checked`), and each option is labeled in its own language
  ("Español", "English") so it's readable before switching.
- **AC-A11Y-3** — Given a language change, When it applies, Then `<html lang>` updates to the new
  locale (screen readers switch pronunciation) and the page `<title>` is in the new language.
- **AC-A11Y-4** — Given the switcher trigger, Then it has an accessible name (e.g.
  `aria-label="Change language"` if icon-only) and a target size ≥ 24×24 px.
- **AC-A11Y-5** — Given a form validation error post-i18n (login, profile), Then the translated
  message is linked via `aria-describedby`, the field sets `aria-invalid`, and the error is
  announced — never signaled by colour alone.
- **AC-A11Y-6** — Given toasts (login success/failure, profile save), Then they render in the
  active locale inside the existing `role="alert"` live region so screen readers announce them.
- **AC-A11Y-7** — Given the new error/404 page, Then it has a translated, descriptive `<title>`
  and heading, and a keyboard-operable link back to home/dashboard.
- **AC-A11Y-8** — Given any Vue Query loading state, Then loading is conveyed accessibly (skeleton
  with `aria-busy` or an announced status), and a query error state renders a text alternative,
  not a colour/icon change alone.

## Recommendation

**Adjust** — proceed with the layers refactor as ADR 0001 specifies, but resolve the open
questions below first; the i18n URL strategy and Wagtail-content decision materially change the
plan's scope, and the error page + dead sidebar links should be pulled into scope explicitly.

## Open questions

1. **URL strategy**: localized route prefixes with Spanish as unprefixed default (`/` = ES,
   `/en/...` = EN) — better for SEO/shareable links — or cookie-only switching with no URL change?
2. **Default locale**: Spanish with browser-language detection on first visit, persisted in a
   cookie? (Audience appears Colombian — confirm.)
3. **Landing content**: should Wagtail CMS content be translated on the backend (extra backend
   work), or stay Spanish in both locales for now? If excluded, is a Spanish landing under an
   English UI acceptable?
4. **Switcher placement**: confirm all three — public Header, login page, and a "Language"
   submenu in the dashboard user dropdown (mirroring "Appearance")?
5. **Persistence**: is language a per-browser preference (cookie) only, or should it be saved to
   the user profile on the backend so it follows the account across devices?
6. **Landing data fetching**: keep SSR via `useAsyncData` for SEO (Vue Query only for
   authenticated dashboard data), or adopt Vue Query with SSR hydration everywhere?
7. **Dead links**: hide `/dashboard/history` and `/dashboard/predictions` sidebar entries until
   those pages exist, or keep them pointing at the new (translated) 404?

## Proposed improvements

- `frontend/CLAUDE.md` (once i18n lands): "All user-facing strings go through i18n (`t()`/locale
  files) — never hardcode copy in templates; format dates/numbers with the active locale, never a
  hardcoded `'en-US'`."
- `e2e/CLAUDE.md` (once i18n lands): "Specs must pin the app locale explicitly and select by role
  with locale-appropriate names — never assume the default language."
