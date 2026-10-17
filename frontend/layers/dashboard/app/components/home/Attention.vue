<script setup lang="ts">
import type { AlertSeverity, FarmAlert } from '../../utils/farm-overview'

const props = defineProps<{ alerts: FarmAlert[]; now: number }>()

const { t, locale } = useI18n()
const localePath = useLocalePath()

const VISIBLE_ALERTS = 6

// Full class names, not `text-${color}`: Tailwind only ships classes it can
// find written out in the source.
const SEVERITY_STYLE: Record<
  AlertSeverity,
  { color: 'error' | 'warning' | 'info'; icon: string; iconClass: string }
> = {
  critical: {
    color: 'error',
    icon: 'i-lucide-circle-alert',
    iconClass: 'text-error',
  },
  warning: {
    color: 'warning',
    icon: 'i-lucide-triangle-alert',
    iconClass: 'text-warning',
  },
  info: { color: 'info', icon: 'i-lucide-lightbulb', iconClass: 'text-info' },
}

const relative = (iso: string): string =>
  formatRelativeTime(iso, locale.value, props.now)

const describe = (alert: FarmAlert) => {
  const plot = alert.plotName
  switch (alert.kind) {
    case 'dry':
      return {
        title: t('dashboard.home.attention.dry', { plot }),
        detail: t('dashboard.home.attention.dryDetail', {
          value: `${new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }).format(alert.value)} ${alert.unit}`,
        }),
        to: localePath(`/dashboard/plots/${alert.plotId}`),
      }
    case 'stale':
      return {
        title: t('dashboard.home.attention.stale', { plot }),
        detail: t('dashboard.home.attention.staleDetail', {
          time: relative(alert.at),
        }),
        to: localePath(`/dashboard/plots/${alert.plotId}`),
      }
    case 'noReadings':
      return {
        title: t('dashboard.home.attention.noReadings', { plot }),
        detail: t('dashboard.home.attention.noReadingsDetail'),
        to: localePath(`/dashboard/plots/${alert.plotId}`),
      }
    case 'sensorOffline':
      return {
        title: t('dashboard.home.attention.sensorOffline', {
          sensor: alert.sensorName,
        }),
        detail: t('dashboard.home.attention.sensorOfflineDetail', {
          plot,
          time: relative(alert.at),
        }),
        to: localePath(`/dashboard/plots/${alert.plotId}`),
      }
    case 'sensorNeverSeen':
      return {
        title: t('dashboard.home.attention.sensorNeverSeen', {
          sensor: alert.sensorName,
        }),
        detail: t('dashboard.home.attention.sensorNeverSeenDetail', { plot }),
        to: localePath(`/dashboard/plots/${alert.plotId}`),
      }
    case 'noIrrigation':
      return {
        title: t('dashboard.home.attention.noIrrigation', { plot }),
        detail: t('dashboard.home.attention.noIrrigationDetail'),
        to: localePath({
          path: '/dashboard/predictions/fuzzy',
          query: { plot: String(alert.plotId) },
        }),
      }
  }
}

const items = computed(() =>
  props.alerts.slice(0, VISIBLE_ALERTS).map((alert, index) => ({
    key: `${alert.kind}-${alert.plotId}-${index}`,
    ...describe(alert),
    ...SEVERITY_STYLE[alert.severity],
    severity: t(`dashboard.home.attention.severity.${alert.severity}`),
  })),
)
const hidden = computed(() => Math.max(props.alerts.length - VISIBLE_ALERTS, 0))
</script>

<template>
  <UCard variant="subtle" class="h-full">
    <template #header>
      <h2 class="flex items-center gap-2 font-semibold text-highlighted">
        <UIcon
          name="i-lucide-bell-ring"
          class="text-primary"
          aria-hidden="true"
        />
        {{ t('dashboard.home.attention.title') }}
        <UBadge
          v-if="alerts.length > 0"
          :label="String(alerts.length)"
          color="warning"
          variant="subtle"
          size="sm"
        />
      </h2>
    </template>

    <UEmpty
      v-if="alerts.length === 0"
      icon="i-lucide-circle-check"
      :description="t('dashboard.home.attention.allGood')"
      variant="naked"
    />

    <ul v-else class="flex flex-col gap-2">
      <li v-for="item in items" :key="item.key">
        <ULink
          :to="item.to"
          class="flex items-start gap-3 rounded-lg p-2 -mx-2 hover:bg-elevated/60 focus-visible:outline-2 focus-visible:outline-primary"
        >
          <UIcon
            :name="item.icon"
            :class="item.iconClass"
            class="mt-0.5 size-5 shrink-0"
            aria-hidden="true"
          />
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="font-medium text-highlighted">{{ item.title }}</span>
            <span class="text-xs text-muted">{{ item.detail }}</span>
          </span>
          <UBadge
            :label="item.severity"
            :color="item.color"
            variant="subtle"
            size="sm"
          />
        </ULink>
      </li>
      <li v-if="hidden > 0" class="text-xs text-muted">
        {{
          t('dashboard.home.attention.more', hidden, {
            named: { count: hidden },
          })
        }}
      </li>
    </ul>
  </UCard>
</template>
