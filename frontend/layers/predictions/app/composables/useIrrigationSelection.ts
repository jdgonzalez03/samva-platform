import type { LocationQueryRaw } from 'vue-router'
import {
  AVERAGE_HOURS_OPTIONS,
  DEFAULT_AVERAGE_HOURS,
} from '../constants/predictions'

const parsePositiveInteger = (value: unknown): number | null => {
  const parsed = Number(Array.isArray(value) ? value[0] : value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

// The URL owns the plot and the averaging window, so a reload or a shared link
// reproduces the same selection. A `?plot=` only counts once the selected
// farm's own plot list confirms it; otherwise the first plot is used.
export const useIrrigationSelection = () => {
  const route = useRoute()
  const router = useRouter()
  const { selectedFarm, isPending: farmsPending } = useSelectedFarm()

  const farmId = computed(() => selectedFarm.value?.id ?? null)
  const { data: plots, isPending: plotsPending } = useFarmPlotsQuery(farmId)
  const plotList = computed(() => plots.value ?? [])

  const plotId = computed<number | null>(() => {
    const requested = parsePositiveInteger(route.query.plot)
    if (plotList.value.some((plot) => plot.id === requested)) return requested
    return plotList.value[0]?.id ?? null
  })

  const hours = computed<number>(() => {
    const requested = parsePositiveInteger(route.query.hours)
    return (
      AVERAGE_HOURS_OPTIONS.find((option) => option === requested) ??
      DEFAULT_AVERAGE_HOURS
    )
  })

  const updateQuery = (patch: Record<string, string>): void => {
    void router.replace({
      query: { ...route.query, ...patch } as LocationQueryRaw,
    })
  }

  const setPlot = (next: number): void => updateQuery({ plot: String(next) })
  const setHours = (next: number): void => updateQuery({ hours: String(next) })

  return {
    selectedFarm,
    farmsPending,
    plotList,
    plotsPending,
    plotId,
    hours,
    setPlot,
    setHours,
  }
}
