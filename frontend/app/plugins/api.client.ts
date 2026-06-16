export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()

  const api = $fetch.create({
    baseURL: config.public.apiBase as string,
    onRequest({ options }) {
      //TODO: Reemplazar con el metodo getAccessToken, etc
      const token = localStorage.getItem('access_token')
      if (token) {
        options.headers.set('Authorization', `Bearer ${token}`)
      }
    },
  })

  return {
    provide: { api },
  }
})
