import type { LocationQueryRaw } from 'vue-router'
import type { StationQueryFilters } from '../types/sensors'
import { parsePageNumber, resolveRange } from '../utils/history-filters'
import {
  DEFAULT_STATION_RANGE,
  parseStationRange,
  type StationRangePreset,
} from '../utils/station-filters'

// The URL owns the range and the readings page, so reloading or sharing the
// link reproduces the exact view.
export const useStationFilters = () => {
  const route = useRoute()
  const router = useRouter()

  // "Now" is pinned: reading `Date.now()` inside the range computed would hand
  // Vue Query a new key on every re-render. Live queries slide the window to
  // the moment of each request themselves.
  const rangeAnchor = shallowRef(Date.now())

  const rangePreset = computed<StationRangePreset>(
    () => parseStationRange(route.query.range) ?? DEFAULT_STATION_RANGE,
  )
  const page = computed(() => parsePageNumber(route.query.page))

  const resolvedRange = computed(() =>
    resolveRange(rangePreset.value, null, null, rangeAnchor.value),
  )
  const isLiveRange = computed(() => resolvedRange.value.live)

  const filters = computed<StationQueryFilters>(() => ({
    date_from: resolvedRange.value.date_from,
    date_to: resolvedRange.value.date_to,
  }))

  const applyQuery = (patch: Record<string, string | undefined>): void => {
    const merged: Record<string, unknown> = { ...route.query, ...patch }
    const query = Object.fromEntries(
      Object.entries(merged).filter(([, value]) => value !== undefined),
    ) as LocationQueryRaw
    void router.push({ query })
  }

  const setRangePreset = (next: StationRangePreset): void => {
    if (next === rangePreset.value) return
    rangeAnchor.value = Date.now()
    // Page 1 is the absence of `?page`: a new range starts from the newest row.
    applyQuery({ range: next, page: undefined })
  }

  const setPage = (next: number): void => {
    if (next === page.value) return
    applyQuery({ page: next <= 1 ? undefined : String(next) })
  }

  return { rangePreset, page, filters, isLiveRange, setRangePreset, setPage }
}
