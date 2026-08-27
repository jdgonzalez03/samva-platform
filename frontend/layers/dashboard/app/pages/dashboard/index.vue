<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import {
  DEFAULT_BASEMAP,
  MAP_HEIGHT_CLASS,
  type BasemapId,
} from '../../constants/map'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()
const { selectedFarm, isPending: farmsPending } = useSelectedFarm()
const { mode, setMode } = useDashboardViewMode()

const farmId = computed(() => selectedFarm.value?.id ?? null)

const {
  data: plots,
  isPending: plotsPending,
  isError: plotsError,
  refetch: refetchPlotsQuery,
} = useFarmPlotsQuery(farmId)

const {
  data: weather,
  isPending: weatherPending,
  isError: weatherError,
  refetch: refetchWeatherQuery,
} = useFarmWeatherQuery(farmId)

const basemap = ref<BasemapId>(DEFAULT_BASEMAP)
const mapAlternativeId = useId()

const plotList = computed(() => plots.value ?? [])
const plotCount = computed(() => plotList.value.length)
// Both counts come from the plots response — the dashboard makes no extra request.
const sensorCount = computed(() =>
  plotList.value.reduce((total, plot) => total + plot.sensor_count, 0),
)
const unmappedPlots = computed(() => getUnmappedPlots(plotList.value))
const canDrawMap = computed(
  () =>
    !!selectedFarm.value && hasMapTarget(selectedFarm.value, plotList.value),
)

const viewItems = computed<TabsItem[]>(() => [
  {
    label: t('dashboard.view.map'),
    icon: 'i-lucide-map',
    value: 'map',
    slot: 'map' as const,
  },
  {
    label: t('dashboard.view.list'),
    icon: 'i-lucide-list',
    value: 'list',
    slot: 'list' as const,
  },
])

const refetchPlots = (): void => {
  void refetchPlotsQuery()
}

const refetchWeather = (): void => {
  void refetchWeatherQuery()
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
          <USkeleton class="h-24 w-full" />
          <USkeleton :class="MAP_HEIGHT_CLASS" class="w-full" />
        </div>

        <p v-else-if="!selectedFarm" class="text-muted">
          {{ t('farm.plots.noFarm') }}
        </p>

        <template v-else>
          <DashboardFarmStatCards
            :plot-count="plotCount"
            :sensor-count="sensorCount"
            :counts-pending="plotsPending"
            :counts-error="plotsError"
            :weather="weather"
            :weather-pending="weatherPending"
            :weather-error="weatherError"
            @retry-weather="refetchWeather"
          />

          <h2 class="text-lg font-semibold text-highlighted">
            {{ selectedFarm.name }}
          </h2>

          <div v-if="plotsPending" aria-busy="true">
            <USkeleton :class="MAP_HEIGHT_CLASS" class="w-full" />
          </div>

          <div
            v-else-if="plotsError"
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

          <!-- Named grouping rather than an aria-label on the tabs root, which
               Reka renders as a plain div where the attribute is prohibited. -->
          <section v-else :aria-label="t('dashboard.view.label')">
            <!-- Reka makes the panel itself a tab stop; Nuxt UI's default
                 content class is `focus:outline-none`, which would leave that
                 stop with no visible focus (2.4.7). The indicator is a ring
                 rather than an outline because that default would win over any
                 outline this adds. -->
            <UTabs
              :items="viewItems"
              :model-value="mode"
              :unmount-on-hide="false"
              variant="pill"
              :ui="{
                content:
                  'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-default',
              }"
              @update:model-value="setMode"
            >
              <template #map>
                <div class="flex flex-col gap-3 pt-4">
                  <UEmpty
                    v-if="plotCount === 0"
                    icon="i-lucide-map"
                    :description="t('farm.plots.none')"
                  />

                  <template v-else>
                    <DashboardBasemapSelector v-model="basemap" />

                    <UEmpty
                      v-if="!canDrawMap"
                      icon="i-lucide-map-pin-off"
                      :description="t('dashboard.map.noLocation')"
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
                  </template>
                </div>
              </template>

              <template #list>
                <div class="pt-4">
                  <UEmpty
                    v-if="plotCount === 0"
                    icon="i-lucide-list"
                    :description="t('farm.plots.none')"
                  />
                  <DashboardPlotsList v-else :plots="plotList" />
                </div>
              </template>
            </UTabs>
          </section>
        </template>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
