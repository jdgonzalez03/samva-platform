# ADR 0001: Migrate the frontend from layered architecture to domain modules (Nuxt Layers)

- **Status**: Accepted
- **Date**: 2026-08-18
- **Scope**: `frontend/`

## Context

The frontend currently uses a **layered architecture with domain-grouped folders**: presentation (`app/pages/`, `app/layouts/`, `app/components/`) → state/logic (`app/composables/<domain>/`) → data access (`app/utils/api/<domain>/` → `fetcher` → `$api` plugin) → contracts (`shared/types/<domain>/`). UI primitives are delegated to Nuxt UI, so there is no atomic-design component hierarchy of our own.

The layering is clean, but each domain is spread horizontally across every layer. The `auth` domain alone touches five places: `app/pages/login.vue`, `app/middleware/{auth,guest}.ts`, `app/composables/auth/`, `app/utils/api/auth/`, `app/plugins/auth-init.client.ts`, plus `shared/types/auth/`.

Growth makes this worse, not better:

- The backend already has `farm`, `sensors`, and `predictions` Django apps whose frontend counterparts don't exist yet.
- The dashboard sidebar already links to `/dashboard/history` and `/dashboard/predictions` — pages still to be built.
- Every new domain added under the current scheme scatters another feature across four-plus directories.

Nuxt 4 supports modular architecture as a first-class citizen through **Layers**: a `layers/` directory is auto-registered, and each layer is a self-contained mini-app (its own `app/pages/`, `components/`, `composables/`, `middleware/`, optional `nuxt.config.ts`) that Nuxt merges into the final app — routes, auto-imports and all.

This is also the cheapest moment to migrate: 4 pages, ~25 components, 3 domains.

## Decision

Adopt **Nuxt Layers — everything is a module, including the shared foundation** — under `frontend/layers/`:

```
frontend/
├── layers/
│   ├── common/      # fetcher + $api plugin + tokens, Header/Footer/Logo, global layouts, shared types/utils
│   ├── auth/        # login page, guest/auth middleware, useAuth, api/auth, auth types
│   ├── cms/         # landing page, cms/* components, StreamField block types
│   └── dashboard/   # dashboard layout & pages, farm/sensor UI (future: farm, sensors, predictions)
├── app/             # minimal shell only: app.vue, error.vue
└── nuxt.config.ts
```

1. **Explicit `common` layer.** All cross-domain code lives in `layers/common/`: the HTTP stack (`fetcher`, `$api` plugin, `tokens`, `errors`), shared UI (`Header`/`Footer`/`Logo`), global layouts, and truly shared types/utils (e.g. `Image`, `getImageUrl`). The root `app/` stays a minimal shell (`app.vue`, `error.vue`). The uniform model — every folder under `layers/` is a module — and the explicit dependency direction (domain layers depend on `common`, never on each other) outweigh the extra indirection; `common` is also extractable as a package if another app ever needs the same JWT fetcher.
2. **Each domain layer owns its full vertical slice**: pages, components, composables, middleware, domain API module, and domain types live together inside the layer.
3. **Incremental migration, `common` then `auth` first.** `common` must exist before any domain layer can consume it; `auth` is the most self-contained domain and validates the pattern end-to-end. Then `cms`, then `dashboard` (when its unfinished map/stats work is resumed). New domains (`farm`, `sensors`, `predictions`) are born as layers directly — never added to the old layout.
4. **Token flow across layers**: tokens are *written* by the auth layer (login → `setTokens()`) but *read* by `common`'s fetcher on every request (Bearer header, 401 → refresh → retry). The fetcher therefore lives in `common`, keeping the dependency direction clean — every domain uses `fetcher` via the `#api` alias (re-mapped to `layers/common/`), and no layer depends on `auth`.

## Consequences

**Positive**

- One feature = one folder: cohesion by domain, no more 5-directory hunts to understand auth.
- The frontend mirrors the backend's Django apps (`accounts`, `cms`, `farm`, `sensors`, `predictions`), so the mental model is the same on both sides of the stack.
- Layers can later be extracted into packages/repos if any module needs to be shared.
- Runtime behavior does not change: Nuxt merges layer routes and auto-imports transparently.

**Negative / costs**

- Import paths and file locations change across most of the frontend; the `#api` and `#shared` aliases must be re-mapped or extended per layer as domains move.
- New placement conventions to document and enforce (what belongs to a layer vs. the base).
- `frontend/CLAUDE.md` guidelines and the project skills must be updated as each domain migrates.

**Transitional state**

Until the migration completes, the codebase is intentionally hybrid (e.g. `auth` as a layer while `cms`/`dashboard` remain layered). That intermediate state is valid; new code in an unmigrated domain follows the old scheme until that domain's migration lands.
