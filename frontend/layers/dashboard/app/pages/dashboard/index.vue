<script setup lang="ts">
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

const plotCount = computed(() => plots.value?.length ?? 0)

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
      <UContainer class="flex flex-col gap-4 p-4">
        <p class="text-muted">
          {{ t('dashboard.index.welcome') }}
        </p>

        <UPageCard
          :title="selectedFarm?.name ?? t('farm.plots.title')"
          icon="i-lucide-map"
        >
          <div
            v-if="farmsPending || (selectedFarm && plotsPending)"
            aria-busy="true"
          >
            <USkeleton class="h-7 w-24" />
          </div>

          <p v-else-if="!selectedFarm" class="text-muted">
            {{ t('farm.plots.noFarm') }}
          </p>

          <div
            v-else-if="plotsError"
            class="flex items-center gap-2 text-sm text-muted"
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

          <p v-else-if="plotCount === 0" class="text-muted">
            {{ t('farm.plots.none') }}
          </p>

          <p v-else class="text-2xl font-semibold">
            {{ t('farm.plots.count', plotCount) }}
          </p>
        </UPageCard>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
