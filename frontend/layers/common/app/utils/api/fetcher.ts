import type { NitroFetchOptions, NitroFetchRequest } from 'nitropack'
import { RefreshTokenError } from './errors'
import { refreshAccessToken } from './tokens'

type RequestOptions = NitroFetchOptions<NitroFetchRequest>
type RequestBody = RequestOptions['body']

// Deliberately narrower than ofetch's `query`: callers pass values, never a
// whole options bag, so nobody can slip a `baseURL`/`method` past the shared
// stack. ofetch drops `undefined` entries and encodes the rest.
export type QueryParams = Record<string, string | number | boolean | undefined>

const api = () => useNuxtApp().$api

async function request<T>(url: string, opts?: RequestOptions): Promise<T> {
  try {
    return await api()<T>(url, opts)
  } catch (error) {
    const status = (error as { status?: number } | null)?.status
    if (status === 401) {
      const refreshed = await refreshAccessToken()
      if (!refreshed) throw new RefreshTokenError()
      return await api()<T>(url, opts)
    }
    throw error
  }
}

export const fetcher = {
  get: <T>(url: string, query?: QueryParams) => request<T>(url, { query }),
  // `responseType: 'blob'` skips ofetch's JSON parsing. Going through `request`
  // rather than a bare fetch is what keeps the 401 → refresh → retry path — and
  // it also means an error body arrives as a Blob, not as parsed JSON.
  getBlob: (url: string, query?: QueryParams) =>
    request<Blob>(url, { query, responseType: 'blob' }),
  post: <T>(url: string, body?: RequestBody) =>
    request<T>(url, { method: 'POST', body }),
  put: <T>(url: string, body?: RequestBody) =>
    request<T>(url, { method: 'PUT', body }),
  patch: <T>(url: string, body?: RequestBody) =>
    request<T>(url, { method: 'PATCH', body }),
  patchFormData: <T>(url: string, formData: FormData) =>
    request<T>(url, { method: 'PATCH', body: formData }),
  delete: <T>(url: string) => request<T>(url, { method: 'DELETE' }),
}
