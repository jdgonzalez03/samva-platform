import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { AccountsQueryKey } from '../constants/query-keys'
import type { UpdateProfilePayload } from '../types/profile'
import { accountsApi } from '../utils/api/accounts'
import { hasTokens } from '#api/tokens'

// Single definition of the profile query so every consumer (profile page,
// useAuth-derived user state, auth-init prefetch) shares one cache entry.
export const profileQueryOptions = () => ({
  queryKey: [AccountsQueryKey.ROOT, AccountsQueryKey.ME] as const,
  queryFn: () => accountsApi.getMe(),
})

export const useProfileQuery = () =>
  useQuery({
    ...profileQueryOptions(),
    // Getter so the token check runs at observer creation on the client;
    // on the server tokens are always null, keeping the query SSR-inert.
    enabled: () => hasTokens(),
  })

export const useUpdateProfileMutation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: UpdateProfilePayload) =>
      accountsApi.updateProfile(payload),
    // Returning the promise makes `mutateAsync` resolve only after the
    // profile refetch completes — callers toast over fresh data.
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [AccountsQueryKey.ROOT] }),
  })
}
