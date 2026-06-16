import { hasTokens } from '#api/tokens'

export default defineNuxtRouteMiddleware((to, from) => {
  if (hasTokens()) {
    return navigateTo('/dashboard')
  }
})
