<script setup lang="ts">
import { QUICK_ACTIONS, TOOL_ICONS } from '../../constants/assistant'

defineProps<{ disabled?: boolean }>()

const emit = defineEmits<{
  send: [question: string]
  fill: [prompt: string]
}>()

const { t } = useI18n()

const choose = (action: (typeof QUICK_ACTIONS)[number]): void => {
  const prompt = t(`assistant.quickActions.${action.key}.prompt`)
  if (action.needsPlot) emit('fill', prompt)
  else emit('send', prompt)
}
</script>

<template>
  <ul
    class="flex flex-wrap justify-center gap-2"
    :aria-label="t('assistant.quickActionsLabel')"
  >
    <li v-for="action in QUICK_ACTIONS" :key="action.key">
      <UButton
        :label="t(`assistant.quickActions.${action.key}.label`)"
        :icon="TOOL_ICONS[action.tool]"
        :trailing-icon="action.needsPlot ? 'i-lucide-pencil' : undefined"
        :disabled="disabled"
        color="neutral"
        variant="outline"
        size="sm"
        @click="choose(action)"
      />
    </li>
  </ul>
</template>
