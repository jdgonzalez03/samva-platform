import type { NitroFetchOptions, NitroFetchRequest } from 'nitropack'
import { RefreshTokenError } from './errors'
import { refreshAccessToken } from './tokens'

type RequestOptions = NitroFetchOptions<NitroFetchRequest>
type RequestBody = RequestOptions['body']

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
  get: <T>(url: string) => request<T>(url),
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
