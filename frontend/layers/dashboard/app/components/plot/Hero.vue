<script setup lang="ts">
import type { PlotDetail, PlotOverview } from '../../../../farm/app/types/farm'
import {
  MINI_MAP_HEIGHT_CLASS,
  STALE_AFTER_MS,
} from '../../constants/plot-detail'

const props = defineProps<{
  plot: PlotDetail
  overview: PlotOverview | undefined
  now: number
}>()

const { t, locale } = useI18n()

const latestReadingAt = computed(() => {
  const times = (props.overview?.conditions ?? []).map((condition) =>
    Date.parse(condition.recorded_at),
  )
  return times.length > 0 ? Math.max(...times) : null
})

const reporting = computed(() => {
  if (latestReadingAt.value === null) {
    return {
      label: t('dashboard.plotDetail.hero.noData'),
      color: 'neutral' as const,
    }
  }
  if (props.now - latestReadingAt.value > STALE_AFTER_MS) {
    return {
      label: t('dashboard.plotDetail.hero.stale'),
      color: 'warning' as const,
    }
  }
  return {
    label: t('dashboard.plotDetail.hero.live'),
    color: 'success' as const,
  }
})

const updatedText = computed(() =>
  latestReadingAt.value === null
    ? null
    : t('dashboard.plotDetail.hero.updated', {
        time: formatRelativeTime(
          new Date(latestReadingAt.value).toISOString(),
          locale.value,
          props.now,
        ),
      }),
)

const area = computed(() =>
  props.plot.area_hectares === null
    ? null
    : t('dashboard.plotDetail.hero.area', {
        value: new Intl.NumberFormat(locale.value, {
          maximumFractionDigits: 2,
        }).format(Number(props.plot.area_hectares)),
      }),
)
</script>

<template>
  <UCard variant="subtle" :ui="{ body: 'p-0 sm:p-0' }">
    <div class="grid lg:grid-cols-5">
      <div class="flex flex-col justify-between gap-6 p-6 lg:col-span-3">
        <div class="flex flex-col gap-3">
          <div class="flex items-center gap-2 text-sm text-muted">
            <UIcon name="i-lucide-tractor" aria-hidden="true" />
            <span>
              {{
                t('dashboard.plotDetail.hero.farm', { name: plot.farm.name })
              }}
            </span>
          </div>
          <p class="text-3xl font-semibold text-highlighted">{{ plot.name }}</p>
          <p v-if="plot.description" class="text-muted max-w-prose">
            {{ plot.description }}
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <UBadge
            :label="reporting.label"
            :color="reporting.color"
            variant="subtle"
            size="lg"
          >
            <template #leading>
              <span class="relative flex size-2" aria-hidden="true">
                <span
                  v-if="reporting.color === 'success'"
                  class="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-75 motion-reduce:animate-none"
                />
                <span
                  class="relative inline-flex size-2 rounded-full bg-current"
                />
              </span>
            </template>
          </UBadge>
          <UBadge
            v-if="area"
            :label="area"
            icon="i-lucide-ruler"
            color="neutral"
            variant="subtle"
            size="lg"
          />
          <UBadge
            :label="
              t('dashboard.plotDetail.hero.sensors', plot.sensor_count, {
                named: { count: plot.sensor_count },
              })
            "
            icon="i-lucide-radio-tower"
            color="neutral"
            variant="subtle"
            size="lg"
          />
          <span v-if="updatedText" class="text-sm text-muted">
            {{ updatedText }}
          </span>
        </div>
      </div>

      <div class="p-2 lg:col-span-2">
        <ClientOnly v-if="plot.geometry">
          <!-- A figure, not role="img": Leaflet's attribution links sit
               inside, and an image role may not contain interactive content. -->
          <figure>
            <PlotMiniMap :geometry="plot.geometry" />
            <figcaption class="sr-only">
              {{ t('dashboard.plotDetail.hero.map', { name: plot.name }) }}
            </figcaption>
          </figure>
          <template #fallback>
            <USkeleton :class="MINI_MAP_HEIGHT_CLASS" class="w-full" />
          </template>
        </ClientOnly>
        <div
          v-else
          :class="MINI_MAP_HEIGHT_CLASS"
          class="flex flex-col items-center justify-center gap-2 rounded-lg bg-elevated p-6 text-center text-sm text-muted"
        >
          <UIcon
            name="i-lucide-map-pin-off"
            class="size-6"
            aria-hidden="true"
          />
          {{ t('dashboard.plotDetail.hero.noMap') }}
        </div>
      </div>
    </div>
  </UCard>
</template>
