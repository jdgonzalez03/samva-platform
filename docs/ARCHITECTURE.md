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
2. The data reaches the backend through one of two doors, both stored by the same code (`sensors/utils.py`: `resolve_sensor` + `store_reading`):
   - **LoRaWAN nodes** (the real field hardware) radio to a gateway that forwards to **The Things Network (TTN)**. TTN decodes each uplink with our formatter (`docs/test-sensors/response-format.js`) and publishes it on its MQTT broker; the `mqtt_ingest` service subscribes and stores one reading per probe, each probe being a `FieldSensor` whose `serial_number` is the probe id sent in the payload ([ADR 0002](adr/0002-mqtt-ingest-for-lorawan-sensors.md)).
   - **HTTP devices** call the public API (`POST /api/sensors/ingest/`). Each user gets an API secret when they register (`Farmer.api_secret`, shown on the profile page). The sensor puts it in the `X-API-Key` header, so the backend knows who sends the data, and identifies itself with its `serial_number` in the body.
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
- **`farm`** — Farms and plots (lots). It uses GeoDjango with Leaflet maps, so you can draw farm polygons in the admin. `GET /api/farm/plots/` lists every plot the user owns across farms with light stats (farm, sensors, area, latest readings with fuzzy level, latest irrigation) for "Mis lotes". `GET /api/farm/plots/<id>/overview/` feeds the plot detail page in one request: latest reading per variable with its 24 h change and fuzzy level (Bajo/Medio/Alto, from the irrigation model's membership functions), hourly series of the last 7 days, the plot's sensors with status, and its latest irrigation prediction.
- **`sensors`** — Everything about sensor data. It integrates weather station providers (like WeatherLink) to pull data from devices. A Celery task polls the weather stations every 5 minutes. Weather stations are read per farm and per station: `GET /api/sensors/farms/<id>/stations/` lists the farm's stations (inactive included) as cards — status `online`/`stale` (newest snapshot older than `STATION_STALE_AFTER`, 30 min)/`never_seen`/`inactive`, latest value per active variable, 24 h hourly air-temperature sparkline — in a constant five queries; `GET /api/sensors/stations/<id>/` adds the station's active variables, and `stations/<id>/series|readings|export/csv|export/json/` mirror the field-sensor history endpoints (same filter params, bucket tiers, page envelope, export cap) over the station's measurements. It also exposes the public ingest API field sensors push readings to (`X-API-Key` auth, throttled per key), and runs the `mqtt_ingest` command (its own compose service, `restart: unless-stopped`) that subscribes to LoRaWAN uplinks: `MQTT_SOURCE=ttn` reads The Things Network over TLS, `MQTT_SOURCE=local` (default) reads the development Mosquitto fed by `backend/scripts/simulate_lora_node.py`. `sensors/lorawan.py` turns a TTN `ApplicationUp` (payload v2, fPort 3) into one reading per probe and logs every rejection on the `sensors.mqtt` logger. In the future: public weather APIs for more data correlation.
- **`predictions`** — Predictions based on the sensor data. Today one model: fuzzy-logic irrigation time (`predictions/fuzzy/irrigation.py`, scikit-fuzzy Mamdani; membership functions and the 27 rules come from an agronomic study and are pinned by golden tests). `POST /api/predictions/plots/<id>/irrigation/` averages the plot's last N hours of soil moisture, air temperature and solar radiation from two sources — the plot's field sensors and the farm's active weather stations, each limited to the variables marked *Use in predictions* (on by default for field sensors, off for stations) — and uses the mean of the available source averages (one vote per source). It runs the model and stores an `IrrigationPrediction` with the per-source breakdown in `input_sources` (422 with the `missing` variables when neither source has readings); `GET` on the same route is the history. `models/` is the catalogue and `fuzzy/irrigation/definitions/` the membership-function shapes for charts.

- **`assistant`** — Chat assistant on a local LLM ([ADR 0003](adr/0003-local-llm-assistant-with-tool-calling.md)). `POST /api/assistant/chat/` takes the whole conversation (`messages`, the last one from the user; only the last 20 reach the model) and the interface `language` (`es` default, `en`), which the system prompt turns into the reply language, sends it to **Ollama** (`ollama` compose service, `OLLAMA_URL`/`OLLAMA_MODEL`, default `llama3.2:3b`) with six tools — `list_farms`, `list_plots`, `get_plot_conditions`, `list_sensors`, `get_latest_irrigation`, `calculate_irrigation` (`assistant/tools.py`) — and runs the tool calls the model asks for, at most 4 rounds. Every tool is scoped to the requesting user and reuses the views' code, so plots are matched by id or name and someone else's plot is "not found". Returns `{reply, tool_calls}` with each tool's arguments and result; nothing is stored. 503 when the model is unreachable or not downloaded, throttled per user (`assistant_chat`).

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
│   ├── farm/           # FarmsMenu, StationCard/StationStatusBadge, farm/plot/
│   │                   # station-list queries + selected-farm state, farmApi,
│   │                   # Farm/Plot/WeatherStation types, FarmQueryKey
│   ├── sensors/        # /dashboard/history, /dashboard/sensors, /dashboard/stations
│   │                   # (+ /[id]) pages, history filters/table/charts (shared
│   │                   # by the station detail), sensorsApi, SensorsQueryKey
│   ├── predictions/    # /dashboard/predictions catalogue + /fuzzy irrigation view,
│   │                   # predictionsApi, membership chart utils, PredictionsQueryKey
│   ├── assistant/      # /dashboard/assistant chat (UChatMessages/UChatPrompt),
│   │                   # useAssistantChat, assistantApi, tool-call rows
│   └── dashboard/      # dashboard layout, home page (components/home), plot detail
│                       # (components/plot), map, farm-overview/plot-series utils
├── public/, server/    # stay at root
└── nuxt.config.ts      # aliases, css path, runtimeConfig, i18n locale metadata
```

Each layer mirrors the Nuxt 4 structure (`layers/<name>/app/pages|components|composables|middleware|plugins|utils|types|constants`) and has a minimal `nuxt.config.ts` with `$meta: { name: '<layer>' }`. New domains (`farm`, `sensors`, `predictions`, `assistant`) are born as layers.

**Dependency direction**: domain layers depend on `common`, never on each other. Sanctioned cross-layer exceptions (each recorded in its feature contract):

1. The auth layer consumes `accountsApi` for login/session restore — exposed as an auto-import by `layers/accounts/nuxt.config.ts` (`imports.dirs`), not a file import.
2. Type-only imports of `Profile` from `layers/accounts/app/types/profile` in `useAuth` and `DropDownUser` — erased at build, so the runtime dependency direction stays domain → common.
3. `dashboard` → `farm`: the auto-imported `<FarmsMenu>` and `<StationCard>` components and the `useSelectedFarm`/`useFarmPlotsQuery`/`useFarmStationsQuery` composables.
4. `sensors` → `farm`: the same auto-imported composables and `<StationCard>`/`<StationStatusBadge>`, plus the type-only `Plot` and `WeatherStation`.

The weather-station list (`farmApi.getStations` → `GET sensors/farms/<id>/stations/`, its query and card) lives in `farm`, not `sensors`: the home dashboard renders the same cards, and `dashboard` may not import from `sensors`. Everything only the station pages use (detail, series, readings, export) stays in `sensors`.
5. `predictions` → `farm`: the auto-imported `useSelectedFarm`/`useFarmPlotsQuery` composables.

Every farm edge runs one way only — `farm` never imports from `dashboard`, `sensors` or `predictions`. The sidebar's "Historial", "Mis sensores", "Estaciones", "Predicciones" and "Asistente" entries are `localePath()` strings, so `dashboard` gains no dependency on `sensors`, `predictions` or `assistant`. The `assistant` layer depends on `common` only: its conversation lives in the page (the backend is stateless), and after a tool that writes (`calculate_irrigation`) it invalidates the whole Vue Query cache instead of importing other layers' query keys.

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

Last update: 2026-10-06.

### Working today

- Landing page: Wagtail CMS → `/api/cms/landing/` → SSR render in Nuxt with StreamField blocks (fixed Spanish).
- Login with JWT (email + password), token refresh, and client-side logout.
- User profile page: view and update profile, with avatar upload (Vue Query mutation + cache invalidation).
- Dashboard shell: sidebar, layouts, and route protection (auth middleware).
- Home dashboard (`/dashboard`): greeting, stat tiles (plots, area, sensors online, alerts), farm conditions (field-sensor averages with fuzzy level, 24 h trend and sparkline), "Necesita atención" alerts (dry soil, stale plots, offline/never-seen sensors, missing irrigation), plot comparison chart, map beside a driest-first plot ranking (plot colours match the map), plots × hour heatmap, irrigation bars, sensor-status donut, daily min/avg/max climate, and the weather-station cards. Fed by `GET /api/farm/farms/<id>/overview/`; the weather-station cards by `GET /api/sensors/farms/<id>/stations/` (the old `GET /api/farm/farms/<id>/weather/` is removed).
- Frontend modular architecture (Nuxt Layers, ADR 0001): migration complete — `common`, `auth`, `accounts`, `cms`, `farm`, `sensors`, `dashboard`.
- i18n es/en (`prefix_except_default`, per-layer locale files) with a language switcher on the login page and in the dashboard user dropdown.
- Designed 404/error page (`frontend/app/error.vue`), translated.
- Celery Beat polls weather stations (WeatherLink) every 5 minutes.
- Weather stations API (`sensors` app): per-farm station cards (status, latest values, 24 h air-temperature sparkline), station detail, and per-station series/readings/CSV-JSON export with the same conventions as the sensor history.
- Farms and plots in the backend admin, with map polygons.
- Sensor history page (`/dashboard/history`, `sensors` layer): farm/plot/variable/date-range filters carried in the URL, Charts vs. Table toggle, 20-row paginated readings table, and CSV/JSON export of the whole filtered set.
- Public sensor ingest API (`POST /api/sensors/ingest/`): `X-API-Key` = the user's `Farmer.api_secret`, sensor resolved by `serial_number`, one timestamped reading per request, idempotent on resend. The user regenerates the secret from the profile's API access card (`POST /api/accounts/me/api-secret/regenerate/`), which cuts off every device still using the old one. Integrator guide: [docs/sensor-ingest-api.md](sensor-ingest-api.md).
- Weather stations pages (`sensors` layer, sidebar "Estaciones"): `/dashboard/stations` lists the selected farm's stations as cards (status in text, last reading, latest value of every variable, 24 h air-temperature sparkline) — the same cards the home dashboard shows; `/dashboard/stations/<id>` adds current conditions, 24 h / 7 d / 30 d charts, a 20-row paginated readings table and CSV/JSON export, with range and page in the URL and a not-found state for an unknown or foreign station. Cards, detail, series and page 1 of the readings refresh every 30 s.
- "Mis sensores" page (`/dashboard/sensors`, `sensors` layer): the selected farm's sensors with serial, plot, variables, and status (online / offline after 45 min without data / never seen / inactive) from `FieldSensor.last_seen_at`, which every ingest request stamps.
- "Mis lotes" (`/dashboard/plots`, sidebar entry): one card per plot across all farms — farm badge, reporting status, soil moisture, temperature, sensors and area, fuzzy level and irrigation badges — with name search and farm filter kept in the URL.
- Plot detail page (`/dashboard/plots/<id>`, `dashboard` layer): hero with satellite mini-map and reporting/area/sensor badges, current-condition cards (value, fuzzy level badge, 24 h trend, sparkline), 24 h / 7 d trend chart with min/avg/max, hourly heatmap of the last 7 days in local time, latest irrigation prediction linking to the fuzzy view, and sensor status list.
- Fuzzy-logic irrigation predictions (`predictions` app + layer): sidebar "Predicciones" with a "Lógica difusa" child, model catalogue cards, and a view that calculates a plot's irrigation time from its recent readings, showing input memberships, output activation chart and the plot's prediction history.
- Installable PWA (`@vite-pwa/nuxt`): manifest, auto-updating service worker that precaches only static build assets (pages and `/api/` always hit the network), icons generated from `frontend/public/logo.svg` by `pwa-assets.config.ts`. The sidebar always shows an "Instalar app" entry until the app runs installed (`$pwa.isPWAInstalled`): it opens the native prompt when the browser offers one (`$pwa.showInstallPrompt`) and otherwise a dialog with manual steps (`InstallAppModal`, iOS-specific on Safari, which has no install prompt). Native store apps (Capacitor/Tauri) are not planned until a store listing or native API is required.
- LoRaWAN ingest over MQTT (ADR 0002): `mqtt_ingest` subscribes to The Things Network (or the dev Mosquitto), stores one reading per probe, and `make simulate-lora` publishes TTN-shaped uplinks for the demo probes 101–109 that `make loaddata` registers on "Lote El Rodeo" (Finca La Montaña).
- Chat assistant (`assistant` app + layer, sidebar "Asistente" under "Predicciones"): asks a local LLM (Ollama, `llama3.2:3b`) that answers with tool calls over the user's own data — farms, plots, latest conditions, sensor status, latest irrigation prescription, and calculating a new one with the fuzzy model. Six quick actions, one per tool (those that need a plot prefill the prompt for the user to finish), a dismissible usage-tips alert remembered per browser, collapsible rows showing each tool used and its result, new-conversation button, error + Retry (503 unavailable, 429 throttled).
- E2E tests (Playwright): CMS API, sensor ingest API, predictions API, landing, auth, profile, i18n, predictions, weather stations.

### Planned

- Sensor ingest follow-ups: batch uploads for offline buffers, per-device keys, hashed secrets.
- Public weather APIs as extra data sources.
