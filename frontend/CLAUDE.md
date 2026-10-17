# Frontend — Claude Code

Guidelines for the Nuxt frontend (`frontend/`). Stack: Nuxt 4 + Nuxt UI + TypeScript (exact pins in `package.json`). Before Vue/Nuxt work, consult the project skills: `nuxt-ui`, `vue-best-practices`, `vue-router-best-practices`, `vue-testing-best-practices`, `accessibility`.

Architecture: domain modules as Nuxt Layers — see [ADR 0001](../docs/adr/0001-frontend-modular-architecture-nuxt-layers.md) and the Frontend section of [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Guidelines

### Layers & file placement

- All domain code lives in its layer: `layers/<domain>/app/{pages,components,composables,middleware,plugins,utils,types,constants}`. The root `app/` is a shell — only `app.vue` and `error.vue` belong there.
- Code used by two or more domains (HTTP stack, shared UI, global layouts, generic utils like date/image) goes to `layers/common/`; domain layers depend on `common`, never on each other. Sole sanctioned exceptions: auth consumes the auto-imported `accountsApi`; type-only `Profile` imports from `layers/accounts` (type imports are erased at build); `dashboard` consumes the auto-imported `<FarmsMenu>` component plus the `farm` composables (`useSelectedFarm`, `useFarmPlotsQuery`) and the weather-station list (its query, types and card); `sensors` consumes the same `farm` composables and station list plus the type-only `Plot`; and `predictions` consumes the same `farm` composables — every one runs one way only, `farm` never imports from `dashboard`, `sensors` or `predictions`. A sidebar nav entry pointing at another layer's route is just a `localePath()` string and creates no dependency.
- New domains (`farm`, `sensors`, `predictions`, …) are born as layers with their own `nuxt.config.ts` (`$meta: { name: '<layer>' }`).
- In-layer imports of types/utils/api use relative paths (no per-domain aliases); rely on Nuxt auto-imports for components/composables.
- Nuxt plugins that consume another plugin's injection must be named object plugins with `dependsOn: ['<name>']` — auto-registered layers load alphabetically, so cross-layer plugin order is otherwise accidental. Current names: `api`, `vue-query`, `i18n:plugin` (module-owned), `auth-init` — do not rename without updating dependents.
- Adding, renaming, or deleting a file under a layer's `app/{composables,utils}` — or adding a whole new layer, whose pages 404 until then — invalidates the running dev server's module graph: restart `npm run dev` before trusting the browser or e2e, otherwise the stale module 404s and route navigation aborts with no visible error.
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
- Light-mode `success` is raised to green-700 in `layers/common/app/assets/main.css` (Nuxt UI's green-500 is ~2:1 as text on its tinted badge background); keep that override, and check any other semantic colour used as badge text the same way.
- A selected/pressed control with text never uses the solid primary colour (white on light-mode primary is ~2.2:1, an axe contrast failure); mark the state with a neutral solid variant or an outline instead.

- Every lookup keyed by a backend semantic key (icons, colours, labels) needs a fallback: the backend adds keys over time and an unknown key must render generically, never crash.

- All Nuxt UI components use the `U` prefix, not `Nuxt` (this is the NuxtUI default).
  - **Wrong:** `<NuxtIcon>`, `<NuxtButton>`, `<NuxtForm>`, `<NuxtInput>`
  - **Correct:** `<UIcon>`, `<UButton>`, `<UForm>`, `<UInput>`
- Always use Lucide icons (`i-lucide-*`). Never use heroicons or any other icon set.
- Keep `icon.localApiEndpoint` off `/api/` (it is `/_nuxt_icon`): nginx routes all of `/api/` to Django, so icons not inlined by SSR 404 behind the proxy while working on `localhost:3000`.
- Every page sets its tab title with `useHead({ title: '...' })` (auto-imported) — never leave the default.
- A `<UAvatar>` (or a `:avatar="…"` on `<UButton>`) always passes `text` with the owner's initials from `getInitials()` — with neither `text` nor `alt` the fallback renders an empty `bg-elevated` circle that reads as a skeleton; mark it `aria-hidden` when a sibling label already names the control.
- The accessible name of a Nuxt UI/Reka control wrapped in `UFormField` is verified in the browser, never assumed: Reka wires its own English `aria-label` on several roots (a combobox trigger reads "Show popup", `UPagination` reads "Page 2"), which overrides the field label and leaks English into a Spanish UI.
- Never give a vertical `UNavigationMenu` item both `to` and `children`: its expand chevron renders as a `<span aria-expanded>`, a critical axe `aria-allowed-attr` violation; render a sub-entry as an indented sibling (`class: 'in-data-[collapsed=false]:ps-7'`).
- Never build a Tailwind class from a variable (`` `text-${color}` ``): Tailwind only ships classes written out in full in the source — map each case to its complete class name.
- A card with `overflow-hidden` inside a `flex-col` stack needs `shrink-0`: overflow makes its min-height 0, so when the panel is short it shrinks and clips its own content instead of the panel scrolling.
- To capitalise an `Intl` date use `first-letter:uppercase`, never `capitalize`, which title-cases every word ("30 De Septiembre").
- `UChatMessages`/`UChatMessage` type their messages and slot props against the AI SDK (`ai`), which is not installed: keep our own `ChatMessage` type (`{ id, role, parts: [{ type: 'text', text }] }`) and, inside a slot, look the message up again by `id` instead of reading the untyped slot prop.
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

### Charts (Unovis) & maps (Leaflet)

- A Leaflet map inside a page draws its vectors in an explicit pane (`map.createPane(name).style.zIndex = '400'`) and its container gets `isolate`: the default overlay pane can end up under the tiles, and Leaflet's own z-indexes otherwise escape over page menus; never wrap a map in `role="img"` — its attribution links make that a `nested-interactive` violation, use `<figure>` + `sr-only` `<figcaption>`.
- A chart tooltip that shows user-typed text (plot, farm, sensor names) is built as DOM with `textContent`, never an HTML string — the name would otherwise be parsed as markup.
- A `VisXYLabels` inside an XY container rendered nothing here; label marks with page text (a summary under the chart) instead.
- A time-of-day grouping (heatmap by hour, "at 18:00") is done client-side in the viewer's timezone — the backend buckets in UTC.

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

### PWA

- The manifest and service worker exist only in production builds (`devOptions` stays off so HMR is never served from a cache); icons and head links come from `public/logo.svg` via `pwa-assets.config.ts` — edit the SVG, never commit generated PNGs.
- Never run `nuxt build` inside `frontend/` while a dev server is up: both share `.nuxt/`. Verify a production build in a scratch copy (rsync without `node_modules`/`.nuxt`/`.output`, symlink `node_modules`), serve it with `PORT=… node .output/server/index.mjs`.
- The service worker must never precache HTML or runtime-cache `/api/`: pages are server-rendered per user and a cached reading would pass for a current one.
- Test installation on a phone through a tunnel with no browser interstitial (`cloudflared tunnel --url …`), never free ngrok: Chrome fetches the manifest without cookies, so ngrok answers it with its warning page and the app never becomes installable.

### Dependencies

- Install with `npm install <pkg>` (no `@version` pin) unless a specific version is strictly required.
