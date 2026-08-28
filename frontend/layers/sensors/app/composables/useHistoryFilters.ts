import type { LocationQueryRaw } from 'vue-router'
import type { HistoryQueryFilters, SensorSemanticKey } from '../types/sensors'
import {
  DEFAULT_HISTORY_VIEW,
  DEFAULT_RANGE_PRESET,
  getStoredHistoryView,
  parseCalendarDate,
  parseHistoryView,
  parsePageNumber,
  parsePlotId,
  parseRangePreset,
  parseVariableKey,
  resolveRange,
  setStoredHistoryView,
  type HistoryRangePreset,
  type HistoryView,
} from '../utils/history-filters'

/**
 * The URL owns every history filter, so reloading or sharing the link
 * reproduces the exact view. `localStorage` holds the view toggle only, and is
 * consulted after mount — reading it during setup would make the client render
 * a different tab than the server did. A stored `plot`/`variable` is
 * deliberately not persisted: it could belong to a farm that is no longer
 * selected.
 */
export const useHistoryFilters = () => {
  const route = useRoute()
  const router = useRouter()
  const { selectedFarm } = useSelectedFarm()

  const farmId = computed(() => selectedFarm.value?.id ?? null)

  const viewFallback = shallowRef<HistoryView>(DEFAULT_HISTORY_VIEW)

  /**
   * "Now" is pinned. Reading `Date.now()` inside the computed that builds the
   * range would hand Vue Query a new key on every re-render and refetch
   * forever; the anchor moves only when the range itself changes.
   */
  const rangeAnchor = shallowRef(Date.now())

  onMounted(() => {
    if (parseHistoryView(route.query.view)) return

    viewFallback.value = getStoredHistoryView() ?? DEFAULT_HISTORY_VIEW
    // `replace`, not `push`: writing the resolved view into the URL without a
    // history entry is what makes Back return to the previous page instead of
    // re-reading storage.
    void router.replace({ query: { ...route.query, view: viewFallback.value } })
  })

  const view = computed<HistoryView>(
    () => parseHistoryView(route.query.view) ?? viewFallback.value,
  )

  const { data: plots, isPending: plotsPending } = useFarmPlotsQuery(farmId)

  const requestedPlotId = computed(() => parsePlotId(route.query.plot))

  /**
   * A plot id only counts once the active farm's own list confirms it. A shared
   * link, or a farm remembered from another visit, easily pairs farm B with a
   * plot of farm A — and that pair is a 404 on every history endpoint, one no
   * "Retry" can ever turn into data.
   */
  const plotId = computed(() =>
    requestedPlotId.value !== null &&
    plots.value?.some((plot) => plot.id === requestedPlotId.value)
      ? requestedPlotId.value
      : null,
  )

  /**
   * False while a `?plot=` from the URL is still unconfirmed. The history
   * queries wait on it, so the pending verdict never leaks into a request:
   * firing early would either 404 with the orphan id or spend a farm-wide
   * request that the confirmed plot immediately replaces.
   */
  const filtersReady = computed(
    () => requestedPlotId.value === null || !plotsPending.value,
  )

  const variable = computed(() => parseVariableKey(route.query.variable))
  const rangePreset = computed(
    () => parseRangePreset(route.query.range) ?? DEFAULT_RANGE_PRESET,
  )
  const customFrom = computed(() => parseCalendarDate(route.query.from))
  const customTo = computed(() => parseCalendarDate(route.query.to))
  const page = computed(() => parsePageNumber(route.query.page))

  const resolvedRange = computed(() =>
    resolveRange(
      rangePreset.value,
      customFrom.value,
      customTo.value,
      rangeAnchor.value,
    ),
  )
  const rangeIssue = computed(() => resolvedRange.value.issue)

  const filters = computed<HistoryQueryFilters>(() => ({
    // Absent, never `null`: the backend reads a missing key as "all".
    ...(plotId.value !== null ? { plot: plotId.value } : {}),
    ...(variable.value !== null ? { variable: variable.value } : {}),
    date_from: resolvedRange.value.date_from,
    date_to: resolvedRange.value.date_to,
  }))

  const hasActiveFilters = computed(
    () =>
      plotId.value !== null ||
      variable.value !== null ||
      rangePreset.value !== DEFAULT_RANGE_PRESET,
  )

  const applyQuery = (
    patch: Record<string, string | undefined>,
    options: { resetPage?: boolean; replace?: boolean } = {},
  ): void => {
    const merged: Record<string, unknown> = { ...route.query, ...patch }
    // Page 1 is the absence of `?page`, so clearing it is how a filter change
    // sends the user back to the first page.
    if (options.resetPage !== false) merged.page = undefined
    // A cleared filter drops out of the URL entirely — never `plot=null`, which
    // the backend would read as a plot id.
    const query = Object.fromEntries(
      Object.entries(merged).filter(([, value]) => value !== undefined),
    ) as LocationQueryRaw

    if (options.replace) void router.replace({ query })
    else void router.push({ query })
  }

  const setView = (next: string | number | undefined): void => {
    const parsed = parseHistoryView(next)
    if (!parsed || parsed === view.value) return

    setStoredHistoryView(parsed)
    // The view toggle is orthogonal to the filters, so it keeps the page.
    applyQuery({ view: parsed }, { resetPage: false })
  }

  const setPlot = (next: number | null): void => {
    if (next === plotId.value) return
    applyQuery({ plot: next === null ? undefined : String(next) })
  }

  const setVariable = (next: SensorSemanticKey | null): void => {
    if (next === variable.value) return
    applyQuery({ variable: next ?? undefined })
  }

  const setRangePreset = (next: HistoryRangePreset): void => {
    if (next === rangePreset.value) return
    rangeAnchor.value = Date.now()
    applyQuery({
      range: next,
      // A preset ignores the custom pair; leaving it behind would resurrect a
      // stale window the moment the user returns to "custom".
      ...(next === 'custom' ? {} : { from: undefined, to: undefined }),
    })
  }

  const setCustomRange = (from: string, to: string): void => {
    rangeAnchor.value = Date.now()
    applyQuery({ range: 'custom', from, to })
  }

  const setPage = (next: number): void => {
    if (next === page.value) return
    const value = next <= 1 ? undefined : String(next)
    applyQuery({ page: value }, { resetPage: false })
  }

  const resetFilters = (): void => {
    rangeAnchor.value = Date.now()
    applyQuery({
      plot: undefined,
      variable: undefined,
      range: undefined,
      from: undefined,
      to: undefined,
    })
  }

  // Drops the id the farm disowned out of the URL, so the link stops naming a
  // filter that is not in effect. Driven by the plot list rather than by a farm
  // change, which is what covers the first resolution: a shared link arrives
  // with its `plot` already set and no previous farm to compare against.
  // `replace`, because the stale combination is not a state worth stepping Back
  // into.
  watch(
    [plots, requestedPlotId],
    () => {
      if (requestedPlotId.value === null || plots.value === undefined) return
      if (plots.value.some((plot) => plot.id === requestedPlotId.value)) return
      applyQuery({ plot: undefined }, { replace: true })
    },
    { immediate: true },
  )

  return {
    farmId,
    selectedFarm,
    view,
    plotId,
    variable,
    rangePreset,
    customFrom,
    customTo,
    page,
    filters,
    filtersReady,
    rangeIssue,
    hasActiveFilters,
    setView,
    setPlot,
    setVariable,
    setRangePreset,
    setCustomRange,
    setPage,
    resetFilters,
  }
}
