# E2E — S.A.M.V.A. Platform

End-to-end tests with Playwright.

## Run the tests

The backend (and frontend, for the frontend tests) must be running first.

```bash
npm install
npm test         # run all tests
npm run test:ui  # run with the Playwright UI
```

## Structure

```
backend/    # API tests (e.g. api_cms.spec.ts — the CMS landing endpoint)
frontend/   # Browser tests (e.g. landing.spec.ts — the landing page)
```

Config lives in `playwright.config.ts`.
