import { getAccessToken } from '#api/tokens'

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()

  const api = $fetch.create({
    baseURL: config.public.apiBase as string,
    onRequest({ options }) {
      const token = getAccessToken()
      if (token) {
        options.headers.set('Authorization', `Bearer ${token}`)
      }
    },
  })

  return {
    provide: { api },
  }
})
