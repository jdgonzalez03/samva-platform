import type { QueryClient } from '@tanstack/vue-query'
import { hasTokens, clearTokens } from '#api/tokens'

export default defineNuxtPlugin({
  name: 'auth-init',
  // The auth layer registers before common (alphabetical layer order), so the
  // session restore must explicitly wait for the `$api` and Vue Query plugins.
  // `i18n:plugin` is required for the locale-aware /login redirect below.
  dependsOn: ['api', 'vue-query', 'i18n:plugin'],
  async setup(nuxtApp) {
    if (!hasTokens()) return

    // Captured before any await so the composable runs within plugin context.
    const localePath = useLocalePath()
    const queryClient = nuxtApp.$queryClient as QueryClient
    const options = profileQueryOptions()

    // Session restore: prime the shared profile query before the app mounts.
    await queryClient.prefetchQuery(options)

    // prefetchQuery swallows errors — an unrestorable session (refresh failed,
    // profile unreachable) is cleaned up like the old fetchMe → logout path.
    if (queryClient.getQueryState(options.queryKey)?.status === 'error') {
      clearTokens()
      queryClient.removeQueries()
      await navigateTo(localePath('/login'))
    }
  },
})
