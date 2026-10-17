<script setup lang="ts">
import type { ChatMessage } from '../../types/assistant'
import { textOf } from '../../utils/chat'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()

const { messages, status, error, send, retry, reset } = useAssistantChat()
const input = ref('')
const prompt = useTemplateRef<{ textareaRef: HTMLTextAreaElement | null }>(
  'prompt',
)

// `UChatMessages` types its slot props against the AI SDK, which this app does
// not install, so the slot's message is looked up again as our own type.
const messageById = computed(
  () => new Map(messages.value.map((message) => [message.id, message])),
)
const findMessage = (id: string): ChatMessage | undefined =>
  messageById.value.get(id)

const submit = (): void => {
  send(input.value)
  input.value = ''
}

// The cursor lands after the prefilled text, where the plot name goes.
const fill = async (text: string): Promise<void> => {
  input.value = text
  await nextTick()
  const textarea = prompt.value?.textareaRef
  textarea?.focus()
  textarea?.setSelectionRange(text.length, text.length)
}

const errorMessage = computed(() => {
  const code = (error.value as { status?: number } | null)?.status
  if (code === 503) return t('assistant.errors.unavailable')
  if (code === 429) return t('assistant.errors.throttled')
  return t('assistant.errors.generic')
})

useHead(() => ({ title: t('assistant.title') }))
</script>

<template>
  <UDashboardPanel id="assistant">
    <template #header>
      <UDashboardNavbar :title="t('assistant.title')" icon="i-lucide-bot">
        <template #right>
          <UButton
            v-if="messages.length"
            :label="t('assistant.newChat')"
            icon="i-lucide-message-square-plus"
            color="neutral"
            variant="outline"
            :disabled="status === 'submitted'"
            @click="reset"
          />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <UContainer class="flex flex-1 flex-col gap-4 p-4 max-w-3xl">
        <div
          v-if="!messages.length"
          class="flex flex-1 flex-col items-center justify-center gap-6 text-center"
        >
          <UIcon
            name="i-lucide-bot"
            class="size-12 text-primary"
            aria-hidden="true"
          />
          <div class="flex flex-col gap-2">
            <h2 class="text-xl font-semibold text-highlighted">
              {{ t('assistant.emptyTitle') }}
            </h2>
            <p class="text-sm text-muted">{{ t('assistant.subtitle') }}</p>
          </div>
          <AssistantUsageTips />
        </div>

        <UChatMessages
          v-else
          :messages="messages"
          :status="status"
          :user="{ side: 'right', variant: 'soft' }"
          :assistant="{ side: 'left', variant: 'naked', icon: 'i-lucide-bot' }"
          should-auto-scroll
          class="flex-1"
          aria-live="polite"
        >
          <template #content="{ message }">
            <div class="flex flex-col gap-2">
              <AssistantToolCalls
                v-if="findMessage(message.id)?.toolCalls.length"
                :calls="findMessage(message.id)!.toolCalls"
              />
              <p class="whitespace-pre-wrap">
                {{ textOf(findMessage(message.id)!) }}
              </p>
            </div>
          </template>
        </UChatMessages>

        <div
          v-if="status === 'error'"
          role="alert"
          class="flex flex-wrap items-center gap-3"
        >
          <p class="text-error">{{ errorMessage }}</p>
          <UButton
            :label="t('assistant.retry')"
            icon="i-lucide-refresh-cw"
            variant="outline"
            @click="retry"
          />
        </div>

        <AssistantQuickActions
          :disabled="status === 'submitted'"
          @send="send"
          @fill="fill"
        />

        <UChatPrompt
          ref="prompt"
          v-model="input"
          :placeholder="t('assistant.placeholder')"
          :aria-label="t('assistant.placeholder')"
          :disabled="status === 'submitted'"
          variant="subtle"
          class="sticky bottom-0"
          @submit="submit"
        >
          <UChatPromptSubmit
            :status="status === 'error' ? 'ready' : status"
            :aria-label="t('assistant.send')"
          />
        </UChatPrompt>
        <p class="text-xs text-muted text-center">
          {{ t('assistant.disclaimer') }}
        </p>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
