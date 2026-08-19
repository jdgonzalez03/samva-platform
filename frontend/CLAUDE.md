# Frontend — Claude Code

Guidelines for the Nuxt frontend (`frontend/`). Stack: Nuxt 4 + Nuxt UI + TypeScript (exact pins in `package.json`). Before Vue/Nuxt work, consult the project skills: `nuxt-ui`, `vue-best-practices`, `vue-router-best-practices`, `vue-testing-best-practices`, `accessibility`.

## Guidelines

### HTTP & API layer

- Never call `fetch`/`$fetch`/`useFetch` directly; all HTTP goes through the shared `fetcher` (`app/utils/api/fetcher.ts`), which wraps the `$api` plugin (base URL, JWT header) and auto-refreshes tokens on 401.
- Endpoints live in domain API modules under `app/utils/api/<domain>/` (e.g. `authApi`, `accountsApi`); composables and components call those modules — never `fetcher` directly.
- Import API-layer code via the `#api` alias (e.g. `import { authApi } from '#api/auth'`), not relative paths.

### Composables & state

- Shared state lives in domain composables under `app/composables/<domain>/` (`useAuth`, etc.) — module-level `ref`s, no Pinia.
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

### Formatting & lint

- Prettier owns formatting (`npm run format`, format-on-save); ESLint only lints — never add stylistic/formatting rules to `eslint.config.mjs` (conflicts stay disabled via `eslint-config-prettier`).

### Dependencies

- Install with `npm install <pkg>` (no `@version` pin) unless a specific version is strictly required.
