# E2E — S.A.M.V.A. Platform

End-to-end tests with Playwright.

## Run the tests

The backend (and frontend, for the frontend tests) must be running first.

Dev topology used to run the suite:

```bash
# 1. Backend stack (Postgres, broker, Django on :8000) — compose from backend/
cd backend && docker compose up -d
make loaddata        # seed fixtures (backend/Makefile; one-time password setup below)

# 2. Frontend on the host (:3000)
cd frontend && npm run dev

# 3. Tests
cd e2e
npm install
npm test         # run all tests
npm run test:ui  # run with the Playwright UI
```

After editing frontend code, warm the dev server (load one page) before running the
suite — cold Vite on-demand compile can swallow pre-hydration clicks and fail the
first spec spuriously.

## Serialized suite

`playwright.config.ts` sets `workers: 1`: the auth/profile/i18n specs share one
backend user and log in through the real form, so spec files must not run
concurrently. Note `fullyParallel: false` alone is not enough — it only serializes
tests within a file; separate spec files still race on parallel workers.

## Structure

```
backend/    # API tests (e.g. api_cms.spec.ts — the CMS landing endpoint)
frontend/   # Browser tests (e.g. landing.spec.ts, auth.spec.ts, profile.spec.ts)
```

Config lives in `playwright.config.ts`. Note: this flat `backend/` + `frontend/`
layout is what the Playwright projects match (`<dir>/**/*.spec.ts`) — there is no
`e2e/tests/` directory.

## Test user credentials

The auth/profile specs log in through the real login form. Credentials come from
env vars, with defaults matching the seeded fixture user:

| Env var             | Default                |
| ------------------- | ---------------------- |
| `E2E_USER_EMAIL`    | `juan.perez@email.com` |
| `E2E_USER_PASSWORD` | `Test@1234!`           |

The fixture (`backend/accounts/fixtures/initial_users.json`) ships the hash of
`Test@1234!` for every seeded user, so `make loaddata` leaves login (and this
suite) working with no extra setup.

## Locale pinning

The `frontend` Playwright project pins `locale: 'es-CO'` (the app's Spanish
default). Specs never assert inline UI strings: every button/menu/toast/label
name lives in the `T` map in `frontend/helpers.ts` — the single
locale-dependent seam to update if the default UI language changes. The i18n
specs additionally use `T_EN` (English strings) and `SWITCHER` from the same
file; form inputs are selected by `type` attribute so translated labels don't
break them.

Gotcha: `UDropdownMenu` overlays aria-hide the rest of the page while open, and
a locale switch does not close the menu — press Escape before locating
background elements.
