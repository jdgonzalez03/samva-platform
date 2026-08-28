import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { HISTORY_PAGE_SIZE } from '../constants/history'
import { SensorsQueryKey } from '../constants/query-keys'
import type { HistoryQueryFilters, ReadingsPage } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import { retryUnlessNotFound } from '#api/errors'
import { hasTokens } from '#api/tokens'

// A plain object in the key is safe — TanStack's `hashKey` sorts object keys —
// and reads far better than five positional refs.
export const historyReadingsQueryOptions = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  page: Ref<number>,
) => ({
  queryKey: [
    SensorsQueryKey.ROOT,
    SensorsQueryKey.HISTORY,
    SensorsQueryKey.READINGS,
    farmId,
    filters,
    page,
  ] as const,
  queryFn: (): Promise<ReadingsPage> =>
    sensorsApi.getHistoryReadings(farmId.value!, {
      ...filters.value,
      page: page.value,
      page_size: HISTORY_PAGE_SIZE,
    }),
})

export const useHistoryReadingsQuery = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  page: Ref<number>,
  isActive: Ref<boolean>,
) =>
  useQuery({
    ...historyReadingsQueryOptions(farmId, filters, page),
    enabled: () => hasTokens() && farmId.value !== null && isActive.value,
    // Paging keeps the previous page on screen instead of flashing a skeleton;
    // the table dims itself while `isPlaceholderData` is true.
    placeholderData: keepPreviousData,
    // A page past the end is DRF's 404.
    retry: retryUnlessNotFound,
  })
