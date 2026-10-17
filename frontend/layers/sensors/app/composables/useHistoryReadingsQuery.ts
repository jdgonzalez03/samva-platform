import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { HISTORY_PAGE_SIZE } from '../constants/history'
import { SensorsQueryKey } from '../constants/query-keys'
import type { HistoryQueryFilters, ReadingsPage } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import {
  historyCacheKey,
  historyRequestFilters,
} from '../utils/history-filters'
import { retryUnlessNotFound } from '#api/errors'
import { hasTokens } from '#api/tokens'

// A plain object in the key is safe — TanStack's `hashKey` sorts object keys —
// and reads far better than five positional refs.
export const historyReadingsQueryOptions = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  live: Ref<boolean>,
  page: Ref<number>,
) => ({
  queryKey: [
    SensorsQueryKey.ROOT,
    SensorsQueryKey.HISTORY,
    SensorsQueryKey.READINGS,
    farmId,
    computed(() => historyCacheKey(filters.value, live.value)),
    page,
  ] as const,
  queryFn: (): Promise<ReadingsPage> =>
    sensorsApi.getHistoryReadings(farmId.value!, {
      ...historyRequestFilters(filters.value, live.value, Date.now()),
      page: page.value,
      page_size: HISTORY_PAGE_SIZE,
    }),
})

export const useHistoryReadingsQuery = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  live: Ref<boolean>,
  page: Ref<number>,
  isActive: Ref<boolean>,
) =>
  useQuery({
    ...historyReadingsQueryOptions(farmId, filters, live, page),
    enabled: () => hasTokens() && farmId.value !== null && isActive.value,
    // Paging keeps the previous page on screen instead of flashing a skeleton;
    // the table dims itself while `isPlaceholderData` is true.
    placeholderData: keepPreviousData,
    // A page past the end is DRF's 404.
    retry: retryUnlessNotFound,
    // Newest readings come first, so only page 1 polls: on a later page every
    // poll would shift the rows under the reader by the readings that arrived.
    refetchInterval: computed(() =>
      live.value && page.value === 1 ? LIVE_REFRESH_INTERVAL_MS : false,
    ),
  })
