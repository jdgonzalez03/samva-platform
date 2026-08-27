# Architecture

This file explains how the system is built. It is the single source of truth.
Every engineering or review agent reads this file first.
Rules for *changing* the code live in the `CLAUDE.md` files of each area. This file is reference only.

**Exact dependency versions are not written here** (they get old fast).
Read the pins in `backend/requirements.txt` and `frontend/package.json`.

## System overview

S.A.M.V.A. is a web platform for farmers. It collects environmental data (like temperature, humidity, and rain) and shows it in a simple way. The goal is to help small and big farmers make better decisions.

How the data flows:

1. Sensors in the field capture environmental data.
2. The sensors send the data to a public API in the backend. Each user gets an `x-api-key` when they register. The sensor puts this key in the request headers, so the backend knows who sends the data. *(This public API is planned — see "Current state" below.)*
3. The backend saves and processes the data.
4. The frontend shows the data in a friendly way.

The repository has three main folders:

- **`frontend/`** — Nuxt 4 with Nuxt UI as the component library.
- **`backend/`** — Django, Wagtail, Django REST Framework (DRF), and Celery.
- **`e2e/`** — Playwright for end-to-end tests.

Infrastructure: Docker Compose for all services, Nginx as reverse proxy, PostgreSQL with PostGIS, RabbitMQ as the Celery broker.

## Backend

Django project at `backend/`. Settings are split in `backend/backend/settings/`: `common.py` (shared), `dev.py`, and `prod.py`. The database is **PostGIS** (PostgreSQL with maps support). Auth uses **JWT** (djangorestframework-simplejwt) with a custom email login backend.

The Django apps:

- **`accounts`** — Users, login, and profiles. The API lives at `/api/accounts/` (JWT login, token refresh, profile).
- **`farmer`** — The farmer model. A farmer has a one-to-one relation with a user. This project does **not** extend Django's user model with `AbstractUser`; the extra data lives in this separate model instead.
- **`core`** — The "common" app. It holds things that do not belong to one app, like global Wagtail settings and general backend code.
- **`cms`** — Content for the landing page, managed with Wagtail (headless CMS with StreamField). The frontend reads it from `/api/cms/landing/`. Wagtail is also used as the admin for the models.
- **`farm`** — Farms and plots (lots). It uses GeoDjango with Leaflet maps, so you can draw farm polygons in the admin.
- **`sensors`** — Everything about sensor data. It integrates weather station providers (like WeatherLink) to pull data from devices. A Celery task polls the weather stations every 5 minutes. In the future: the public API for field sensors (with `x-api-key`) and public weather APIs for more data correlation.
- **`predictions`** — Predictions based on the sensor data. It uses fuzzy logic. Example: predict the irrigation time for a plot.

Background jobs run with **Celery** + RabbitMQ. Scheduled jobs use Celery Beat (see `CELERY_BEAT_SCHEDULE` in `backend/backend/settings/common.py`).

## Frontend

Nuxt 4 app at `frontend/`, with Nuxt UI, Tailwind CSS, TanStack Vue Query, and @nuxtjs/i18n, in TypeScript (exact pins in `frontend/package.json`).

### Modular architecture (Nuxt Layers)

The frontend is fully modular per [ADR 0001](adr/0001-frontend-modular-architecture-nuxt-layers.md): each domain is a self-contained Nuxt Layer (auto-registered from `frontend/layers/`), and the root `app/` is a minimal shell.

```
frontend/
├── app/                # shell only: app.vue, error.vue (designed 404/error page)
├── layers/
│   ├── common/         # HTTP stack (fetcher, $api plugin, tokens, errors), shared UI
│   │                   # (Header/Footer/Logo, LanguageSwitcher, TractorIcon), default
│   │                   # layout, main.css, generic utils (date, image)
│   ├── auth/           # login page/layout, auth+guest middleware, useAuth,
│   │                   # auth-init plugin, authApi, auth types
│   ├── accounts/       # profile page, ProfileSkeleton, useAccount composables,
│   │                   # accountsApi, Profile types, AccountsQueryKey
│   ├── cms/            # landing page (SSR), cms block components, cmsApi,
│   │                   # StreamField types
│   ├── farm/           # FarmsMenu, farm/plot queries + selected-farm state,
│   │                   # farmApi, Farm/Plot types, FarmQueryKey
│   ├── sensors/        # /dashboard/history page, history filters/table/charts,
│   │                   # sensorsApi, history utils, SensorsQueryKey
│   └── dashboard/      # dashboard layout + index page, DropDownUser, farm widgets
├── public/, server/    # stay at root
└── nuxt.config.ts      # aliases, css path, runtimeConfig, i18n locale metadata
```

Each layer mirrors the Nuxt 4 structure (`layers/<name>/app/pages|components|composables|middleware|plugins|utils|types|constants`) and has a minimal `nuxt.config.ts` with `$meta: { name: '<layer>' }`. New domains (`farm`, `sensors`, `predictions`) are born as layers.

**Dependency direction**: domain layers depend on `common`, never on each other. Sanctioned cross-layer exceptions (each recorded in its feature contract):

1. The auth layer consumes `accountsApi` for login/session restore — exposed as an auto-import by `layers/accounts/nuxt.config.ts` (`imports.dirs`), not a file import.
2. Type-only imports of `Profile` from `layers/accounts/app/types/profile` in `useAuth` and `DropDownUser` — erased at build, so the runtime dependency direction stays domain → common.
3. `dashboard` → `farm`: the auto-imported `<FarmsMenu>` component and the `useSelectedFarm`/`useFarmPlotsQuery` composables.
4. `sensors` → `farm`: the same auto-imported composables plus the type-only `Plot`.

Both farm edges run one way only — `farm` never imports from `dashboard` or `sensors`. The sidebar's "Historial" entry is a `localePath('/dashboard/history')` string, so `dashboard` gains no dependency on `sensors`.

### HTTP

- All requests go through the shared `fetcher` (`layers/common/app/utils/api/fetcher.ts`): Bearer injection, 401 → refresh (`POST accounts/token/refresh/`) → retry once → `RefreshTokenError`.
- The `$api` plugin (`layers/common/app/plugins/api.ts`) is **universal (isomorphic)**: baseURL is `runtimeConfig.apiBaseServer` on the server and `runtimeConfig.public.apiBase` on the client, so SSR works in both host-dev and docker topologies. Token reads return `null` on the server.
- Domain API modules (`authApi`, `accountsApi`, `cmsApi`) live at `layers/<domain>/app/utils/api/<domain>.ts`. Their paths are **relative to the fetcher baseURL** (`accounts/me/`, `cms/landing/` — no `/api` prefix). Auth endpoints live under `accounts/` — the backend has no `auth/` mount.
- Aliases: `#api` maps to `layers/common/app/utils/api` and exposes **only the common HTTP stack** (`fetcher`, `tokens`, `errors`) — domain api modules are not behind it. `#shared` (`layers/common/shared/`) is reserved for genuinely cross-layer types; empty today.
- **Plugin ordering**: auto-registered layers load alphabetically, so plugins are **named object plugins** ordered with `dependsOn` — `vue-query` and `auth-init` depend on `api`; `auth-init` also depends on `vue-query` and `i18n:plugin`. Renaming a plugin breaks its dependents.

### State & data (Vue Query)

- Client data goes through TanStack Vue Query behind module composables (`useProfileQuery`, `useUpdateProfileMutation`, `useAuth`'s login/logout mutations). No Pinia.
- Query keys come from per-module enums (`layers/<domain>/app/constants/query-keys.ts`, e.g. `AccountsQueryKey`); a single `profileQueryOptions()` factory feeds `useQuery`, `fetchQuery`, and `prefetchQuery` so all surfaces share one cache entry.
- Mutations invalidate their module's root key on success; skeletons/spinners bind to `isPending`, and query error states render text + Retry (never colour alone).
- **The SSR landing does not use Vue Query**: `layers/cms/app/pages/index.vue` fetches via `useAsyncData('cms-landing', () => cmsApi.getLanding())` through the isomorphic `$api` plugin.

### i18n

- @nuxtjs/i18n with `strategy: 'prefix_except_default'` and `defaultLocale: 'es'`: `/` = Spanish, `/en/...` = English. Browser detection on first visit at `/`, persisted in the `i18n_redirected` cookie.
- Root `nuxt.config.ts` declares locale **metadata** only (`code`/`language`/`name`); message files ship **per layer** at `layers/<name>/i18n/locales/{es,en}.json`, each under its own namespace (`common.*`, `auth.*`, `accounts.*`, `dashboard.*`, `farm.*`, `sensors.*`) — the module merges them by locale code.
- Translated surfaces: login, dashboard area (layout, index, dropdown, profile), and the error page. The landing/cms surfaces (Header, Footer, cms blocks) are fixed Spanish and ship no locale files; `/en` still renders them without errors.
- Navigation is locale-aware (`useLocalePath`/`switchLocalePath`) in middleware, logout, sidebar links, and the error page, so the `/en` prefix survives redirects. Dates format via `Intl` with the active locale. `<html lang>` tracks the locale via `useLocaleHead`.

## Current state

Last update: 2026-08-22.

### Working today

- Landing page: Wagtail CMS → `/api/cms/landing/` → SSR render in Nuxt with StreamField blocks (fixed Spanish).
- Login with JWT (email + password), token refresh, and client-side logout.
- User profile page: view and update profile, with avatar upload (Vue Query mutation + cache invalidation).
- Dashboard shell: sidebar, layouts, and route protection (auth middleware). The dashboard index page is a simple placeholder body — no map or sensor cards yet.
- Frontend modular architecture (Nuxt Layers, ADR 0001): migration complete — `common`, `auth`, `accounts`, `cms`, `farm`, `sensors`, `dashboard`.
- i18n es/en (`prefix_except_default`, per-layer locale files) with a language switcher on the login page and in the dashboard user dropdown.
- Designed 404/error page (`frontend/app/error.vue`), translated.
- Celery Beat polls weather stations (WeatherLink) every 5 minutes.
- Farms and plots in the backend admin, with map polygons.
- Sensor history page (`/dashboard/history`, `sensors` layer): farm/plot/variable/date-range filters carried in the URL, Charts vs. Table toggle, 20-row paginated readings table, and CSV/JSON export of the whole filtered set.
- E2E tests (Playwright): CMS API, landing, auth, profile, i18n.

### Planned

- Dashboard main page: farm map and sensor cards (`leaflet` and `@unovis` are installed for this work; the current index page is a placeholder).
- Public sensor API with `x-api-key` per user, so field sensors can push data.
- Predictions with fuzzy logic (irrigation time), from the `predictions` app to the frontend.
- Dashboard page for predictions (born as a `predictions` layer, per ADR 0001 §3).
- Public weather APIs as extra data sources.
