<script setup lang="ts">
import type { BasemapId } from '../../constants/map'

defineProps<{
  modelValue: BasemapId
}>()

const emit = defineEmits<{ 'update:modelValue': [value: BasemapId] }>()

const { t } = useI18n()

const items = computed(() => [
  { value: 'street', label: t('dashboard.map.street') },
  { value: 'satellite', label: t('dashboard.map.satellite') },
])
</script>

<template>
  <URadioGroup
    :model-value="modelValue"
    :items="items"
    orientation="horizontal"
    :legend="t('dashboard.map.basemap')"
    :aria-label="t('dashboard.map.basemap')"
    :ui="{
      fieldset: 'flex-wrap items-center gap-x-4 gap-y-1',
      legend: 'mb-0 text-sm',
    }"
    @update:model-value="emit('update:modelValue', $event as BasemapId)"
  />
</template>
