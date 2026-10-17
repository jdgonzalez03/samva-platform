<script setup lang="ts">
import {
  FALLBACK_STATUS_LOOK,
  STATION_STATUS_LOOKS,
} from '../../constants/stations'

const props = withDefaults(
  defineProps<{ status: string; size?: 'md' | 'lg' }>(),
  { size: 'md' },
)

const { t, te } = useI18n()

const look = computed(
  () => STATION_STATUS_LOOKS[props.status] ?? FALLBACK_STATUS_LOOK,
)

// The label is the state, the colour only repeats it (1.4.1).
const label = computed(() => {
  const key = `farm.stations.status.${props.status}`
  return te(key) ? t(key) : t('farm.stations.status.unknown')
})
</script>

<template>
  <UBadge
    :color="look.color"
    :icon="look.icon"
    variant="subtle"
    :size="size"
    :label="label"
  />
</template>
