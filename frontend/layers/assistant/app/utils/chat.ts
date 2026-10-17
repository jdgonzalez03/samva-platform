import type { ChatMessage } from '../types/assistant'

export const textOf = (message: ChatMessage): string =>
  message.parts.map((part) => part.text).join('')
