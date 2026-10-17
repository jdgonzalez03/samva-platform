<script setup lang="ts">
import { MODEL_CARDS } from '../../../constants/predictions'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()
const localePath = useLocalePath()

const { data: models, isPending, isError, refetch } = usePredictionModelsQuery()

const cards = computed(() =>
  (models.value ?? []).flatMap((model) => {
    const card = MODEL_CARDS[model.key]
    if (!card) return []
    return [
      {
        key: model.key,
        icon: card.icon,
        to: localePath(card.path),
        title: t(`predictions.models.${card.i18nKey}.title`),
        description: t(`predictions.models.${card.i18nKey}.description`),
      },
    ]
  }),
)

const retry = (): void => {
  void refetch()
}

useHead(() => ({ title: t('predictions.title') }))
</script>

<template>
  <UDashboardPanel id="predictions">
    <template #header>
      <UDashboardNavbar
        :title="t('predictions.title')"
        icon="i-lucide-brain-circuit"
      />
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-6 p-4">
        <p class="text-sm text-muted">{{ t('predictions.subtitle') }}</p>

        <div
          v-if="isPending"
          aria-busy="true"
          class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          <USkeleton class="h-36 w-full" />
        </div>

        <div v-else-if="isError" role="alert" class="flex items-center gap-3">
          <p class="text-error">{{ t('predictions.modelsError') }}</p>
          <UButton
            :label="t('predictions.retry')"
            icon="i-lucide-refresh-cw"
            variant="outline"
            @click="retry"
          />
        </div>

        <UPageGrid v-else class="lg:grid-cols-3">
          <UPageCard
            v-for="card in cards"
            :key="card.key"
            :title="card.title"
            :description="card.description"
            :icon="card.icon"
            :to="card.to"
            variant="subtle"
            spotlight
          />
        </UPageGrid>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
