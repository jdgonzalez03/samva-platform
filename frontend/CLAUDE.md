# Frontend — Claude Code

Guidelines for the Nuxt frontend (`frontend/`). Stack: Nuxt 4 + Nuxt UI + TypeScript (exact pins in `package.json`). Before Vue/Nuxt work, consult the project skills: `nuxt-ui`, `vue-best-practices`, `vue-router-best-practices`, `vue-testing-best-practices`, `accessibility`.

Architecture: domain modules as Nuxt Layers — see [ADR 0001](../docs/adr/0001-frontend-modular-architecture-nuxt-layers.md) and the Frontend section of [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Guidelines

### Layers & file placement

- All domain code lives in its layer: `layers/<domain>/app/{pages,components,composables,middleware,plugins,utils,types,constants}`. The root `app/` is a shell — only `app.vue` and `error.vue` belong there.
- Code used by two or more domains (HTTP stack, shared UI, global layouts, generic utils like date/image) goes to `layers/common/`; domain layers depend on `common`, never on each other. Sole sanctioned exceptions: auth consumes the auto-imported `accountsApi`; type-only `Profile` imports from `layers/accounts` (type imports are erased at build); `dashboard` consumes the auto-imported `<FarmsMenu>` component plus the `farm` composables (`useSelectedFarm`, `useFarmPlotsQuery`); and `sensors` consumes the same `farm` composables plus the type-only `Plot` — both dependencies run one way only, `farm` never imports from `dashboard` or `sensors`. A sidebar nav entry pointing at another layer's route is just a `localePath()` string and creates no dependency.
- New domains (`farm`, `sensors`, `predictions`, …) are born as layers with their own `nuxt.config.ts` (`$meta: { name: '<layer>' }`).
- In-layer imports of types/utils/api use relative paths (no per-domain aliases); rely on Nuxt auto-imports for components/composables.
- Nuxt plugins that consume another plugin's injection must be named object plugins with `dependsOn: ['<name>']` — auto-registered layers load alphabetically, so cross-layer plugin order is otherwise accidental. Current names: `api`, `vue-query`, `i18n:plugin` (module-owned), `auth-init` — do not rename without updating dependents.
- Adding, renaming, or deleting a file under a layer's `app/{composables,utils}` invalidates the running dev server's module graph: restart `npm run dev` before trusting the browser or e2e, otherwise the stale module 404s and route navigation aborts with no visible error.
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
- A query whose 404 is a final state (record not found, page past the end) sets `retry: retryUnlessNotFound` and consumers detect it with `isNotFound(error)` — both from `#api/errors`; never inline `(error as { status?: number }).status === 404`, and never raise the retry count above the client default (`retry: 1`).
- Bind loading UI to `isPending` (skeleton wrappers get `aria-busy="true"`); render query errors as text + a labeled Retry control, never colour/icon alone.
- Template event handlers must wrap `refetch`/`mutateAsync` to return `void` (vue-tsc rejects their promise types on `@click`).
- A query whose result depends on a parameter takes the parameter as a `Ref` and puts it **in the query key** (`[Key.ROOT, Key.PLOTS, farmId]`); Vue Query unwraps and tracks it, so changing it refetches with no watcher, emit, or manual invalidation on the consuming page.
- `useQuery` returns a bag of refs, not a reactive proxy: destructure what you need in `<script setup>` (`const { data, isPending } = useX()`) — `query.isPending` used straight in a template is a Ref object, always truthy.
- Injections provided by named object plugins are typed `unknown` on `nuxtApp.$x` inside other plugins — cast via an imported type there; inside components use the library composable (e.g. `useQueryClient()`).

### Composables & state

- Cross-page selection state (the active farm, …) uses `useState` — never a module-scoped `ref`, which is a singleton shared across SSR requests — and is reconciled against the list the backend returned rather than trusted from storage, so reload, user switch, and deleted records all fall back with one rule.
- Shared state lives in the domain's composables (`layers/<domain>/app/composables/`), derived from the Vue Query cache where a query exists — no Pinia.
- All functions inside composables (and any future stores) must be arrow functions, not `function` declarations.
- Converting a user-picked calendar day into an instant for the API always maps start/end of the **local** day to UTC, with a comment saying so — the backend is UTC, so a naive conversion makes "22 de agosto" mean the wrong 24 hours in Bogotá (UTC−5).
- A bounded index carried in the URL (page, tab, step) is clamped in a watcher with `immediate: true`, not only on later changes — otherwise a hand-edited or shared out-of-range value lands the view in a dead-end error with no way back.

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
- A `<UAvatar>` (or a `:avatar="…"` on `<UButton>`) always passes `text` with the owner's initials from `getInitials()` — with neither `text` nor `alt` the fallback renders an empty `bg-elevated` circle that reads as a skeleton; mark it `aria-hidden` when a sibling label already names the control.
- The accessible name of a Nuxt UI/Reka control wrapped in `UFormField` is verified in the browser, never assumed: Reka wires its own English `aria-label` on several roots (a combobox trigger reads "Show popup", `UPagination` reads "Page 2"), which overrides the field label and leaks English into a Spanish UI.
- `UTable` renders an empty separator `<tr>` between `thead` and `tbody`, so `getByRole('row')` counts one more than you expect — count data rows with `locator('tbody tr')`.

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

### Charts (Unovis)

- A missing datum must reach a `VisLine`'s `y` accessor as `undefined`/`NaN`, never `null`: Unovis reads `null` as 0 with `defined: true` and draws a flat line at zero across data that does not exist — a chart that states a false measurement rather than showing a gap.
- A categorical chart (`VisGroupedBar`) gets its tooltip from `VisTooltip` with `:triggers` keyed on the mark's selector (`GroupedBar.selectors.bar`). `VisCrosshair` assumes a continuous x axis and silently does nothing over bars.

### i18n

- All user-facing strings in in-scope surfaces (login, dashboard area, error page) go through `t()` + locale files — never hardcoded; zod validation messages are built inside a `computed` schema so they switch live.
- Root `nuxt.config.ts` declares locale metadata only (`code`/`language`/`name`); each layer declares `i18n.locales` with `file:` entries and ships `layers/<name>/i18n/locales/{es,en}.json` under its own top-level namespace (`auth.*`, `accounts.*`, …) — @nuxtjs/i18n merges by locale code.
- Landing/cms surfaces (Header, Footer, cms block components) stay untranslated Spanish and ship no locale files.
- Dates/numbers format via `Intl` with the active locale (`useI18n().locale`) — never a hardcoded locale like `'en-US'`.
- Internal navigation and middleware redirects use `useLocalePath()`/`switchLocalePath()` so the `/en` prefix is preserved — never raw `/dashboard`-style paths in `to`/`navigateTo`.
- In locale JSON messages, escape literal `@` as `{'@'}` (and `|`/`{` similarly) — vue-i18n compiles messages and a bare `@` crashes SSR with "Invalid linked format".

### Formatting & lint

- Prettier owns formatting (`npm run format`, format-on-save); ESLint only lints — never add stylistic/formatting rules to `eslint.config.mjs` (conflicts stay disabled via `eslint-config-prettier`).
- Comments use `//` line syntax only — never JSDoc/`/** */` blocks, even above exported composables or functions.

### Dependencies

- Install with `npm install <pkg>` (no `@version` pin) unless a specific version is strictly required.
