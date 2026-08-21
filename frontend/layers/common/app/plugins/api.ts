import { getAccessToken } from '#api/tokens'

// Universal plugin: SSR requests go straight to the backend (apiBaseServer),
// client requests go through the public base (proxied in the docker topology).
export default defineNuxtPlugin({
  name: 'api',
  setup() {
    const config = useRuntimeConfig()

    const api = $fetch.create({
      baseURL: import.meta.server
        ? (config.apiBaseServer as string)
        : (config.public.apiBase as string),
      onRequest({ options }) {
        // getAccessToken() is null on the server; public SSR calls need no token.
        const token = getAccessToken()
        if (token) {
          options.headers.set('Authorization', `Bearer ${token}`)
        }
      },
    })

    return {
      provide: { api },
    }
  },
})
