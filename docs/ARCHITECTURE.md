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

Nuxt 4 app at `frontend/`, with Nuxt UI v4, Tailwind CSS 4, and TypeScript.

- **Target architecture: modular (Nuxt Layers).** Each domain module lives in its own folder under `layers/`. Code shared by two or more modules goes to the `common` layer (the JWT fetcher, `$api` plugin, tokens, Header/Footer, global layouts). Domain layers depend on `common`, never on each other. See [ADR 0001](adr/0001-frontend-modular-architecture-nuxt-layers.md) for the full decision.
- **Today the code is still layered** (grouped by type: `pages/`, `composables/`, `utils/api/`). The migration is incremental: `common` first, then `auth`, then the rest. New domains are born as layers directly.
- **HTTP**: all requests go through the shared `fetcher` (`app/utils/api/fetcher.ts`). It adds the JWT header and refreshes the token when a request gets a 401. Domain API modules live in `app/utils/api/<domain>/` and are imported with the `#api` alias.
- **State**: domain composables (`useAuth`, `useAccount`) with Nuxt `useState`. No Pinia.
- **Types**: shared types live in `shared/types/<domain>/`, imported with the `#shared` alias. They mirror the backend API.
- **i18n**: translations must use i18n. *(Planned — the i18n module is not installed yet; texts are still hardcoded in Spanish and English.)*

## Current state

Last update: 2026-08-18.

### Working today

- Landing page: Wagtail CMS → `/api/cms/landing/` → SSR render in Nuxt with StreamField blocks.
- Login with JWT (email + password), token refresh, and logout.
- User profile page: view and update profile, with avatar upload.
- Dashboard shell: sidebar, layouts, and route protection (auth middleware).
- Celery Beat polls weather stations (WeatherLink) every 5 minutes.
- Farms and plots in the backend admin, with map polygons.
- E2E tests for the landing page and the CMS API (Playwright).

### In progress

- Dashboard main page: the map and sensor cards are not finished. `frontend/app/pages/dashboard/index.vue` references components and mocks that do not exist yet (`leaflet` and `@unovis` are installed for this work).
- Frontend migration to Nuxt Layers (ADR 0001): decided, not started.

### Planned

- Public sensor API with `x-api-key` per user, so field sensors can push data.
- Predictions with fuzzy logic (irrigation time), from the `predictions` app to the frontend.
- Dashboard pages for history and predictions (the sidebar links exist, the pages do not).
- i18n in the frontend.
- Public weather APIs as extra data sources.
