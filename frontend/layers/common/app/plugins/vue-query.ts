import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'

// Universal plugin so a fresh QueryClient exists per SSR request (no state
// leakage across requests). All queries are client-side (enabled gates on
// tokens), so no dehydration/hydration is needed — the SSR landing stays on
// `useAsyncData` + `cmsApi`.
export default defineNuxtPlugin({
  name: 'vue-query',
  setup(nuxtApp) {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 30_000,
          retry: 1,
        },
      },
    })

    nuxtApp.vueApp.use(VueQueryPlugin, { queryClient })

    return {
      provide: { queryClient },
    }
  },
})
