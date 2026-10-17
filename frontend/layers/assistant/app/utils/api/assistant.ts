import { fetcher } from '#api/fetcher'
import type { ChatLanguage, ChatReply, ChatTurn } from '../../types/assistant'

export const assistantApi = {
  chat: (messages: ChatTurn[], language: ChatLanguage) =>
    fetcher.post<ChatReply>('assistant/chat/', { messages, language }),
}
