import { RefreshTokenError } from './errors'

//TODO: Maybe we need to move this into useAuth in future
function refreshAccessToken(): Promise<boolean> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return Promise.resolve(false)

  const config = useRuntimeConfig()
  return $fetch<{ access: string }>('/accounts/token/refresh/', {
    baseURL: config.public.apiBase as string,
    method: 'POST',
    body: { refresh: refreshToken },
  })
    .then(data => { localStorage.setItem('access_token', data.access); return true })
    .catch(() => { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); return false })
}

const api = () => useNuxtApp().$api

const addPrefixToEndpoint = (endpoint: string) => `api/${endpoint}`

async function request<T>(url: string, opts?: Record<string, any>): Promise<T> {
  try {
    return await api()<T>(addPrefixToEndpoint(url), opts)
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
  delete: <T>(url: string) => request<T>(url, { method: 'DELETE' }),
}
