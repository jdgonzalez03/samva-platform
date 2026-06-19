import { RefreshTokenError } from './errors'
import { refreshAccessToken } from './tokens'

const api = () => useNuxtApp().$api

async function request<T>(url: string, opts?: Record<string, any>): Promise<T> {
  try {
    return await api()<T>(url, opts)
  } catch (error: any) {
    if (error?.status === 401) {
      const refreshed = await refreshAccessToken()
      if (!refreshed) throw new RefreshTokenError()
      return await api()<T>(url, opts)
    }
    throw error
  }
}

export const fetcher = {
  get:    <T>(url: string) => request<T>(url),
  post:   <T>(url: string, body?: any) => request<T>(url, { method: 'POST', body }),
  put:    <T>(url: string, body?: any) => request<T>(url, { method: 'PUT', body }),
  patch:  <T>(url: string, body?: any) => request<T>(url, { method: 'PATCH', body }),
  patchFormData: <T>(url: string, formData: FormData) =>
    request<T>(url, { method: 'PATCH', body: formData }),
  delete: <T>(url: string) => request<T>(url, { method: 'DELETE' }),
}
