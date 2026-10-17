<script setup lang="ts">
import {
  DEFAULT_BASEMAP,
  MAP_HEIGHT_CLASS,
  type BasemapId,
} from '../../constants/map'
import { buildAlerts, plotColors } from '../../utils/farm-overview'
import { pointsWithinHours, toSeriesPoints } from '../../utils/plot-series'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()
const localePath = useLocalePath()
const { selectedFarm, isPending: farmsPending } = useSelectedFarm()

const farmId = computed(() => selectedFarm.value?.id ?? null)

const {
  data: plots,
  isPending: plotsPending,
  isError: plotsError,
  refetch: refetchPlotsQuery,
} = useFarmPlotsQuery(farmId)

const {
  data: overview,
  isPending: overviewPending,
  isError: overviewError,
  refetch: refetchOverviewQuery,
} = useFarmOverviewQuery(farmId)

const {
  data: stations,
  isPending: stationsPending,
  isError: stationsError,
  refetch: refetchStationsQuery,
} = useFarmStationsQuery(farmId)

// A failed background poll keeps the data already on screen; the error state is
// only for a page that has nothing to show, and the next poll retries anyway.
const overviewFailed = computed(
  () => overviewError.value && overview.value === undefined,
)
const stationsFailed = computed(
  () => stationsError.value && stations.value === undefined,
)

// One clock drives every relative time and freshness threshold on the page.
const now = useNow(60_000)

const basemap = ref<BasemapId>(DEFAULT_BASEMAP)
const mapAlternativeId = useId()
const stationsHeadingId = useId()

const plotList = computed(() => plots.value ?? [])
const unmappedPlots = computed(() => getUnmappedPlots(plotList.value))
const canDrawMap = computed(
  () =>
    !!selectedFarm.value && hasMapTarget(selectedFarm.value, plotList.value),
)
const colors = computed(() => plotColors(plotList.value))

const alerts = computed(() =>
  overview.value ? buildAlerts(overview.value, now.value) : null,
)

const sparklineByKey = computed(() =>
  Object.fromEntries(
    (overview.value?.series ?? []).map((series) => [
      series.semantic_key,
      pointsWithinHours(toSeriesPoints(series), 24, now.value),
    ]),
  ),
)

const refetchPlots = (): void => {
  void refetchPlotsQuery()
}
const refetchOverview = (): void => {
  void refetchOverviewQuery()
}
const refetchStations = (): void => {
  void refetchStationsQuery()
}

useHead(() => ({ title: t('dashboard.index.title') }))
</script>

<template>
  <UDashboardPanel id="home-dashboard">
    <template #header>
      <UDashboardNavbar
        :title="t('dashboard.index.title')"
        icon="i-lucide-house"
      />
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-6 p-4">
        <div v-if="farmsPending" aria-busy="true" class="flex flex-col gap-6">
          <USkeleton class="h-32 w-full" />
          <USkeleton class="h-24 w-full" />
          <USkeleton :class="MAP_HEIGHT_CLASS" class="w-full" />
        </div>

        <p v-else-if="!selectedFarm" class="text-muted">
          {{ t('farm.plots.noFarm') }}
        </p>

        <template v-else>
          <HomeGreeting :farm-name="selectedFarm.name" :now="now" />

          <div
            v-if="plotsError"
            role="alert"
            class="flex flex-wrap items-center gap-2 text-sm text-muted"
          >
            <span>{{ t('farm.plots.error') }}</span>
            <UButton
              variant="link"
              color="neutral"
              size="xs"
              class="p-0"
              @click="refetchPlots"
            >
              {{ t('farm.plots.retry') }}
            </UButton>
          </div>

          <HomeStats
            :plots="plotList"
            :plots-pending="plotsPending"
            :plots-error="plotsError"
            :overview="overview"
            :alert-count="alerts ? alerts.length : null"
          />

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
              :aria-label="t('dashboard.home.conditions.title')"
              class="flex flex-col gap-3"
            >
              <div>
                <h2 class="text-lg font-semibold text-highlighted">
                  {{ t('dashboard.home.conditions.title') }}
                </h2>
                <p class="text-sm text-muted">
                  {{ t('dashboard.home.conditions.subtitle') }}
                </p>
              </div>
              <p v-if="overview.conditions.length === 0" class="text-muted">
                {{ t('dashboard.home.conditions.empty') }}
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

            <div class="grid gap-4 lg:grid-cols-3">
              <HomeAttention :alerts="alerts ?? []" :now="now" />
              <div class="lg:col-span-2">
                <HomeComparison
                  :overview="overview"
                  :colors="colors"
                  :now="now"
                />
              </div>
            </div>
          </template>

          <div class="grid gap-4 xl:grid-cols-5">
            <UCard
              variant="subtle"
              class="xl:col-span-3"
              :ui="{ body: 'flex flex-col gap-3' }"
            >
              <template #header>
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <h2
                    class="flex items-center gap-2 font-semibold text-highlighted"
                  >
                    <UIcon
                      name="i-lucide-map"
                      class="text-primary"
                      aria-hidden="true"
                    />
                    {{ selectedFarm.name }}
                  </h2>
                  <DashboardBasemapSelector
                    v-if="plotList.length > 0"
                    v-model="basemap"
                  />
                </div>
              </template>

              <div v-if="plotsPending" aria-busy="true">
                <USkeleton :class="MAP_HEIGHT_CLASS" class="w-full" />
              </div>

              <UEmpty
                v-else-if="plotList.length === 0"
                icon="i-lucide-map"
                :description="t('farm.plots.none')"
                variant="naked"
              />

              <UEmpty
                v-else-if="!canDrawMap"
                icon="i-lucide-map-pin-off"
                :description="t('dashboard.map.noLocation')"
                variant="naked"
              />

              <section
                v-else
                role="region"
                :aria-label="
                  t('dashboard.map.region', { name: selectedFarm.name })
                "
                :aria-describedby="mapAlternativeId"
                class="flex flex-col gap-2"
              >
                <ClientOnly>
                  <LazyDashboardPlotsMap
                    :farm="selectedFarm"
                    :plots="plotList"
                    :basemap="basemap"
                  />
                  <template #fallback>
                    <div
                      :class="MAP_HEIGHT_CLASS"
                      role="status"
                      aria-busy="true"
                      class="w-full"
                    >
                      <USkeleton class="size-full" />
                      <span class="sr-only">
                        {{ t('dashboard.map.loading') }}
                      </span>
                    </div>
                  </template>
                </ClientOnly>

                <p :id="mapAlternativeId" class="text-sm text-muted">
                  {{ t('dashboard.map.alternative') }}
                </p>
              </section>

              <DashboardUnmappedPlotsNote
                v-if="unmappedPlots.length"
                :plots="unmappedPlots"
              />
            </UCard>

            <div class="xl:col-span-2">
              <HomeRanking
                v-if="overview"
                :overview="overview"
                :colors="colors"
                :now="now"
              />
            </div>
          </div>

          <template v-if="overview">
            <HomePlotsHeatmap :overview="overview" :now="now" />

            <div class="grid gap-4 lg:grid-cols-3">
              <div class="lg:col-span-2">
                <HomeIrrigation :overview="overview" :colors="colors" />
              </div>
              <HomeSensors :overview="overview" />
            </div>

            <HomeClimate :overview="overview" />
          </template>

          <section
            :aria-labelledby="stationsHeadingId"
            class="flex flex-col gap-3"
          >
            <div class="flex flex-wrap items-center justify-between gap-3">
              <h2
                :id="stationsHeadingId"
                class="flex items-center gap-2 text-lg font-semibold text-highlighted"
              >
                <UIcon
                  name="i-lucide-cloud-sun"
                  class="text-primary"
                  aria-hidden="true"
                />
                {{ t('dashboard.home.stations.title') }}
              </h2>
              <UButton
                v-if="stations && stations.length > 0"
                :to="localePath('/dashboard/stations')"
                :label="t('dashboard.home.stations.viewAll')"
                trailing-icon="i-lucide-arrow-right"
                color="neutral"
                variant="link"
              />
            </div>

            <div
              v-if="stationsPending"
              aria-busy="true"
              class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
            >
              <USkeleton class="h-64 w-full" />
              <USkeleton class="h-64 w-full" />
            </div>

            <div
              v-else-if="stationsFailed"
              role="alert"
              class="flex flex-wrap items-center gap-2 text-sm text-muted"
            >
              <span>{{ t('dashboard.home.stations.error') }}</span>
              <UButton
                variant="link"
                color="neutral"
                size="xs"
                class="p-0"
                @click="refetchStations"
              >
                {{ t('dashboard.retry') }}
              </UButton>
            </div>

            <UEmpty
              v-else-if="!stations || stations.length === 0"
              icon="i-lucide-cloud-off"
              :description="t('dashboard.home.stations.empty')"
              variant="naked"
            />

            <div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <StationCard
                v-for="station in stations"
                :key="station.id"
                :station="station"
                :now="now"
              />
            </div>
          </section>
        </template>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
