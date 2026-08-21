# Frontend — Claude Code

Guidelines for the Nuxt frontend (`frontend/`). Stack: Nuxt 4 + Nuxt UI + TypeScript (exact pins in `package.json`). Before Vue/Nuxt work, consult the project skills: `nuxt-ui`, `vue-best-practices`, `vue-router-best-practices`, `vue-testing-best-practices`, `accessibility`.

Architecture: domain modules as Nuxt Layers — see [ADR 0001](../docs/adr/0001-frontend-modular-architecture-nuxt-layers.md) and the Frontend section of [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Guidelines

### Layers & file placement

- All domain code lives in its layer: `layers/<domain>/app/{pages,components,composables,middleware,plugins,utils,types,constants}`. The root `app/` is a shell — only `app.vue` and `error.vue` belong there.
- Code used by two or more domains (HTTP stack, shared UI, global layouts, generic utils like date/image) goes to `layers/common/`; domain layers depend on `common`, never on each other. Sole sanctioned exceptions: auth consumes the auto-imported `accountsApi`, and type-only `Profile` imports from `layers/accounts` (type imports are erased at build).
- New domains (`farm`, `sensors`, `predictions`, …) are born as layers with their own `nuxt.config.ts` (`$meta: { name: '<layer>' }`).
- In-layer imports of types/utils/api use relative paths (no per-domain aliases); rely on Nuxt auto-imports for components/composables.
- Nuxt plugins that consume another plugin's injection must be named object plugins with `dependsOn: ['<name>']` — auto-registered layers load alphabetically, so cross-layer plugin order is otherwise accidental. Current names: `api`, `vue-query`, `i18n:plugin` (module-owned), `auth-init` — do not rename without updating dependents.
- In a layer's `nuxt.config.ts`, resolve `imports.dirs` (and any path option) to absolute paths with `fileURLToPath(new URL(..., import.meta.url))` — relative paths are not layer-relative.

### HTTP & API layer

- Never call `fetch`/`$fetch`/`useFetch` directly; all HTTP goes through the shared `fetcher` (`layers/common/app/utils/api/fetcher.ts`), which wraps the isomorphic `$api` plugin (base URL, JWT header) and auto-refreshes tokens on 401.
- Endpoints live in domain API modules at `layers/<domain>/app/utils/api/<domain>.ts` (e.g. `authApi`, `accountsApi`, `cmsApi`); composables and components call those modules — never `fetcher` directly.
- Module `api.ts` paths are relative to the fetcher baseURL (`/api`) — never prefix `/api` or hardcode the host; trailing slash required (Django). Auth/login/token endpoints live under `accounts/` — there is no `auth/` mount on the backend.
- The `#api` alias exposes only the common HTTP stack (`fetcher`, `tokens`, `errors`); domain api modules are imported relatively inside their own layer.
- Error handling reads ofetch's `FetchError` (`error.status`, `error.data`) with the per-endpoint shape from the backend — there is no uniform error envelope (login 401 uses `{ error }`, DRF elsewhere uses `{ detail }` or a field→messages map).

### SSR

- Guard browser-only APIs (`localStorage`, `window`, …) with `import.meta.client`; on the server return `null`/no-op — pages and middleware run server-side on direct loads.
- Universal plugins must work in both topologies: server-side HTTP uses `runtimeConfig.apiBaseServer`, client-side uses `runtimeConfig.public.apiBase` (host dev and docker resolve them differently).
- The SSR landing fetches via `useAsyncData` wrapping `cmsApi` — never Vue Query, never a direct `useFetch`.

### Vue Query (client data)

- Module composables wrap `useQuery`/`useMutation` (`useProfileQuery`, `useUpdateProfileMutation`, …); components never call Vue Query with ad-hoc keys.
- Query keys come from the module's `<Module>QueryKey` enum in `layers/<domain>/app/constants/query-keys.ts`; define one `<x>QueryOptions()` factory per query (plain object + `as const` key — not the `queryOptions()` helper, whose DataTag typing breaks on spread) shared by `useQuery`, `fetchQuery`, and `prefetchQuery`.
- Mutations invalidate their module's `[<Module>QueryKey.ROOT]` on success; logout clears the whole cache.
- Bind loading UI to `isPending` (skeleton wrappers get `aria-busy="true"`); render query errors as text + a labeled Retry control, never colour/icon alone.
- Template event handlers must wrap `refetch`/`mutateAsync` to return `void` (vue-tsc rejects their promise types on `@click`).
- Injections provided by named object plugins are typed `unknown` on `nuxtApp.$x` inside other plugins — cast via an imported type there; inside components use the library composable (e.g. `useQueryClient()`).

### Composables & state

- Shared state lives in the domain's composables (`layers/<domain>/app/composables/`), derived from the Vue Query cache where a query exists — no Pinia.
- All functions inside composables (and any future stores) must be arrow functions, not `function` declarations.

**Correct:**

```ts
const fetchMe = async () => { ... }
const clearUser = () => { user.value = null }
const waitForReady = () => readyPromise
```

**Wrong:**

```ts
function fetchMe() { ... }
async function fetchMe() { ... }
function clearUser() { user.value = null }
```

### UI components & icons

- All Nuxt UI components use the `U` prefix, not `Nuxt` (this is the NuxtUI default).
  - **Wrong:** `<NuxtIcon>`, `<NuxtButton>`, `<NuxtForm>`, `<NuxtInput>`
  - **Correct:** `<UIcon>`, `<UButton>`, `<UForm>`, `<UInput>`
- Always use Lucide icons (`i-lucide-*`). Never use heroicons or any other icon set.
- Every page sets its tab title with `useHead({ title: '...' })` (auto-imported) — never leave the default.

**Correct:**

```vue
<UIcon name="i-lucide-circle-check" />
<UIcon name="i-lucide-circle-x" />
<UIcon name="i-lucide-loader-circle" class="animate-spin" />
```

**Wrong:**

```vue
<UIcon name="i-heroicons-check-circle" />
<UIcon name="i-heroicons-x-circle" />
```

### i18n

- All user-facing strings in in-scope surfaces (login, dashboard area, error page) go through `t()` + locale files — never hardcoded; zod validation messages are built inside a `computed` schema so they switch live.
- Root `nuxt.config.ts` declares locale metadata only (`code`/`language`/`name`); each layer declares `i18n.locales` with `file:` entries and ships `layers/<name>/i18n/locales/{es,en}.json` under its own top-level namespace (`auth.*`, `accounts.*`, …) — @nuxtjs/i18n merges by locale code.
- Landing/cms surfaces (Header, Footer, cms block components) stay untranslated Spanish and ship no locale files.
- Dates/numbers format via `Intl` with the active locale (`useI18n().locale`) — never a hardcoded locale like `'en-US'`.
- Internal navigation and middleware redirects use `useLocalePath()`/`switchLocalePath()` so the `/en` prefix is preserved — never raw `/dashboard`-style paths in `to`/`navigateTo`.
- In locale JSON messages, escape literal `@` as `{'@'}` (and `|`/`{` similarly) — vue-i18n compiles messages and a bare `@` crashes SSR with "Invalid linked format".

### Formatting & lint

- Prettier owns formatting (`npm run format`, format-on-save); ESLint only lints — never add stylistic/formatting rules to `eslint.config.mjs` (conflicts stay disabled via `eslint-config-prettier`).

### Dependencies

- Install with `npm install <pkg>` (no `@version` pin) unless a specific version is strictly required.
