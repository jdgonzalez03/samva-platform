export type ChatRole = 'user' | 'assistant'

// Interface locales the backend knows how to answer in.
export type ChatLanguage = 'es' | 'en'

export interface ChatTurn {
  role: ChatRole
  content: string
}

export interface ToolCall {
  name: string
  arguments: Record<string, unknown>
  result: unknown
}

export interface ChatReply {
  reply: string
  tool_calls: ToolCall[]
}

// The shape `UChatMessages` renders: text lives in `parts`.
export interface ChatMessage {
  id: string
  role: ChatRole
  parts: { type: 'text'; text: string }[]
  toolCalls: ToolCall[]
}
