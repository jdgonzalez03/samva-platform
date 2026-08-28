<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import { CHART_HEIGHT_CLASS, HISTORY_PAGE_SIZE } from '../../constants/history'
import type { ExportFormat } from '../../types/sensors'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

// Which shape of chart the filters ask for. The Charts/Table toggle is
// orthogonal to it: the table serves every mode, because the readings endpoint
// already answers the farm-wide case too.
//
type HistoryDisplayMode = 'plotAverages' | 'allVariables' | 'singleVariable'

const { t, locale } = useI18n()

const { isPending: farmsPending } = useSelectedFarm()

const {
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
} = useHistoryFilters()

const { data: plots, isPending: plotsPending } = useFarmPlotsQuery(farmId)

const { data: variables, isPending: variablesPending } =
  useHistoryVariablesQuery(farmId, plotId, filtersReady)

const isTableView = computed(() => view.value === 'table')
const isChartView = computed(() => view.value === 'chart')

// The view decides which data the page needs; `filtersReady` decides when the
// filters are trustworthy enough to ask for it.
const isTableQueryEnabled = computed(
  () => isTableView.value && filtersReady.value,
)
const isChartQueryEnabled = computed(
  () => isChartView.value && filtersReady.value,
)

const displayMode = computed<HistoryDisplayMode>(() => {
  if (plotId.value === null) return 'plotAverages'
  return variable.value === null ? 'allVariables' : 'singleVariable'
})

const {
  data: readingsPage,
  isPending: readingsPending,
  isPlaceholderData: readingsIsPlaceholder,
  isError: readingsError,
  error: readingsErrorObject,
  refetch: refetchReadingsQuery,
} = useHistoryReadingsQuery(farmId, filters, page, isTableQueryEnabled)

const {
  data: series,
  isPending: seriesPending,
  isError: seriesError,
  refetch: refetchSeriesQuery,
} = useHistorySeriesQuery(farmId, filters, isChartQueryEnabled)

const {
  data: averages,
  isPending: averagesPending,
  isError: averagesError,
  refetch: refetchAveragesQuery,
} = useHistoryPlotAveragesQuery(farmId, filters, isChartQueryEnabled)

const { exportHistory, isExporting, exportError } = useHistoryExport()

const plotList = computed(() => plots.value ?? [])
const variableList = computed(() => variables.value ?? [])
const readings = computed(() => readingsPage.value?.results ?? [])
const readingsCount = computed(() => readingsPage.value?.count ?? 0)
const seriesList = computed(() => series.value ?? [])
const averagesList = computed(() => averages.value ?? [])

const pageCount = computed(() =>
  Math.max(1, Math.ceil(readingsCount.value / HISTORY_PAGE_SIZE)),
)

const readingsErrorStatus = computed(
  () =>
    (readingsErrorObject.value as { status?: number } | null)?.status ?? null,
)

// A page past the last one: either the count already says so, or DRF answered
// the 404 it reserves for that case. A bookmarked or shared `?page=` outlives
// the rows it pointed at, and no amount of retrying turns that 404 into data.
//
const isPageOutOfRange = computed(() => {
  if (page.value <= 1) return false
  if (readingsErrorStatus.value === 404) return true
  return readingsPage.value !== undefined && page.value > pageCount.value
})

// `immediate`, because the out-of-range value arrives with the very first
// render on a shared link: a plain watcher waits for a change that never comes
// once the request has failed. The 404 carries no count to clamp against, so
// the first page is the only one known to exist.
watch(
  [isPageOutOfRange, pageCount],
  () => {
    if (!isPageOutOfRange.value) return
    setPage(readingsErrorStatus.value === 404 ? 1 : pageCount.value)
  },
  { immediate: true },
)

const chartCount = computed(() =>
  displayMode.value === 'plotAverages'
    ? new Set(averagesList.value.map((average) => average.variable_id)).size
    : seriesList.value.length,
)

const hasResults = computed(() => {
  if (isTableView.value) return readingsCount.value > 0
  return chartCount.value > 0
})

const numberFormatter = computed(() => new Intl.NumberFormat(locale.value))

// Announced politely, never focused: a filter or page change must report its
// result without yanking the caret away from the control the user just used
// (2.4.3, 4.1.3). Empty while pending, so only settled counts are read out.
//
const liveStatus = computed(() => {
  if (isTableView.value) {
    if (readingsPending.value || readingsIsPlaceholder.value) return ''
    // A count of zero over a page that does not exist is not a result worth
    // announcing; the alert or the bounce to page 1 speaks instead.
    if (readingsError.value || isPageOutOfRange.value) return ''
    return t(
      'sensors.history.status.table',
      {
        count: numberFormatter.value.format(readingsCount.value),
        page: page.value,
        pages: pageCount.value,
      },
      readingsCount.value,
    )
  }

  const pending =
    displayMode.value === 'plotAverages'
      ? averagesPending.value
      : seriesPending.value
  if (pending) return ''

  return t(
    'sensors.history.status.charts',
    { count: chartCount.value },
    chartCount.value,
  )
})

const viewItems = computed<TabsItem[]>(() => [
  {
    label: t('sensors.history.view.chart'),
    icon: 'i-lucide-chart-line',
    value: 'chart',
    slot: 'chart' as const,
  },
  {
    label: t('sensors.history.view.table'),
    icon: 'i-lucide-table',
    value: 'table',
    slot: 'table' as const,
  },
])

// Template handlers must return void: vue-tsc rejects a promise on `@click`.
const refetchReadings = (): void => {
  void refetchReadingsQuery()
}

const refetchSeries = (): void => {
  void refetchSeriesQuery()
}

const refetchAverages = (): void => {
  void refetchAveragesQuery()
}

const onExport = (fileFormat: ExportFormat): void => {
  const farm = selectedFarm.value
  if (!farm) return
  void exportHistory(fileFormat, farm.id, farm.name, filters.value)
}

useHead(() => ({ title: t('sensors.history.title') }))
</script>

<template>
  <UDashboardPanel id="sensors-history">
    <template #header>
      <UDashboardNavbar
        :title="t('sensors.history.title')"
        icon="i-lucide-history"
      />

      <UDashboardToolbar
        v-if="selectedFarm"
        :ui="{
          root: 'items-end gap-4 py-3 overflow-visible',
          left: 'flex-1 min-w-0',
        }"
      >
        <template #left>
          <SensorsHistoryFilters
            :farm-name="selectedFarm.name"
            :plots="plotList"
            :plots-pending="plotsPending"
            :plot-id="plotId"
            :variables="variableList"
            :variables-pending="variablesPending"
            :variable="variable"
            :range-preset="rangePreset"
            :custom-from="customFrom"
            :custom-to="customTo"
            :range-issue="rangeIssue"
            :has-active-filters="hasActiveFilters"
            @update:plot="setPlot"
            @update:variable="setVariable"
            @update:range-preset="setRangePreset"
            @update:custom-range="setCustomRange"
            @reset="resetFilters"
          />
        </template>

        <template #right>
          <SensorsHistoryExportMenu
            :disabled="!hasResults"
            :is-exporting="isExporting"
            :export-error="exportError"
            @export="onExport"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-6 p-4">
        <div v-if="farmsPending" aria-busy="true" class="flex flex-col gap-4">
          <USkeleton class="h-6 w-72" />
          <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
        </div>

        <p v-else-if="!selectedFarm" class="text-muted">
          {{ t('sensors.history.noFarm') }}
        </p>

        <template v-else>
          <p class="text-sm text-muted">{{ t('sensors.history.subtitle') }}</p>

          <p aria-live="polite" class="sr-only">{{ liveStatus }}</p>

          <!-- Reka renders the tabs root as a div, where aria-label is prohibited. -->
          <section :aria-label="t('sensors.history.view.label')">
            <!-- The panel is a tab stop; Nuxt UI's `focus:outline-none` would hide its focus (2.4.7). -->
            <UTabs
              :items="viewItems"
              :model-value="view"
              :unmount-on-hide="false"
              variant="pill"
              :ui="{
                content:
                  'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-default',
              }"
              @update:model-value="setView"
            >
              <template #chart>
                <div class="pt-4">
                  <template v-if="displayMode === 'plotAverages'">
                    <div
                      v-if="averagesPending"
                      aria-busy="true"
                      class="grid gap-4 sm:grid-cols-2"
                    >
                      <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
                      <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
                    </div>

                    <div
                      v-else-if="averagesError"
                      role="alert"
                      class="flex flex-wrap items-center gap-2 text-sm text-muted"
                    >
                      <span>{{ t('sensors.history.error') }}</span>
                      <UButton
                        variant="link"
                        color="neutral"
                        size="xs"
                        class="p-0"
                        @click="refetchAverages"
                      >
                        {{ t('sensors.history.retry') }}
                      </UButton>
                    </div>

                    <UEmpty
                      v-else-if="averagesList.length === 0"
                      icon="i-lucide-chart-column"
                      :description="t('sensors.history.table.empty')"
                    />

                    <SensorsHistoryAveragesGrid
                      v-else
                      :averages="averagesList"
                      :plots="plotList"
                    />
                  </template>

                  <template v-else>
                    <div
                      v-if="seriesPending"
                      aria-busy="true"
                      class="grid gap-4 sm:grid-cols-2"
                    >
                      <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
                      <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
                    </div>

                    <div
                      v-else-if="seriesError"
                      role="alert"
                      class="flex flex-wrap items-center gap-2 text-sm text-muted"
                    >
                      <span>{{ t('sensors.history.error') }}</span>
                      <UButton
                        variant="link"
                        color="neutral"
                        size="xs"
                        class="p-0"
                        @click="refetchSeries"
                      >
                        {{ t('sensors.history.retry') }}
                      </UButton>
                    </div>

                    <UEmpty
                      v-else-if="seriesList.length === 0"
                      icon="i-lucide-chart-line"
                      :description="t('sensors.history.table.empty')"
                    />

                    <SensorsHistoryChartGrid
                      v-else
                      :series="seriesList"
                      :range-from="filters.date_from"
                      :range-to="filters.date_to"
                    />
                  </template>
                </div>
              </template>

              <template #table>
                <div class="pt-4">
                  <!-- Out-of-range page: the watcher is already bouncing to page 1, so no alert. -->
                  <div
                    v-if="readingsPending || isPageOutOfRange"
                    aria-busy="true"
                    class="flex flex-col gap-2"
                  >
                    <USkeleton class="h-10 w-full" />
                    <USkeleton class="h-64 w-full" />
                  </div>

                  <div
                    v-else-if="readingsError"
                    role="alert"
                    class="flex flex-wrap items-center gap-2 text-sm text-muted"
                  >
                    <span>{{ t('sensors.history.error') }}</span>
                    <UButton
                      variant="link"
                      color="neutral"
                      size="xs"
                      class="p-0"
                      @click="refetchReadings"
                    >
                      {{ t('sensors.history.retry') }}
                    </UButton>
                  </div>

                  <SensorsHistoryTable
                    v-else
                    :farm-name="selectedFarm.name"
                    :readings="readings"
                    :count="readingsCount"
                    :page="page"
                    :pending="readingsPending"
                    :is-placeholder="readingsIsPlaceholder"
                    :show-plot-column="plotId === null"
                    @update:page="setPage"
                  />
                </div>
              </template>
            </UTabs>
          </section>
        </template>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
