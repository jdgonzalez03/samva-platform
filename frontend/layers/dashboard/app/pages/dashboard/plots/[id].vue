<script setup lang="ts">
import {
  DEFAULT_VIEW_MODE,
  getStoredViewMode,
  type ViewMode,
} from '../../../utils/view-mode'
import { isNotFound } from '#api/errors'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()
const route = useRoute()
const localePath = useLocalePath()
const { selectedFarm, selectFarm } = useSelectedFarm()

// A non-numeric id resolves to null, which keeps the query disabled and renders
// the not-found state without a request.
const plotId = computed(() => {
  const parsed = Number(route.params.id)
  return Number.isInteger(parsed) ? parsed : null
})

const {
  data: plot,
  isPending,
  isError,
  error,
  refetch: refetchPlotQuery,
} = usePlotQuery(plotId)

const plotNotFound = computed(
  () => plotId.value === null || (isError.value && isNotFound(error.value)),
)

const title = computed(() =>
  plot.value
    ? t('dashboard.plotDetail.title', { name: plot.value.name })
    : t('dashboard.plotDetail.notFound'),
)

// Read after mount, not inside the computed: on the server storage resolves to
// the default, and Vue does not patch a mismatched attribute during hydration —
// the SSR href would survive and send a "list" user back to the map.
const storedMode = ref<ViewMode>(DEFAULT_VIEW_MODE)
onMounted(() => {
  storedMode.value = getStoredViewMode() ?? DEFAULT_VIEW_MODE
})

const backTo = computed(() =>
  localePath({ path: '/dashboard', query: { view: storedMode.value } }),
)

const refetchPlot = (): void => {
  void refetchPlotQuery()
}

// A direct load of a plot belonging to another of the farmer's farms must leave
// the sidebar switcher coherent with what the page shows.
watch(plot, (value) => {
  if (value && value.farm.id !== selectedFarm.value?.id) {
    selectFarm(value.farm.id)
  }
})

useHead(() => ({ title: title.value }))
</script>

<template>
  <UDashboardPanel id="plot-detail">
    <template #header>
      <!-- The navbar title is the page's only <h1>, so it has to name the
           plot rather than repeat the section name. -->
      <UDashboardNavbar :title="title" icon="i-lucide-map" />
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-4 p-4">
        <ULink
          :to="backTo"
          class="inline-flex items-center gap-1 min-h-8 w-fit"
        >
          <UIcon name="i-lucide-arrow-left" />
          {{ t('dashboard.plotDetail.back') }}
        </ULink>

        <div
          v-if="isPending && !plotNotFound"
          aria-busy="true"
          class="flex flex-col gap-3"
        >
          <USkeleton class="h-8 w-64" />
          <USkeleton class="h-64 w-full" />
        </div>

        <p v-else-if="plotNotFound" class="text-muted">
          {{ t('dashboard.plotDetail.notFoundBody') }}
        </p>

        <div
          v-else-if="isError"
          role="alert"
          class="flex flex-wrap items-center gap-2 text-sm text-muted"
        >
          <span>{{ t('dashboard.plotDetail.error') }}</span>
          <UButton
            variant="link"
            color="neutral"
            size="xs"
            class="p-0"
            @click="refetchPlot"
          >
            {{ t('dashboard.retry') }}
          </UButton>
        </div>

        <pre
          v-else-if="plot"
          tabindex="0"
          role="region"
          :aria-label="t('dashboard.plotDetail.dump')"
          class="overflow-auto max-h-96 rounded-lg bg-elevated p-4 text-sm"
        ><code>{{ JSON.stringify(plot, null, 2) }}</code></pre>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
