import { test, expect } from '@playwright/test'
import { E2E_USER } from '../frontend/helpers'

// Only the contract around the model is checked here: a real answer needs the
// LLM downloaded in the ollama service and its wording is not deterministic.
test.describe('API del asistente', () => {
  test('sin token responde 401', async ({ request }) => {
    const response = await request.post('/api/assistant/chat/', {
      data: { messages: [{ role: 'user', content: 'hola' }] },
    })

    expect(response.status()).toBe(401)
  })

  test('rechaza una conversación vacía o que no termina en el usuario', async ({
    request,
  }) => {
    const login = await request.post('/api/accounts/login/', { data: E2E_USER })
    const headers = {
      Authorization: `Bearer ${(await login.json()).tokens.access}`,
    }

    const empty = await request.post('/api/assistant/chat/', {
      headers,
      data: { messages: [] },
    })
    const fromAssistant = await request.post('/api/assistant/chat/', {
      headers,
      data: { messages: [{ role: 'assistant', content: 'hola' }] },
    })

    expect(empty.status()).toBe(400)
    expect(fromAssistant.status()).toBe(400)
  })
})
