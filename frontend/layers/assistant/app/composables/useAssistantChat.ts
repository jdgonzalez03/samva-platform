import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { WRITE_TOOLS } from '../constants/assistant'
import type {
  ChatLanguage,
  ChatMessage,
  ChatRole,
  ChatTurn,
  ToolCall,
} from '../types/assistant'
import { assistantApi } from '../utils/api/assistant'
import { textOf } from '../utils/chat'

const createMessage = (
  role: ChatRole,
  text: string,
  toolCalls: ToolCall[] = [],
): ChatMessage => ({
  id: crypto.randomUUID(),
  role,
  parts: [{ type: 'text', text }],
  toolCalls,
})

// The conversation lives only in this page instance: the backend is stateless
// and receives the whole history on every turn, so leaving the page (or
// logging out) starts a fresh chat and never shows one user's chat to another.
export const useAssistantChat = () => {
  const queryClient = useQueryClient()
  const { locale } = useI18n()
  const messages = ref<ChatMessage[]>([])

  // Tool results carry Spanish farm and plot names, so the reply language is
  // stated rather than left for the model to guess from the question.
  const language = (): ChatLanguage => (locale.value === 'en' ? 'en' : 'es')

  const mutation = useMutation({
    mutationFn: (history: ChatTurn[]) => assistantApi.chat(history, language()),
    onSuccess: (data) => {
      messages.value.push(
        createMessage('assistant', data.reply, data.tool_calls),
      )
      if (data.tool_calls.some((call) => WRITE_TOOLS.has(call.name))) {
        void queryClient.invalidateQueries()
      }
    },
  })

  const history = (): ChatTurn[] =>
    messages.value.map((message) => ({
      role: message.role,
      content: textOf(message),
    }))

  const send = (text: string): void => {
    const content = text.trim()
    if (!content || mutation.isPending.value) return
    messages.value.push(createMessage('user', content))
    mutation.mutate(history())
  }

  // The failed turn is still the last user message, so resending the same
  // history asks it again without duplicating it.
  const retry = (): void => {
    if (mutation.isPending.value) return
    mutation.mutate(history())
  }

  const reset = (): void => {
    messages.value = []
    mutation.reset()
  }

  const status = computed(() => {
    if (mutation.isPending.value) return 'submitted' as const
    if (mutation.isError.value) return 'error' as const
    return 'ready' as const
  })

  return {
    messages,
    status,
    error: mutation.error,
    send,
    retry,
    reset,
  }
}
