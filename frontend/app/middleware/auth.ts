export default defineNuxtRouteMiddleware((to, from) => {
  const isAuthenticated = false
//TODO: Update this logic to check actual authentication status, e.g., by checking a token or session
  if (!isAuthenticated) {
    console.log('User is not authenticated, redirecting to login page...')
    return navigateTo('/login')
  }
})