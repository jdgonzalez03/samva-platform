import { hasTokens } from '#api/tokens'

export default defineNuxtRouteMiddleware(() => {
  // Tokens live in localStorage; the auth decision happens client-side after hydration.
  if (import.meta.server) return

  if (!hasTokens()) {
    const localePath = useLocalePath()
    return navigateTo(localePath('/login'))
  }
})
