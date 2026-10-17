<script setup lang="ts">
import { INPUT_ICONS, IRRIGATION_INPUTS } from '../../constants/predictions'
import type {
  IrrigationDefinitions,
  IrrigationInput,
  IrrigationPrediction,
} from '../../types/predictions'

const props = defineProps<{
  prediction: IrrigationPrediction
  definitions: IrrigationDefinitions | undefined
}>()

const { t, locale } = useI18n()

const AVERAGE_FIELDS: Record<IrrigationInput, keyof IrrigationPrediction> = {
  moisture: 'avg_moisture',
  temperature: 'avg_temperature',
  radiation: 'avg_radiation',
}

const numberFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)
const percentFormat = computed(
  () => new Intl.NumberFormat(locale.value, { style: 'percent' }),
)

const formatWithUnit = (value: number, unit: string): string =>
  `${numberFormat.value.format(value)} ${unit}`.trim()

interface SourceRow {
  key: 'field' | 'station' | 'used'
  label: string
  // null when that source had no readings in the window.
  value: string | null
}

const formatSource = (value: number | null, unit: string): string | null =>
  value === null ? null : formatWithUnit(value, unit)

// Predictions stored before the per-source breakdown carry `{}`: no row then.
const sourceRows = (
  input: IrrigationInput,
  unit: string,
  used: string,
): SourceRow[] | null => {
  const sources = props.prediction.input_sources?.[input]
  if (!sources) return null
  return [
    {
      key: 'field',
      label: t('predictions.fuzzy.sources.field'),
      value: formatSource(sources.field, unit),
    },
    {
      key: 'station',
      label: t('predictions.fuzzy.sources.station'),
      value: formatSource(sources.station, unit),
    },
    { key: 'used', label: t('predictions.fuzzy.sources.used'), value: used },
  ]
}

const cards = computed(() =>
  IRRIGATION_INPUTS.map((input) => {
    const definition = props.definitions?.[input]
    const unit = definition?.unit ?? ''
    const average = props.prediction[AVERAGE_FIELDS[input]] as number
    const value = formatWithUnit(average, unit)
    return {
      input,
      icon: INPUT_ICONS[input],
      title: t(`predictions.fuzzy.inputs.${input}`),
      value,
      sources: sourceRows(input, unit, value),
      clippedNote:
        props.prediction.clipped_inputs.includes(input) && definition
          ? t('predictions.fuzzy.clipped', {
              min: numberFormat.value.format(definition.bounds[0]),
              max: numberFormat.value.format(definition.bounds[1]),
              unit,
            })
          : null,
      memberships: Object.entries(
        props.prediction.input_memberships[input] ?? {},
      ).map(([term, degree]) => ({
        term,
        label: t(`predictions.fuzzy.terms.${term}`),
        degree,
        percent: percentFormat.value.format(degree),
      })),
    }
  }),
)
</script>

<template>
  <section class="flex flex-col gap-3">
    <h2 class="text-base font-semibold text-highlighted">
      {{ t('predictions.fuzzy.inputs.title') }}
    </h2>
    <div class="grid gap-4 md:grid-cols-3">
      <UCard v-for="card in cards" :key="card.input" variant="subtle">
        <div class="flex flex-col gap-4">
          <div class="flex items-center gap-2">
            <UIcon
              :name="card.icon"
              class="size-5 text-primary"
              aria-hidden="true"
            />
            <h3 class="text-sm font-medium text-muted">{{ card.title }}</h3>
          </div>
          <p class="text-2xl font-semibold text-highlighted">
            {{ card.value }}
          </p>

          <dl
            v-if="card.sources"
            class="-mt-2 flex flex-wrap gap-x-2 gap-y-1 text-xs text-muted"
          >
            <div
              v-for="(source, index) in card.sources"
              :key="source.key"
              class="flex gap-1"
            >
              <dt>{{ source.label }}</dt>
              <dd class="font-medium tabular-nums text-default">
                <template v-if="source.value !== null">{{
                  source.value
                }}</template>
                <template v-else>
                  <span aria-hidden="true">—</span>
                  <span class="sr-only">{{
                    t('predictions.fuzzy.sources.none')
                  }}</span>
                </template>
                <span
                  v-if="index < card.sources.length - 1"
                  aria-hidden="true"
                  class="ms-1 font-normal text-muted"
                  >·</span
                >
              </dd>
            </div>
          </dl>

          <UAlert
            v-if="card.clippedNote"
            :description="card.clippedNote"
            icon="i-lucide-triangle-alert"
            color="warning"
            variant="subtle"
          />

          <ul class="flex flex-col gap-2">
            <li
              v-for="membership in card.memberships"
              :key="membership.term"
              class="flex flex-col gap-1"
            >
              <div class="flex justify-between text-xs">
                <span>{{ membership.label }}</span>
                <span class="font-medium tabular-nums">{{
                  membership.percent
                }}</span>
              </div>
              <UProgress
                :model-value="membership.degree * 100"
                :aria-label="
                  t('predictions.fuzzy.membership', { term: membership.label })
                "
                size="sm"
              />
            </li>
          </ul>
        </div>
      </UCard>
    </div>
  </section>
</template>
