<script setup lang="ts">
definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()

const { selectedFarm, isPending: farmsPending } = useSelectedFarm()
const farmId = computed(() => selectedFarm.value?.id ?? null)

const {
  data: stations,
  isPending,
  isError,
  refetch,
} = useFarmStationsQuery(farmId)

// Ages are shown in minutes, so a finer tick would only re-render for nothing.
const now = useNow(30_000)

const stationList = computed(() => stations.value ?? [])

// A failed background poll keeps the list already on screen; the error state is
// only for a page that has nothing to show, and the next poll retries anyway.
const loadFailed = computed(() => isError.value && stations.value === undefined)

const retry = (): void => {
  void refetch()
}

useHead(() => ({ title: t('sensors.stations.title') }))
</script>

<template>
  <UDashboardPanel id="sensors-stations">
    <template #header>
      <UDashboardNavbar
        :title="t('sensors.stations.title')"
        icon="i-lucide-cloud-sun"
      />
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-6 p-4">
        <div v-if="farmsPending" aria-busy="true" class="flex flex-col gap-4">
          <USkeleton class="h-6 w-72" />
          <USkeleton class="h-64 w-full" />
        </div>

        <p v-else-if="!selectedFarm" class="text-muted">
          {{ t('sensors.stations.noFarm') }}
        </p>

        <template v-else>
          <p class="text-sm text-muted">
            {{ t('sensors.stations.subtitle', { farm: selectedFarm.name }) }}
          </p>

          <div
            v-if="isPending"
            aria-busy="true"
            class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
          >
            <USkeleton class="h-64 w-full" />
            <USkeleton class="h-64 w-full" />
          </div>

          <div
            v-else-if="loadFailed"
            role="alert"
            class="flex flex-col items-center gap-3 text-center"
          >
            <p class="text-default">{{ t('sensors.stations.error') }}</p>
            <UButton
              variant="outline"
              color="neutral"
              icon="i-lucide-refresh-cw"
              @click="retry"
            >
              {{ t('sensors.stations.retry') }}
            </UButton>
          </div>

          <UEmpty
            v-else-if="stationList.length === 0"
            icon="i-lucide-cloud-off"
            :description="t('sensors.stations.empty')"
          />

          <div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <StationCard
              v-for="station in stationList"
              :key="station.id"
              :station="station"
              :now="now"
              heading-tag="h2"
            />
          </div>
        </template>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
