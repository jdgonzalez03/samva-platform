import { useMutation, useQueryClient } from '@tanstack/vue-query'
import type { LoginPayload } from '../types/auth'
import { authApi } from '../utils/api/auth'
import { setTokens, clearTokens } from '#api/tokens'

export const useAuth = () => {
  const router = useRouter()
  const localePath = useLocalePath()
  const queryClient = useQueryClient()
  // Shared profile query cache: sidebar, dropdown, and profile page all
  // derive the user from the same entry (auto-imported from layers/accounts).
  const profileQuery = useProfileQuery()

  const loginMutation = useMutation({
    mutationFn: (payload: LoginPayload) => authApi.login(payload),
    onSuccess: async (data) => {
      setTokens(data.tokens.access, data.tokens.refresh)
      // Awaited so the login button spinner covers the profile fetch and a
      // failed fetch rejects `login()` exactly like the pre-Vue Query flow.
      await queryClient.fetchQuery(profileQueryOptions())
    },
  })

  const logoutMutation = useMutation({
    // Client-side only per contract — no backend logout endpoint.
    mutationFn: async () => {
      clearTokens()
      await router.push(localePath('/login'))
      // Cache cleared after navigation so no observer refetches token-less.
      queryClient.removeQueries()
    },
  })

  const user = computed(() => profileQuery.data.value ?? null)
  const isAuthenticated = computed(() => !!profileQuery.data.value)
  const loading = computed(() => loginMutation.isPending.value)

  const login = (payload: LoginPayload) => loginMutation.mutateAsync(payload)
  const logout = () => logoutMutation.mutate()
  const refetchProfile = (): void => {
    void profileQuery.refetch()
  }

  return {
    user,
    isAuthenticated,
    loading,
    profilePending: profileQuery.isPending,
    profileError: profileQuery.isError,
    refetchProfile,
    login,
    logout,
  }
}
