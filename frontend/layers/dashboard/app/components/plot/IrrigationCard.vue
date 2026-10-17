<script setup lang="ts">
import type { PlotIrrigation } from '../../../../farm/app/types/farm'

const props = defineProps<{
  irrigation: PlotIrrigation | null
  plotId: number
  now: number
}>()

const { t, locale } = useI18n()
const localePath = useLocalePath()

// A plain route string into the predictions layer: the link is the whole
// integration, so dashboard gains no dependency on it.
const predictionLink = computed(() =>
  localePath({
    path: '/dashboard/predictions/fuzzy',
    query: { plot: String(props.plotId) },
  }),
)

const minutes = computed(() =>
  props.irrigation
    ? new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }).format(
        props.irrigation.irrigation_time_minutes,
      )
    : null,
)
</script>

<template>
  <UCard variant="subtle" :ui="{ body: 'flex flex-col gap-4' }">
    <template #header>
      <h2 class="flex items-center gap-2 font-semibold text-highlighted">
        <UIcon
          name="i-lucide-droplets"
          class="text-primary"
          aria-hidden="true"
        />
        {{ t('dashboard.plotDetail.irrigation.title') }}
      </h2>
    </template>

    <template v-if="irrigation">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <p class="text-4xl font-semibold text-highlighted tabular-nums">
          {{ t('dashboard.plotDetail.irrigation.minutes', { value: minutes }) }}
        </p>
        <UBadge
          :label="
            t(
              `dashboard.plotDetail.irrigation.labels.${irrigation.output_label}`,
            )
          "
          size="lg"
          variant="subtle"
        />
      </div>
      <p class="text-sm text-muted">
        {{
          t('dashboard.plotDetail.irrigation.computedAt', {
            time: formatRelativeTime(irrigation.requested_at, locale, now),
            hours: irrigation.avg_period_hours,
          })
        }}
      </p>
      <UButton
        :to="predictionLink"
        :label="t('dashboard.plotDetail.irrigation.recalculate')"
        icon="i-lucide-refresh-cw"
        variant="outline"
        class="w-fit"
      />
    </template>

    <UEmpty
      v-else
      icon="i-lucide-droplets"
      :description="t('dashboard.plotDetail.irrigation.empty')"
      :actions="[
        {
          label: t('dashboard.plotDetail.irrigation.calculate'),
          icon: 'i-lucide-calculator',
          to: predictionLink,
        },
      ]"
      variant="naked"
    />
  </UCard>
</template>
