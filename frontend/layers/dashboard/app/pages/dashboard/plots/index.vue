<script setup lang="ts">
import type { LocationQueryRaw } from 'vue-router'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const { data, isPending, isError, refetch } = usePlotSummariesQuery()
const now = useNow(60_000)

// A failed background poll keeps the data already on screen; the error state is
// only for a page that has nothing to show, and the next poll retries anyway.
const loadFailed = computed(() => isError.value && data.value === undefined)

const ALL_FARMS = 'all'

const plots = computed(() => data.value ?? [])

const farms = computed(() => {
  const byId = new Map(plots.value.map((plot) => [plot.farm.id, plot.farm]))
  return [...byId.values()]
})

// Filters live in the URL so a reload or a shared link keeps them. A `?farm=`
// only counts once the plot list confirms the user owns it.
const farmFilter = computed(() => {
  const requested = Number(route.query.farm)
  return farms.value.some((farm) => farm.id === requested) ? requested : null
})
const search = computed(() =>
  typeof route.query.q === 'string' ? route.query.q : '',
)

const updateQuery = (patch: Record<string, string | undefined>): void => {
  const query = Object.fromEntries(
    Object.entries({ ...route.query, ...patch }).filter(
      ([, value]) => value !== undefined && value !== '',
    ),
  ) as LocationQueryRaw
  void router.replace({ query })
}

const farmItems = computed(() => [
  { label: t('dashboard.plotsIndex.allFarms'), value: ALL_FARMS },
  ...farms.value.map((farm) => ({ label: farm.name, value: String(farm.id) })),
])
const farmValue = computed(() =>
  farmFilter.value === null ? ALL_FARMS : String(farmFilter.value),
)
const setFarm = (value: string | number): void => {
  updateQuery({ farm: value === ALL_FARMS ? undefined : String(value) })
}
const setSearch = (value: string | number): void => {
  updateQuery({ q: String(value) })
}
const clearFilters = (): void => {
  updateQuery({ farm: undefined, q: undefined })
}

const visiblePlots = computed(() => {
  const needle = search.value.trim().toLocaleLowerCase()
  return plots.value.filter(
    (plot) =>
      (farmFilter.value === null || plot.farm.id === farmFilter.value) &&
      (!needle || plot.name.toLocaleLowerCase().includes(needle)),
  )
})

const subtitle = computed(() =>
  t('dashboard.plotsIndex.subtitle', {
    plots: t('dashboard.plotsIndex.plotsCount', plots.value.length, {
      named: { count: plots.value.length },
    }),
    farms: t('dashboard.plotsIndex.farmsCount', farms.value.length, {
      named: { count: farms.value.length },
    }),
  }),
)

const retry = (): void => {
  void refetch()
}

useHead(() => ({ title: t('dashboard.plotsIndex.title') }))
</script>

<template>
  <UDashboardPanel id="plots-index">
    <template #header>
      <UDashboardNavbar
        :title="t('dashboard.plotsIndex.title')"
        icon="i-lucide-land-plot"
      />

      <UDashboardToolbar
        v-if="plots.length > 0"
        :ui="{ root: 'items-end gap-4 py-3 overflow-visible' }"
      >
        <template #left>
          <div class="flex flex-wrap items-end gap-3">
            <UInput
              :model-value="search"
              icon="i-lucide-search"
              :placeholder="t('dashboard.plotsIndex.search')"
              :aria-label="t('dashboard.plotsIndex.search')"
              class="w-56"
              @update:model-value="setSearch"
            />
            <USelect
              :model-value="farmValue"
              :items="farmItems"
              icon="i-lucide-tractor"
              :aria-label="t('dashboard.plotsIndex.farm')"
              class="w-52"
              @update:model-value="setFarm"
            />
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-6 p-4">
        <div
          v-if="isPending"
          aria-busy="true"
          class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
        >
          <USkeleton v-for="index in 6" :key="index" class="h-72 w-full" />
        </div>

        <div
          v-else-if="loadFailed"
          role="alert"
          class="flex flex-wrap items-center gap-2 text-sm text-muted"
        >
          <span>{{ t('dashboard.plotsIndex.error') }}</span>
          <UButton
            variant="link"
            color="neutral"
            size="xs"
            class="p-0"
            @click="retry"
          >
            {{ t('dashboard.retry') }}
          </UButton>
        </div>

        <UEmpty
          v-else-if="plots.length === 0"
          icon="i-lucide-land-plot"
          :description="t('dashboard.plotsIndex.empty')"
        />

        <template v-else>
          <p class="text-sm text-muted">{{ subtitle }}</p>

          <UEmpty
            v-if="visiblePlots.length === 0"
            icon="i-lucide-search-x"
            :description="t('dashboard.plotsIndex.noMatches')"
            :actions="[
              {
                label: t('dashboard.plotsIndex.clearFilters'),
                icon: 'i-lucide-x',
                variant: 'outline',
                onClick: clearFilters,
              },
            ]"
          />

          <UPageGrid v-else class="sm:grid-cols-2 xl:grid-cols-3">
            <PlotSummaryCard
              v-for="plot in visiblePlots"
              :key="plot.id"
              :plot="plot"
              :now="now"
            />
          </UPageGrid>
        </template>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
