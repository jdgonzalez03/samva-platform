<script setup lang="ts">
import {
  AVERAGE_HOURS_OPTIONS,
  CHART_HEIGHT_CLASS,
} from '../../../constants/predictions'
import type {
  IrrigationPrediction,
  MissingSensorData,
} from '../../../types/predictions'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t, te, locale } = useI18n()

const {
  selectedFarm,
  farmsPending,
  plotList,
  plotsPending,
  plotId,
  hours,
  setPlot,
  setHours,
} = useIrrigationSelection()

const { data: definitions } = useIrrigationDefinitionsQuery()
const {
  data: history,
  isPending: historyPending,
  isError: historyError,
  refetch: refetchHistory,
} = useIrrigationHistoryQuery(plotId)
const {
  mutate: createPrediction,
  data: createdPrediction,
  error: createError,
  isPending: isCalculating,
  reset: resetCreation,
} = useCreateIrrigationPrediction()

const plotItems = computed(() =>
  plotList.value.map((plot) => ({ label: plot.name, value: plot.id })),
)
const hoursItems = computed(() =>
  AVERAGE_HOURS_OPTIONS.map((option) => ({
    label: t('predictions.fuzzy.hoursOption', { hours: option }),
    value: option as number,
  })),
)

// A result or error from the previous plot must not linger under the new one.
watch(plotId, () => resetCreation())

const historyList = computed(() => history.value?.results ?? [])

// The freshly calculated prediction wins; otherwise the plot's latest one is
// shown, so reopening the page does not start from a blank state.
const prediction = computed<IrrigationPrediction | null>(
  () => createdPrediction.value ?? historyList.value[0] ?? null,
)

const errorMessage = computed(() => {
  const error = createError.value as {
    status?: number
    data?: MissingSensorData
  } | null
  if (!error) return null
  if (error.status !== 422 || !error.data?.missing) {
    return t('predictions.fuzzy.error')
  }
  const variables = error.data.missing
    .map((key) =>
      te(`predictions.fuzzy.missingVariables.${key}`)
        ? t(`predictions.fuzzy.missingVariables.${key}`)
        : key,
    )
    .join(', ')
  return t('predictions.fuzzy.missing', { variables })
})

const activationSummary = computed(() => {
  if (!prediction.value) return ''
  const percent = new Intl.NumberFormat(locale.value, { style: 'percent' })
  const list = Object.entries(prediction.value.output_activation)
    .map(
      ([term, degree]) =>
        `${t(`predictions.fuzzy.labels.${term}`)} ${percent.format(degree)}`,
    )
    .join(', ')
  return t('predictions.fuzzy.chart.alternative', { list })
})

const calculate = (): void => {
  if (plotId.value === null) return
  createPrediction({ plotId: plotId.value, hours: hours.value })
}

const retryHistory = (): void => {
  void refetchHistory()
}

useHead(() => ({ title: t('predictions.fuzzy.title') }))
</script>

<template>
  <UDashboardPanel id="predictions-fuzzy">
    <template #header>
      <UDashboardNavbar
        :title="t('predictions.fuzzy.title')"
        icon="i-lucide-waves"
      />

      <UDashboardToolbar
        v-if="selectedFarm && plotList.length > 0"
        :ui="{ root: 'items-end gap-4 py-3 overflow-visible' }"
      >
        <template #left>
          <div class="flex flex-wrap items-end gap-4">
            <UFormField :label="t('predictions.fuzzy.plot')" name="plot">
              <USelect
                :model-value="plotId ?? undefined"
                :items="plotItems"
                :aria-label="t('predictions.fuzzy.plot')"
                class="min-w-48"
                @update:model-value="(value) => setPlot(Number(value))"
              />
            </UFormField>
            <UFormField :label="t('predictions.fuzzy.window')" name="hours">
              <USelect
                :model-value="hours"
                :items="hoursItems"
                :aria-label="t('predictions.fuzzy.window')"
                class="min-w-40"
                @update:model-value="(value) => setHours(Number(value))"
              />
            </UFormField>
            <UButton
              :label="t('predictions.fuzzy.calculate')"
              icon="i-lucide-calculator"
              :loading="isCalculating"
              :disabled="plotId === null"
              @click="calculate"
            />
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-6 p-4">
        <div
          v-if="farmsPending || (selectedFarm && plotsPending)"
          aria-busy="true"
          class="flex flex-col gap-4"
        >
          <USkeleton class="h-6 w-72" />
          <USkeleton class="h-32 w-full" />
        </div>

        <p v-else-if="!selectedFarm" class="text-muted">
          {{ t('predictions.fuzzy.noFarm') }}
        </p>

        <p v-else-if="plotList.length === 0" class="text-muted">
          {{ t('predictions.fuzzy.noPlots') }}
        </p>

        <template v-else>
          <p class="text-sm text-muted">
            {{ t('predictions.fuzzy.subtitle') }}
          </p>

          <UAlert
            v-if="errorMessage"
            :description="errorMessage"
            icon="i-lucide-circle-alert"
            color="error"
            variant="subtle"
            role="alert"
          />

          <div
            v-if="isCalculating || (historyPending && !prediction)"
            aria-busy="true"
            class="flex flex-col gap-4"
          >
            <USkeleton class="h-32 w-full" />
            <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
          </div>

          <p v-else-if="!prediction" class="text-muted">
            {{ t('predictions.fuzzy.empty') }}
          </p>

          <template v-else>
            <PredictionsIrrigationResult :prediction="prediction" />

            <PredictionsIrrigationInputs
              :prediction="prediction"
              :definitions="definitions"
            />

            <section
              class="flex flex-col gap-3"
              :aria-label="t('predictions.fuzzy.chart.title')"
            >
              <h2 class="text-base font-semibold text-highlighted">
                {{ t('predictions.fuzzy.chart.title') }}
              </h2>
              <p class="text-sm text-muted">
                {{ t('predictions.fuzzy.chart.description') }}
              </p>
              <ClientOnly v-if="definitions">
                <div aria-hidden="true">
                  <PredictionsIrrigationOutputChart
                    :definition="definitions.irrigation_time"
                    :activation="prediction.output_activation"
                    :minutes="prediction.irrigation_time_minutes"
                  />
                </div>
                <template #fallback>
                  <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
                </template>
              </ClientOnly>
              <p class="text-sm">{{ activationSummary }}</p>
            </section>
          </template>

          <PredictionsIrrigationHistory
            :predictions="historyList"
            :pending="historyPending"
            :error="historyError"
            @retry="retryHistory"
          />
        </template>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
