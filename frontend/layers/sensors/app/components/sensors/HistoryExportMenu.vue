<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ExportFormat } from '../../types/sensors'

defineProps<{
  disabled: boolean
  isExporting: boolean
  exportError: string | null
}>()

const emit = defineEmits<{ export: [fileFormat: ExportFormat] }>()

const { t } = useI18n()

const items = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: t('sensors.history.export.csv'),
      icon: 'i-lucide-file-spreadsheet',
      onSelect: () => emit('export', 'csv'),
    },
    {
      label: t('sensors.history.export.json'),
      icon: 'i-lucide-file-json',
      onSelect: () => emit('export', 'json'),
    },
  ],
])
</script>

<template>
  <div class="flex flex-col items-end gap-2">
    <UDropdownMenu :items="items">
      <UButton
        icon="i-lucide-download"
        color="neutral"
        variant="subtle"
        :label="t('sensors.history.export.label')"
        :loading="isExporting"
        :disabled="disabled || isExporting"
        class="min-h-8"
      />
    </UDropdownMenu>

    <p
      v-if="exportError"
      role="alert"
      class="flex items-start gap-2 max-w-sm text-sm text-error text-right"
    >
      <UIcon
        name="i-lucide-triangle-alert"
        aria-hidden="true"
        class="mt-0.5 shrink-0"
      />
      <span>{{ exportError }}</span>
    </p>
  </div>
</template>
