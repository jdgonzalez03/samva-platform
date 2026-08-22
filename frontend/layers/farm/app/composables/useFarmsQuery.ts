import { useQuery } from '@tanstack/vue-query'
import { FarmQueryKey } from '../constants/query-keys'
import { farmApi } from '../utils/api/farm'
import { hasTokens } from '#api/tokens'

// Single definition of the farm list query so the sidebar switcher and every
// dashboard page share one cache entry.
export const farmsQueryOptions = () => ({
  queryKey: [FarmQueryKey.ROOT, FarmQueryKey.LIST] as const,
  queryFn: () => farmApi.getFarms(),
})

export const useFarmsQuery = () =>
  useQuery({
    ...farmsQueryOptions(),
    // Getter so the token check runs at observer creation on the client;
    // on the server tokens are always null, keeping the query SSR-inert.
    enabled: () => hasTokens(),
  })
