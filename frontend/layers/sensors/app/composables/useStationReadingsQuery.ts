import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { HISTORY_PAGE_SIZE } from '../constants/history'
import { SensorsQueryKey } from '../constants/query-keys'
import type { StationQueryFilters, StationReadingsPage } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import {
  historyCacheKey,
  historyRequestFilters,
} from '../utils/history-filters'
import { retryUnlessNotFound } from '#api/errors'
import { hasTokens } from '#api/tokens'

export const stationReadingsQueryOptions = (
  stationId: Ref<number | null>,
  filters: Ref<StationQueryFilters>,
  live: Ref<boolean>,
  page: Ref<number>,
) => ({
  queryKey: [
    SensorsQueryKey.ROOT,
    SensorsQueryKey.STATION,
    stationId,
    SensorsQueryKey.READINGS,
    computed(() => historyCacheKey(filters.value, live.value)),
    page,
  ] as const,
  queryFn: (): Promise<StationReadingsPage> =>
    sensorsApi.getStationReadings(stationId.value!, {
      ...historyRequestFilters(filters.value, live.value, Date.now()),
      page: page.value,
      page_size: HISTORY_PAGE_SIZE,
    }),
})

export const useStationReadingsQuery = (
  stationId: Ref<number | null>,
  filters: Ref<StationQueryFilters>,
  live: Ref<boolean>,
  page: Ref<number>,
  isActive: Ref<boolean>,
) =>
  useQuery({
    ...stationReadingsQueryOptions(stationId, filters, live, page),
    enabled: () => hasTokens() && stationId.value !== null && isActive.value,
    // Paging keeps the previous page on screen; the table dims itself while
    // `isPlaceholderData` is true.
    placeholderData: keepPreviousData,
    // A page past the end is DRF's 404.
    retry: retryUnlessNotFound,
    // Newest readings come first, so only page 1 polls: on a later page every
    // poll would shift the rows under the reader.
    refetchInterval: computed(() =>
      live.value && page.value === 1 ? LIVE_REFRESH_INTERVAL_MS : false,
    ),
  })
