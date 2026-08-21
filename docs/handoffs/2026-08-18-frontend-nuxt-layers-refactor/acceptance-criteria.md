# Acceptance criteria — Frontend Nuxt Layers refactor + Vue Query + i18n

Behaviour source of truth for `2026-08-18-frontend-nuxt-layers-refactor`. Every
downstream role verifies its slice against this list; QA signs off the full list.

## Safety net (pre-refactor)

- [ ] **AC1** — Given the pre-refactor codebase, When the new e2e smoke specs run
  (login → dashboard redirect, logout, auth/guest route protection, profile update),
  Then they pass — and they keep passing unmodified in behaviour after Stage A.

## Stage A — Layers structure

- [ ] **AC2** — Given the migration is complete, When inspecting `frontend/`, Then all
  domain code lives under `layers/common|auth|accounts|cms|dashboard` per ADR 0001
  (accounts as its own layer), and root `app/` holds only the shell
  (`app.vue`, `error.vue`).
- [ ] **AC3** — Given any module needs the backend, When it issues a request, Then it
  goes through that module's `api.ts` object built on the common fetcher — including
  the landing page (no direct `useFetch`/`$fetch` for API calls; SSR via
  `useAsyncData` wrapping `cmsApi`).
- [ ] **AC4** — Given each domain layer, Then its types and constants live inside the
  layer (no cross-layer imports except from `common`; layers never import each other).
- [ ] **AC5** — Given the pre-refactor app, When Stage A lands, Then landing, login →
  dashboard redirect, logout, route protection, and profile update behave identically
  and all e2e specs (including AC1's) pass.
- [ ] **AC6** — Given the sidebar, Then the `/dashboard/history` and
  `/dashboard/predictions` entries are hidden, and navigating to a non-existent route
  renders the new designed `error.vue` with a working link back home.
- [ ] **AC7** — Given `npm run typecheck`, lint, and build, When run after each stage,
  Then all pass.

## Stage B — Vue Query

- [ ] **AC8** — Given a component reading server data client-side (e.g. profile), Then
  it uses a module composable wrapping `useQuery` with module-scoped query keys
  (`[<Module>QueryKey.ROOT, ...]`), and existing skeletons/loading UI bind to
  `isPending`.
- [ ] **AC9** — Given a client-side write (login, logout, profile update), Then it goes
  through a module composable wrapping `useMutation`, with success/error toasts
  preserved and relevant queries invalidated on success.
- [ ] **AC10** — Given the SSR landing page, Then it still server-renders its CMS
  content via `useAsyncData` + `cmsApi` (not Vue Query) and remains SEO-renderable.

## Stage C — i18n

- [ ] **AC11** — Given a first-time visitor, When they load the app, Then locale is
  detected from the browser (fallback `es`), persisted in a cookie, and routes follow
  `prefix_except_default` (`/` Spanish unprefixed, `/en/...` English).
- [ ] **AC12** — Given the login page and the entire dashboard area (nav, pages,
  forms, selects, toasts, zod validation messages, page titles, error page), Then all
  their UI strings render via i18n in the active locale with no hardcoded copy
  remaining in those surfaces.
- [ ] **AC13** — Given the language switcher (dashboard user-dropdown "Language"
  submenu mirroring "Appearance", and a switcher on the login page), When the user
  selects the other language, Then all in-scope strings switch immediately —
  including toasts and validation messages — the URL prefix updates accordingly, and
  the choice persists across reloads.
- [ ] **AC14** — Given the public landing in either locale, Then its content and
  chrome render in Spanish (Wagtail content and landing Header/Footer untranslated,
  out of scope) without errors.
- [ ] **AC15** — Given locale-affected formatting (profile "member since" date), Then
  it formats per the active locale — no hardcoded `'en-US'`.
- [ ] **AC16** — Given middleware redirects (auth/guest) and internal navigations,
  When triggered in the `en` locale, Then they preserve the `/en` prefix and no
  navigation 404s in either locale.

## Docs

- [ ] **AC17** — Given the feature is done, When reading `docs/ARCHITECTURE.md` and
  `frontend/CLAUDE.md`, Then both reflect the layers layout, Vue Query conventions,
  and i18n rules.

## Accessibility (WCAG 2.2 AA)

- [ ] **AC-A11Y-1** — Given the language switcher (any placement), When I Tab to it,
  Then it shows a visible focus ring, opens with Enter/Space, arrow keys move between
  language options, and `Escape` closes and returns focus to the trigger.
- [ ] **AC-A11Y-2** — Given the switcher options, Then each is exposed as a menu
  item/radio with the current language checked (`aria-checked`), and each option is
  labeled in its own language ("Español", "English").
- [ ] **AC-A11Y-3** — Given a language change, When it applies, Then `<html lang>`
  updates to the new locale and the page `<title>` is in the new language.
- [ ] **AC-A11Y-4** — Given the switcher trigger, Then it has an accessible name
  (e.g. `aria-label` if icon-only) and a target size ≥ 24×24 px.
- [ ] **AC-A11Y-5** — Given a form validation error post-i18n (login, profile), Then
  the translated message is linked via `aria-describedby`, the field sets
  `aria-invalid`, and the error is announced — never signaled by colour alone.
- [ ] **AC-A11Y-6** — Given toasts (login success/failure, profile save), Then they
  render in the active locale inside the existing `role="alert"` live region.
- [ ] **AC-A11Y-7** — Given the new error/404 page, Then it has a translated,
  descriptive `<title>` and heading, and a keyboard-operable link back to
  home/dashboard.
- [ ] **AC-A11Y-8** — Given any Vue Query loading state, Then loading is conveyed
  accessibly (skeleton with `aria-busy` or an announced status), and a query error
  state renders a text alternative, not a colour/icon change alone.
