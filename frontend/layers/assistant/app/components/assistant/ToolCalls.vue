<script setup lang="ts">
import { DEFAULT_TOOL_ICON, TOOL_ICONS } from '../../constants/assistant'
import type { ToolCall } from '../../types/assistant'

defineProps<{ calls: ToolCall[] }>()

const { t, te } = useI18n()

const label = (call: ToolCall): string => {
  const key = `assistant.tools.${call.name}`
  return te(key) ? t(key) : t('assistant.tools.unknown', { name: call.name })
}

const hasError = (call: ToolCall): boolean =>
  typeof call.result === 'object' &&
  call.result !== null &&
  'error' in call.result
</script>

<template>
  <div class="flex flex-col gap-1">
    <UChatTool
      v-for="(call, index) in calls"
      :key="`${call.name}-${index}`"
      :text="label(call)"
      :suffix="hasError(call) ? t('assistant.toolFailed') : undefined"
      :icon="TOOL_ICONS[call.name] ?? DEFAULT_TOOL_ICON"
    >
      <pre
        class="max-h-64 overflow-auto rounded-md bg-elevated p-2 text-xs text-muted whitespace-pre-wrap"
        >{{ JSON.stringify(call.result, null, 2) }}</pre>
    </UChatTool>
  </div>
</template>
