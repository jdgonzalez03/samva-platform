<script setup lang="ts">
definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

import { mockFarms } from '../../utils/dashboard/mock'
import type { TabsItem } from '@nuxt/ui'


const selectedFarm = useState('selected-farm', () => mockFarms[0])

const viewModesForMyFarm = ref<TabsItem[]>([
  { label: 'Map', value: 'map' },
  { label: 'List', value: 'list' }
])
const viewMode = ref<'map' | 'list'>('map')


const selectedLot = ref<number | null>(null)

const farmSensors = computed(() => {
  if (selectedLot.value) {
    const lot = selectedFarm.value?.lots.find(l => l.id === selectedLot.value)
    return lot ? lot.sensors : []
  }
  return selectedFarm.value?.lots.flatMap(l => l.sensors) ?? []
})


</script>

<template>
  <UDashboardPanel id="home-dashboard">
    <template #header>
      <UDashboardNavbar title="Dashboard" icon="i-lucide-house">
        <template #right>
          <UTabs v-model="viewMode" :items="viewModesForMyFarm" default-value="map" size="sm" class="w-40" :content="false" />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-4 p-4">
          <template v-if="viewMode == 'map'" class="h-[45vh]">
            <DashboardMapView  />
          </template>

          <template v-else>
            <DashboardLotList/>
          </template>

        <div class="mt-4 space-y-4">
          <div class="flex items-center gap-2">
            <h2 class="font-semibold text-lg">
              Sensores
              <span v-if="selectedLot" class="text-sm text-muted-foreground font-normal">
                · Lote {{ selectedLot }}
              </span>
            </h2>
            <USelect
              v-if="selectedFarm"
              v-model="selectedLot"
              :items="[
                { label: 'Todos los lotes', value: null },
                ...(selectedFarm?.lots ?? []).map(l => ({ label: l.name, value: l.id })),
              ]"
              value-attribute="value"
              size="xs"
              class="ml-auto"
            />
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            <DashboardSensorCard
              v-for="sensor in farmSensors"
              :key="sensor.id"
              :icon="sensor.icon"
              :name="sensor.name"
              :value="`${sensor.value}${sensor.unit}`"
            />
          </div>
        </div>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
