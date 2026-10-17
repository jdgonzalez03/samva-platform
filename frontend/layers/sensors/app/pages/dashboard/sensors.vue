<script setup lang="ts">
import { DEVICES_TICK_MS } from '../../constants/devices'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()
const localePath = useLocalePath()

const { selectedFarm, isPending: farmsPending } = useSelectedFarm()
const farmId = computed(() => selectedFarm.value?.id ?? null)

const {
  data: sensors,
  isPending,
  isError,
  refetch,
} = useFarmSensorsQuery(farmId)

const now = useNow(DEVICES_TICK_MS)

const sensorList = computed(() => sensors.value ?? [])

// A failed background poll keeps the list already on screen; the error state is
// only for a page that has nothing to show, and the next poll retries anyway.
const loadFailed = computed(() => isError.value && sensors.value === undefined)

const retry = (): void => {
  void refetch()
}

useHead(() => ({ title: t('sensors.devices.title') }))
</script>

<template>
  <UDashboardPanel id="sensors-devices">
    <template #header>
      <UDashboardNavbar
        :title="t('sensors.devices.title')"
        icon="i-lucide-radio-tower"
      />
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-6 p-4">
        <div v-if="farmsPending" aria-busy="true" class="flex flex-col gap-4">
          <USkeleton class="h-6 w-72" />
          <USkeleton class="h-64 w-full" />
        </div>

        <p v-else-if="!selectedFarm" class="text-muted">
          {{ t('sensors.devices.noFarm') }}
        </p>

        <template v-else>
          <i18n-t
            keypath="sensors.devices.subtitle"
            tag="p"
            class="text-sm text-muted"
            scope="global"
          >
            <template #profile>
              <ULink
                :to="localePath('/dashboard/profile')"
                class="text-primary underline"
                >{{ t('sensors.devices.profileLink') }}</ULink
              >
            </template>
          </i18n-t>

          <div v-if="isPending" aria-busy="true" class="flex flex-col gap-2">
            <USkeleton class="h-10 w-full" />
            <USkeleton class="h-48 w-full" />
          </div>

          <div
            v-else-if="loadFailed"
            class="flex flex-col items-center gap-3 text-center"
          >
            <p class="text-default">{{ t('sensors.devices.error') }}</p>
            <UButton
              variant="outline"
              color="neutral"
              icon="i-lucide-refresh-cw"
              @click="retry"
            >
              {{ t('sensors.devices.retry') }}
            </UButton>
          </div>

          <UEmpty
            v-else-if="sensorList.length === 0"
            icon="i-lucide-radio-tower"
            :description="t('sensors.devices.empty')"
          />

          <SensorsDeviceTable
            v-else
            :farm-name="selectedFarm.name"
            :sensors="sensorList"
            :now="now"
          />
        </template>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
