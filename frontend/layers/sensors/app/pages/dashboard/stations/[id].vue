<script setup lang="ts">
import {
  CHART_HEIGHT_CLASS,
  HISTORY_PAGE_SIZE,
  VARIABLE_ICONS,
} from '../../../constants/history'
import type { ExportFormat, SensorSemanticKey } from '../../../types/sensors'
import { historyRequestFilters } from '../../../utils/history-filters'
import {
  parseStationId,
  STATION_RANGE_PRESETS,
  type StationRangePreset,
} from '../../../utils/station-filters'
import { isNotFound } from '#api/errors'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const RANGE_LABEL_KEYS: Record<StationRangePreset, string> = {
  '1h': 'sensors.history.range.last1h',
  '6h': 'sensors.history.range.last6h',
  '24h': 'sensors.history.range.last24h',
  '7d': 'sensors.history.range.last7d',
  '30d': 'sensors.history.range.last30d',
}

const { t, te, locale } = useI18n()
const route = useRoute()
const localePath = useLocalePath()
const { selectedFarm, selectFarm } = useSelectedFarm()

const stationId = computed(() => parseStationId(route.params.id))

const {
  data: station,
  isPending,
  isError,
  error,
  refetch: refetchStationQuery,
} = useStationQuery(stationId)

const notFound = computed(
  () => stationId.value === null || (isError.value && isNotFound(error.value)),
)
const stationFailed = computed(
  () => isError.value && station.value === undefined && !notFound.value,
)

// The history requests answer the same 404 as the detail, so they wait for a
// station that exists instead of failing three times over.
const isStationKnown = computed(() => station.value !== undefined)

const { rangePreset, page, filters, isLiveRange, setRangePreset, setPage } =
  useStationFilters()

const {
  data: series,
  isPending: seriesPending,
  isError: seriesError,
  refetch: refetchSeriesQuery,
} = useStationSeriesQuery(stationId, filters, isLiveRange, isStationKnown)

const {
  data: readingsPage,
  isPending: readingsPending,
  isPlaceholderData: readingsIsPlaceholder,
  isError: readingsError,
  error: readingsErrorObject,
  refetch: refetchReadingsQuery,
} = useStationReadingsQuery(
  stationId,
  filters,
  isLiveRange,
  page,
  isStationKnown,
)

const { exportStation, isExporting, exportError } = useHistoryExport()

const now = useNow(30_000)

const seriesList = computed(() => series.value?.series ?? [])
const readings = computed(() => readingsPage.value?.results ?? [])
const readingsCount = computed(() => readingsPage.value?.count ?? 0)
const pageCount = computed(() =>
  Math.max(1, Math.ceil(readingsCount.value / HISTORY_PAGE_SIZE)),
)

// A failed background poll keeps the data already on screen; the error state is
// only for a view that has nothing to show, and the next poll retries anyway.
const seriesFailed = computed(
  () => seriesError.value && series.value === undefined,
)
const readingsFailed = computed(
  () => readingsError.value && readingsPage.value === undefined,
)

// A bookmarked `?page=` can outlive the rows it pointed at: either the count
// says so, or DRF answers the 404 it reserves for a page past the end.
const isPageOutOfRange = computed(() => {
  if (page.value <= 1) return false
  if (isNotFound(readingsErrorObject.value)) return true
  return readingsPage.value !== undefined && page.value > pageCount.value
})

// `immediate`: a shared out-of-range link arrives with the first render.
watch(
  [isPageOutOfRange, pageCount],
  () => {
    if (!isPageOutOfRange.value) return
    setPage(isNotFound(readingsErrorObject.value) ? 1 : pageCount.value)
  },
  { immediate: true },
)

const provider = computed(() => {
  const value = station.value?.provider ?? ''
  const key = `farm.stations.providers.${value}`
  return te(key) ? t(key) : value
})

const dateTimeFormat = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'short',
      timeStyle: 'short',
    }),
)

const numberFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 2 }),
)

const describeTime = (iso: string) => ({
  iso,
  relative: formatRelativeTime(iso, locale.value, now.value),
  absolute: dateTimeFormat.value.format(new Date(iso)),
})

const lastReading = computed(() =>
  station.value?.last_reading_at
    ? describeTime(station.value.last_reading_at)
    : null,
)

const variableIcon = (key: string): string =>
  VARIABLE_ICONS[key as SensorSemanticKey] ?? VARIABLE_ICONS.other

const rangeOptions = computed(() =>
  STATION_RANGE_PRESETS.map((preset) => ({
    value: preset,
    label: t(RANGE_LABEL_KEYS[preset]),
  })),
)

// Announced politely, never focused: a range or page change reports its result
// without pulling the caret off the control the user just used. Refreshed when
// a request the user caused settles — never on a poll changing the count.
const liveStatus = shallowRef('')
watch(
  [rangePreset, page, locale, readingsPending, readingsIsPlaceholder],
  () => {
    if (
      readingsPending.value ||
      readingsIsPlaceholder.value ||
      readingsFailed.value
    ) {
      liveStatus.value = ''
      return
    }
    liveStatus.value = t(
      'sensors.history.status.table',
      {
        count: new Intl.NumberFormat(locale.value).format(readingsCount.value),
        page: page.value,
        pages: pageCount.value,
      },
      readingsCount.value,
    )
  },
)

const title = computed(() => {
  if (station.value) return station.value.name
  if (notFound.value) return t('sensors.stations.detail.notFound')
  return t('sensors.stations.detail.loading')
})

const backTo = computed(() => localePath('/dashboard/stations'))

const refetchStation = (): void => {
  void refetchStationQuery()
}
const refetchSeries = (): void => {
  void refetchSeriesQuery()
}
const refetchReadings = (): void => {
  void refetchReadingsQuery()
}

const onExport = (fileFormat: ExportFormat): void => {
  const value = station.value
  if (!value) return
  void exportStation(
    fileFormat,
    value.id,
    value.name,
    historyRequestFilters(filters.value, isLiveRange.value, Date.now()),
  )
}

// A direct load of a station of another of the farmer's farms must leave the
// sidebar switcher coherent with what the page shows.
watch(station, (value) => {
  if (value && value.farm_id !== selectedFarm.value?.id) {
    selectFarm(value.farm_id)
  }
})

useHead(() => ({ title: title.value }))
</script>

<template>
  <UDashboardPanel id="sensors-station">
    <template #header>
      <!-- The navbar title is the page's only <h1>, so it names the station. -->
      <UDashboardNavbar :title="title" icon="i-lucide-cloud-sun" />

      <UDashboardToolbar
        v-if="station"
        :ui="{ root: 'flex-wrap items-end gap-4 py-3 overflow-visible' }"
      >
        <template #left>
          <!-- Neutral, not primary: white text on the light-mode primary is 2.2:1 (1.4.3). -->
          <div
            role="group"
            :aria-label="t('sensors.stations.detail.range')"
            class="flex flex-wrap gap-2"
          >
            <UButton
              v-for="option in rangeOptions"
              :key="option.value"
              :label="option.label"
              :aria-pressed="rangePreset === option.value"
              color="neutral"
              :variant="rangePreset === option.value ? 'solid' : 'outline'"
              size="sm"
              class="min-h-8"
              @click="setRangePreset(option.value)"
            />
          </div>
        </template>

        <template #right>
          <SensorsHistoryExportMenu
            :disabled="readingsCount === 0"
            :is-exporting="isExporting"
            :export-error="exportError"
            @export="onExport"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-6 p-4">
        <ULink
          :to="backTo"
          class="inline-flex items-center gap-1 min-h-8 w-fit"
        >
          <UIcon name="i-lucide-arrow-left" aria-hidden="true" />
          {{ t('sensors.stations.detail.back') }}
        </ULink>

        <div
          v-if="isPending && !notFound"
          aria-busy="true"
          class="flex flex-col gap-3"
        >
          <USkeleton class="h-28 w-full" />
          <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
        </div>

        <UEmpty
          v-else-if="notFound"
          icon="i-lucide-cloud-off"
          :title="t('sensors.stations.detail.notFound')"
          :description="t('sensors.stations.detail.notFoundBody')"
          :actions="[
            {
              label: t('sensors.stations.detail.backToList'),
              icon: 'i-lucide-arrow-left',
              to: backTo,
              color: 'neutral',
              variant: 'outline',
            },
          ]"
        />

        <div
          v-else-if="stationFailed"
          role="alert"
          class="flex flex-wrap items-center gap-2 text-sm text-muted"
        >
          <span>{{ t('sensors.stations.detail.error') }}</span>
          <UButton
            variant="link"
            color="neutral"
            size="xs"
            class="p-0"
            @click="refetchStation"
          >
            {{ t('sensors.stations.retry') }}
          </UButton>
        </div>

        <template v-else-if="station">
          <UCard variant="subtle" :ui="{ body: 'flex flex-col gap-2' }">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="flex min-w-0 flex-col gap-1">
                <p class="text-2xl font-semibold text-highlighted">
                  {{ station.name }}
                </p>
                <p class="text-sm text-muted">
                  {{ t('sensors.stations.detail.provider', { provider }) }}
                </p>
              </div>
              <StationStatusBadge :status="station.status" size="lg" />
            </div>
            <p class="text-sm text-muted">
              <template v-if="lastReading">
                {{ t('farm.stations.lastReading') }}
                <time
                  :datetime="lastReading.iso"
                  :title="lastReading.absolute"
                  >{{ lastReading.relative }}</time
                >
              </template>
              <template v-else>{{ t('farm.stations.neverReported') }}</template>
            </p>
          </UCard>

          <section
            :aria-label="t('sensors.stations.detail.conditions')"
            class="flex flex-col gap-3"
          >
            <h2 class="text-lg font-semibold text-highlighted">
              {{ t('sensors.stations.detail.conditions') }}
            </h2>
            <p v-if="station.latest.length === 0" class="text-muted">
              {{ t('farm.stations.noReadings') }}
            </p>
            <ul v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <li v-for="reading in station.latest" :key="reading.variable_id">
                <UCard variant="subtle" :ui="{ body: 'flex flex-col gap-2' }">
                  <div class="flex items-center gap-2 min-w-0">
                    <span
                      class="inline-flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"
                      aria-hidden="true"
                    >
                      <UIcon
                        :name="variableIcon(reading.semantic_key)"
                        class="size-4"
                      />
                    </span>
                    <h3 class="truncate text-sm font-medium text-muted">
                      {{ reading.name }}
                    </h3>
                  </div>
                  <p
                    class="text-2xl font-semibold text-highlighted tabular-nums"
                  >
                    {{ numberFormat.format(reading.value) }}
                    <span class="text-base font-normal text-muted">{{
                      reading.unit
                    }}</span>
                  </p>
                  <p class="text-xs text-muted">
                    <time
                      :datetime="reading.recorded_at"
                      :title="describeTime(reading.recorded_at).absolute"
                      >{{ describeTime(reading.recorded_at).relative }}</time
                    >
                  </p>
                </UCard>
              </li>
            </ul>
          </section>

          <section
            :aria-label="t('sensors.stations.detail.charts')"
            class="flex flex-col gap-3"
          >
            <h2 class="text-lg font-semibold text-highlighted">
              {{ t('sensors.stations.detail.charts') }}
            </h2>

            <div
              v-if="seriesPending"
              aria-busy="true"
              class="grid gap-4 sm:grid-cols-2"
            >
              <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
              <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
            </div>

            <div
              v-else-if="seriesFailed"
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
                {{ t('sensors.stations.retry') }}
              </UButton>
            </div>

            <UEmpty
              v-else-if="seriesList.length === 0"
              icon="i-lucide-chart-line"
              :description="t('sensors.stations.detail.noData')"
            />

            <SensorsHistoryChartGrid
              v-else
              :series="seriesList"
              :range-from="series?.date_from ?? filters.date_from"
              :range-to="series?.date_to ?? filters.date_to"
              :alternative="t('sensors.stations.detail.chartsAlternative')"
            />
          </section>

          <section
            :aria-label="t('sensors.stations.detail.readings')"
            class="flex flex-col gap-3"
          >
            <h2 class="text-lg font-semibold text-highlighted">
              {{ t('sensors.stations.detail.readings') }}
            </h2>

            <p aria-live="polite" class="sr-only">{{ liveStatus }}</p>

            <!-- Out-of-range page: the watcher is already bouncing back, so no alert. -->
            <div
              v-if="readingsPending || isPageOutOfRange"
              aria-busy="true"
              class="flex flex-col gap-2"
            >
              <USkeleton class="h-10 w-full" />
              <USkeleton class="h-64 w-full" />
            </div>

            <div
              v-else-if="readingsFailed"
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
                {{ t('sensors.stations.retry') }}
              </UButton>
            </div>

            <SensorsHistoryTable
              v-else
              :subject="station.name"
              :readings="readings"
              :count="readingsCount"
              :page="page"
              :pending="readingsPending"
              :is-placeholder="readingsIsPlaceholder"
              :show-plot-column="false"
              :show-sensor-column="false"
              @update:page="setPage"
            />
          </section>
        </template>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
