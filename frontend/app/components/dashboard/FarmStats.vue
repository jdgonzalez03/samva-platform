<script setup lang="ts">

const baseStats = [{
  title: 'Temperatura Promedio',
  icon: 'i-lucide-thermometer',
  minValue: 15,
  maxValue: 35,
  minVariation: -5,
  maxVariation: 8,
  unit: '°C',
  formatter: (value: number) => `${value.toFixed(1)}°C`
}, {
  title: 'Humedad Promedio',
  icon: 'i-lucide-droplets',
  minValue: 30,
  maxValue: 85,
  minVariation: -10,
  maxVariation: 15,
  unit: '%',
  formatter: (value: number) => `${value.toFixed(1)}%`
}, {
  title: 'pH del Suelo',
  icon: 'i-lucide-leaf',
  minValue: 5.5,
  maxValue: 8.5,
  minVariation: -2,
  maxVariation: 3,
  unit: 'pH',
  formatter: (value: number) => `${value.toFixed(2)}`
}, {
  title: 'Radiación Solar',
  icon: 'i-lucide-sun',
  minValue: 100,
  maxValue: 1000,
  minVariation: -20,
  maxVariation: 25,
  unit: 'W/m²',
  formatter: (value: number) => `${value.toFixed(0)} W/m²`
}]

const { data: stats } = await useAsyncData<any[]>('stats', async () => {
  return baseStats.map((stat) => {
    // Generar valor aleatorio dentro del rango del sensor
    const value = stat.minValue + Math.random() * (stat.maxValue - stat.minValue)
    // Generar variación aleatoria
    const variation = stat.minVariation + Math.random() * (stat.maxVariation - stat.minVariation)

    return {
      title: stat.title,
      icon: stat.icon,
      value: stat.formatter ? stat.formatter(value) : value,
      variation: parseFloat(variation.toFixed(1))
    }
  })
})
</script>

<template>
  <UPageGrid class="lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-px">
    <UPageCard
      v-for="(stat, index) in stats"
      :key="index"
      :icon="stat.icon"
      :title="stat.title"
      to="/dashboard/history"
      variant="subtle"
      :ui="{
        container: 'gap-y-1.5',
        wrapper: 'items-start',
        leading: 'p-2.5 rounded-full bg-primary/10 ring ring-inset ring-primary/25 flex-col',
        title: 'font-normal text-muted text-xs uppercase'
      }"
      class="lg:rounded-none first:rounded-l-lg last:rounded-r-lg hover:z-1"
    >
      <div class="flex items-center gap-2">
        <span class="text-2xl font-semibold text-highlighted">
          {{ stat.value }}
        </span>

        <UBadge
          :color="stat.variation > 0 ? 'success' : 'error'"
          variant="subtle"
          class="text-xs"
        >
          {{ stat.variation > 0 ? '+' : '' }}{{ stat.variation }}%
        </UBadge>
      </div>
    </UPageCard>
  </UPageGrid>
</template>