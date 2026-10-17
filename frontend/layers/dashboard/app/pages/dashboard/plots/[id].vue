<script setup lang="ts">
import { pointsWithinHours, toSeriesPoints } from '../../../utils/plot-series'
import { isNotFound } from '#api/errors'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()
const route = useRoute()
const localePath = useLocalePath()
const { selectedFarm, selectFarm } = useSelectedFarm()

// A non-numeric id resolves to null, which keeps the query disabled and renders
// the not-found state without a request.
const plotId = computed(() => {
  const parsed = Number(route.params.id)
  return Number.isInteger(parsed) ? parsed : null
})

const {
  data: plot,
  isPending,
  isError,
  error,
  refetch: refetchPlotQuery,
} = usePlotQuery(plotId)

const {
  data: overview,
  isPending: overviewPending,
  isError: overviewError,
  refetch: refetchOverviewQuery,
} = usePlotOverviewQuery(plotId)

// A failed background poll keeps the data already on screen; the error state is
// only for a page that has nothing to show, and the next poll retries anyway.
const overviewFailed = computed(
  () => overviewError.value && overview.value === undefined,
)

// One clock drives every "hace 5 min" and the stale-data badge, so they agree.
const now = useNow(60_000)

const sparklineByKey = computed(() =>
  Object.fromEntries(
    (overview.value?.series ?? []).map((series) => [
      series.semantic_key,
      pointsWithinHours(toSeriesPoints(series), 24, now.value),
    ]),
  ),
)

const plotNotFound = computed(
  () => plotId.value === null || (isError.value && isNotFound(error.value)),
)

const title = computed(() =>
  plot.value
    ? t('dashboard.plotDetail.title', { name: plot.value.name })
    : t('dashboard.plotDetail.notFound'),
)

const backTo = computed(() => localePath('/dashboard'))

const refetchPlot = (): void => {
  void refetchPlotQuery()
}
const refetchOverview = (): void => {
  void refetchOverviewQuery()
}

// A direct load of a plot belonging to another of the farmer's farms must leave
// the sidebar switcher coherent with what the page shows.
watch(plot, (value) => {
  if (value && value.farm.id !== selectedFarm.value?.id) {
    selectFarm(value.farm.id)
  }
})

useHead(() => ({ title: title.value }))
</script>

<template>
  <UDashboardPanel id="plot-detail">
    <template #header>
      <!-- The navbar title is the page's only <h1>, so it has to name the
           plot rather than repeat the section name. -->
      <UDashboardNavbar :title="title" icon="i-lucide-map" />
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-6 p-4">
        <ULink
          :to="backTo"
          class="inline-flex items-center gap-1 min-h-8 w-fit"
        >
          <UIcon name="i-lucide-arrow-left" />
          {{ t('dashboard.plotDetail.back') }}
        </ULink>

        <div
          v-if="isPending && !plotNotFound"
          aria-busy="true"
          class="flex flex-col gap-3"
        >
          <USkeleton class="h-8 w-64" />
          <USkeleton class="h-64 w-full" />
        </div>

        <p v-else-if="plotNotFound" class="text-muted">
          {{ t('dashboard.plotDetail.notFoundBody') }}
        </p>

        <div
          v-else-if="isError"
          role="alert"
          class="flex flex-wrap items-center gap-2 text-sm text-muted"
        >
          <span>{{ t('dashboard.plotDetail.error') }}</span>
          <UButton
            variant="link"
            color="neutral"
            size="xs"
            class="p-0"
            @click="refetchPlot"
          >
            {{ t('dashboard.retry') }}
          </UButton>
        </div>

        <template v-else-if="plot">
          <PlotHero :plot="plot" :overview="overview" :now="now" />

          <div
            v-if="overviewPending"
            aria-busy="true"
            class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            <USkeleton v-for="index in 4" :key="index" class="h-48 w-full" />
          </div>

          <div
            v-else-if="overviewFailed"
            role="alert"
            class="flex flex-wrap items-center gap-2 text-sm text-muted"
          >
            <span>{{ t('dashboard.plotDetail.overviewError') }}</span>
            <UButton
              variant="link"
              color="neutral"
              size="xs"
              class="p-0"
              @click="refetchOverview"
            >
              {{ t('dashboard.retry') }}
            </UButton>
          </div>

          <template v-else-if="overview">
            <section
              :aria-label="t('dashboard.plotDetail.conditions.title')"
              class="flex flex-col gap-3"
            >
              <h2 class="text-lg font-semibold text-highlighted">
                {{ t('dashboard.plotDetail.conditions.title') }}
              </h2>
              <p v-if="overview.conditions.length === 0" class="text-muted">
                {{ t('dashboard.plotDetail.conditions.empty') }}
              </p>
              <div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <PlotConditionCard
                  v-for="condition in overview.conditions"
                  :key="condition.semantic_key"
                  :condition="condition"
                  :points="sparklineByKey[condition.semantic_key] ?? []"
                  :now="now"
                />
              </div>
            </section>

            <template v-if="overview.series.length > 0">
              <PlotTrend :series="overview.series" :now="now" />
              <PlotHeatmap :series="overview.series" :now="now" />
            </template>

            <div class="grid gap-4 lg:grid-cols-2">
              <PlotIrrigationCard
                :irrigation="overview.irrigation"
                :plot-id="plot.id"
                :now="now"
              />
              <PlotSensorsCard :sensors="overview.sensors" :now="now" />
            </div>
          </template>
        </template>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
