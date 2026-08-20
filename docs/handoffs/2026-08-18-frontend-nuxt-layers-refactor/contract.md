# api contract — frontend Nuxt Layers refactor

Summary: No backend changes. This is the authoritative inventory of every backend endpoint the
frontend consumes today, and the shape each layer's `api.ts` must implement over the common
fetcher. Backend code (`backend/accounts`, `backend/cms`, `backend/farmer`) is authoritative;
frontend drift is flagged below and must be fixed during Stage A.

## Path convention

All module paths are **relative to the fetcher's baseURL** (`runtimeConfig.public.apiBase`,
default `/api`; SSR uses `apiBaseServer`). Written without the `/api` prefix, no leading slash,
trailing slash required (Django): `accounts/me/`, `cms/landing/`.

**There is no `/api/auth/` mount on the backend.** Root `urls.py` mounts: `api/accounts/`
(accounts app — includes login + token endpoints), `api/cms/`, `api/core/`. The frontend `auth`
module therefore calls `accounts/...` paths — do not invent `auth/...` paths.

## Common fetcher (`layers/common`) — the shared contract

Every module `api.ts` builds on `fetcher` (`get/post/put/patch/patchFormData/delete`), which must:

1. **Bearer injection** — attach `Authorization: Bearer <accessToken>` when a token exists
   (via the `$api` `$fetch.create` plugin; tokens in `localStorage`, client only).
2. **401 → refresh → retry** — on any 401, `POST accounts/token/refresh/` with
   `{ refresh }`; on `200 { access: string }` store it and retry the original request **once**;
   on refresh failure clear both tokens and throw `RefreshTokenError` (statusCode 401).
   The refresh call itself uses raw `$fetch` (never recurses through `fetcher`).
3. **Error surface** — non-2xx rejects with ofetch's `FetchError`: `error.status` (HTTP code)
   and `error.data` (the backend JSON body, shapes below). No other normalization; modules and
   composables never catch inside `api.ts`.
4. **Isomorphic use** — `cmsApi` is called during SSR (`useAsyncData`), so the `$api` plugin /
   fetcher must work server-side: baseURL = `apiBaseServer` on server, `public.apiBase` on
   client; token read is guarded (no `localStorage` on server; public endpoints need no token).

Owned by `layers/common`: `fetcher`, `$api` plugin, `tokens.ts`
(`get/set/clearTokens`, `hasTokens`, `refreshAccessToken`), `errors.ts`
(`RefreshTokenError`, `NotFoundError`). `#api` alias re-maps here.

## Entities (types per module)

```ts
// layers/auth (types/auth.ts)
interface LoginPayload { email: string; password: string }
interface AuthTokens   { refresh: string; access: string }
interface AuthResponse { message: string; tokens: AuthTokens }

// layers/accounts (types/profile.ts)
interface OrganizationProfile {
  id: number; name: string | null; nit: string | null; created_at: string  // ISO datetime
}
interface FarmerProfile {
  id: number
  first_name: string | null; last_name: string | null
  document_type: 'CC' | 'CE' | 'PASSPORT' | null
  document_number: string | null
  gender: 'M' | 'F' | null
  phone_number: string | null; city: string | null
  department: string | null; address: string | null
  avatar: string | null                    // media URL when set
  is_active: boolean
  organization: OrganizationProfile | null
  created_at: string                       // ISO datetime
}
interface Profile { id: number; email: string; farmer: FarmerProfile }
interface UpdateProfilePayload {           // all optional; PATCH is partial
  first_name?: string; last_name?: string; document_type?: string
  document_number?: string; gender?: string; phone_number?: string
  city?: string; department?: string; address?: string
  avatar?: File                            // presence switches to multipart
}

// layers/cms (types/landing.ts, types/blocks.ts, types/common.ts)
interface LandingData { title: string; body: StreamBlock[] }
// StreamBlock union + Image etc. stay as currently defined in shared/types/cms/*
```

## Endpoints

### `layers/auth` → exported object `authApi`

| Method + path | Auth | Request | 2xx | Errors |
| --- | --- | --- | --- | --- |
| `POST accounts/login/` | public | JSON `{ email: string, password: string }` (both required) | `200` `AuthResponse` | `400` `{ email?: string[], password?: string[] }` (DRF validation) · `401` `{ error: "Invalid email or password" }` |
| `POST accounts/token/refresh/` | public (refresh token in body) | `{ refresh: string }` | `200` `{ access: string }` (no rotation — no `refresh` in response) | `400` `{ refresh: string[] }` · `401` `{ detail: string, code: "token_not_valid" }` |

```ts
export const authApi = {
  login(data: LoginPayload) {
    return fetcher.post<AuthResponse>('accounts/login/', data)
  },
}
```

- Token refresh is **not** on `authApi` — it belongs to `layers/common/tokens.ts`
  (`refreshAccessToken`), since the fetcher itself drives it. Auth layer only *writes*
  tokens after login (`setTokens`).
- Logout has **no backend endpoint** — it is client-side only (`clearTokens` + state reset
  + redirect). Do not add a logout call.
- `POST accounts/token/verify/` exists on the backend but is consumed by no frontend surface —
  excluded from the contract (YAGNI; do not add it to `authApi`).

### `layers/accounts` → exported object `accountsApi`

| Method + path | Auth | Request | 2xx | Errors |
| --- | --- | --- | --- | --- |
| `GET accounts/me/` | Bearer | — | `200` `Profile` | `401` `{ detail: string }` |
| `PATCH accounts/me/` | Bearer | Partial `UpdateProfilePayload`: JSON when no file; `multipart/form-data` when `avatar` present (empty/`undefined`/`null` values omitted from the form) | `200` `Profile` (full, re-serialized) | `400` `{ <field>: string[] }` · `401` `{ detail: string }` |

```ts
export const accountsApi = {
  getMe() { return fetcher.get<Profile>('accounts/me/') },
  updateProfile(data: UpdateProfilePayload) { /* JSON or patchFormData as above */ },
}
```

### `layers/cms` → exported object `cmsApi` (new — fixes the direct `useFetch` violation)

| Method + path | Auth | Request | 2xx | Errors |
| --- | --- | --- | --- | --- |
| `GET cms/landing/` | public | — | `200` `LandingData` | `404` `{ detail: "Landing page not found" }` |

```ts
export const cmsApi = {
  getLanding() { return fetcher.get<LandingData>('cms/landing/') },
}
```

## Surfaces

| Surface / route | Layer | Endpoint(s) |
| --- | --- | --- |
| `/login` (login form; also `useAuth.login`) | auth | `POST accounts/login/` then `GET accounts/me/` |
| `auth`/`guest` middleware + `auth-init` plugin session restore | auth (uses accountsApi) | `GET accounts/me/` |
| `/dashboard/profile` (view + update, "member since") | accounts | `GET/PATCH accounts/me/` |
| `/` landing (SSR via `useAsyncData` wrapping `cmsApi` — **not** Vue Query) | cms | `GET cms/landing/` |
| Any 401 anywhere while authenticated | common (fetcher) | `POST accounts/token/refresh/` |

## Drift found (backend authoritative — fix in Stage A)

1. **`authApi.login` bypasses the fetcher** (raw `fetch()` + hand-rolled error). Must become
   `fetcher.post<AuthResponse>('accounts/login/', data)`; callers switch from `Error.message`
   to `FetchError.status`/`.data.error`. Drop the `endpoints/login.ts` indirection — methods
   live directly on the api object.
2. **Nullable vs optional**: backend serializers always emit every field, with `null` for
   empty — frontend types currently use `?` (undefined). Types above use `| null`; update them.
3. **Error envelope is not uniform**: login 401 uses `{ error }`, everything else DRF
   `{ detail }` or field-map `{ field: string[] }`. Frontend error handling must read the shape
   per endpoint as tabled — do not assume one envelope.
4. **Landing page** calls `useFetch` directly with `${apiBase}/cms/landing/` — replace with
   `useAsyncData('cms-landing', () => cmsApi.getLanding())`.

## Notes

- No pagination anywhere in scope; no paginated collections → no deep-link/single-item gap.
- Vue Query (Stage B) wraps these same `api.ts` methods in module composables
  (`useQuery`/`useMutation`, `[<Module>QueryKey.ROOT, ...]` keys); it does not change any
  request/response shape in this contract.
- Type names stay as currently exported (`LoginPayload`, `AuthResponse`, `Profile`, …) — the
  refactor is behavior-preserving; only their file location moves into each layer.
- `layers/dashboard` has no api module today (no dashboard-specific endpoints exist yet);
  future `farm`/`sensors`/`predictions` modules get their own `api.ts` when born as layers.

Open questions: none.

## Proposed improvements

- `frontend/CLAUDE.md` (API layer section): "Module `api.ts` paths are relative to the
  fetcher baseURL (`/api`) — never prefix `/api` or hardcode the host; auth/login/token
  endpoints live under `accounts/` (there is no `auth/` mount on the backend)."
- `backend/CLAUDE.md` (new API rule): "Error responses use DRF conventions — `{ detail: str }`
  for auth/not-found and the field→messages map for validation; never invent ad-hoc keys like
  `{ error: ... }`" (the login view predates this; align it whenever that view is next touched).
