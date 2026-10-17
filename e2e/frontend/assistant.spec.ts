import { test, expect, type Page, type Request } from '@playwright/test'
import { gotoHydrated, loginAs, T, T_EN } from './helpers'

const CHAT_URL = '**/api/assistant/chat/'
const ASSISTANT_PATH = '/dashboard/assistant'

const FARMS_REPLY = {
  reply: 'Tienes 3 fincas: Finca El Tesoro, Finca San Vicente y Finca La Esperanza.',
  tool_calls: [
    {
      name: 'list_farms',
      arguments: {},
      result: [{ id: 1, name: 'Finca El Tesoro', address: 'Vereda', plots: 3 }],
    },
  ],
}

const IRRIGATION_REPLY = {
  reply: 'Para el Lote El Abrevadero se recomienda regar 10,1 minutos.',
  tool_calls: [
    {
      name: 'calculate_irrigation',
      arguments: { plot: 'el abrevadero' },
      result: { plot: 'Lote El Abrevadero', irrigation_time_minutes: 10.14 },
    },
  ],
}

// The LLM runs in the backend; the UI is driven by stubbed replies so the
// specs never depend on a model being downloaded or on its wording.
async function stubChat(
  page: Page,
  responses: { status?: number; json: object }[],
): Promise<Request[]> {
  const requests: Request[] = []
  await page.route(CHAT_URL, (route) => {
    requests.push(route.request())
    const next = responses.shift() ?? { json: FARMS_REPLY }
    return route.fulfill({ status: next.status ?? 200, json: next.json })
  })
  return requests
}

// Text typed right after hydration can reach the textarea before its v-model
// listens, so the send goes out empty: retry until the question shows up as a
// user message (UChatMessage renders `data-role` on its root).
async function ask(page: Page, question: string): Promise<void> {
  const prompt = page.getByRole('textbox', { name: T.assistantPrompt })
  const sent = page.locator('[data-role="user"]').filter({ hasText: question })
  const before = await sent.count()
  await expect(async () => {
    await prompt.fill(question)
    await page.getByRole('button', { name: T.assistantSend }).click()
    await expect(sent).toHaveCount(before + 1, { timeout: 1000 })
  }).toPass()
}

test.describe('Asistente', () => {
  test('el sidebar abre el asistente con preguntas sugeridas', async ({
    page,
  }) => {
    await loginAs(page)

    await page.getByRole('link', { name: T.navAssistant }).click()

    await expect(page).toHaveURL(/\/dashboard\/assistant$/)
    await expect(page).toHaveTitle(new RegExp(T.assistantTitle))
    await expect(page.getByText(T.assistantEmpty)).toBeVisible()
    await expect(
      page.getByRole('button', { name: T.assistantSuggestionFarms }),
    ).toBeVisible()
  })

  test('una sugerencia pregunta y muestra la herramienta usada y la respuesta', async ({
    page,
  }) => {
    const requests = await stubChat(page, [{ json: FARMS_REPLY }])
    await loginAs(page)
    await gotoHydrated(page, ASSISTANT_PATH)

    await page.getByRole('button', { name: T.assistantSuggestionFarms }).click()

    await expect(page.getByText(FARMS_REPLY.reply)).toBeVisible()
    await expect(page.getByText(T.assistantToolFarms)).toBeVisible()
    await expect(
      page.locator('[data-role="user"]').filter({ hasText: T.assistantSuggestionFarms }),
    ).toBeVisible()
    expect(requests[0].postDataJSON()).toEqual({
      messages: [{ role: 'user', content: T.assistantSuggestionFarms }],
      language: 'es',
    })
  })

  test('en inglés pide la respuesta en inglés', async ({ page }) => {
    const requests = await stubChat(page, [{ json: FARMS_REPLY }])
    await loginAs(page)
    await gotoHydrated(page, `/en${ASSISTANT_PATH}`)

    await page.getByRole('button', { name: T_EN.assistantSuggestionFarms }).click()

    await expect(page.getByText(FARMS_REPLY.reply)).toBeVisible()
    expect(requests[0].postDataJSON()).toEqual({
      messages: [{ role: 'user', content: T_EN.assistantSuggestionFarms }],
      language: 'en',
    })
  })

  test('una acción que necesita lote solo deja la pregunta escrita', async ({
    page,
  }) => {
    const requests = await stubChat(page, [{ json: IRRIGATION_REPLY }])
    await loginAs(page)
    await gotoHydrated(page, ASSISTANT_PATH)

    await page.getByRole('button', { name: T.assistantActionCalculate }).click()

    const prompt = page.getByRole('textbox', { name: T.assistantPrompt })
    await expect(prompt).toHaveValue(T.assistantPromptCalculate)
    await expect(prompt).toBeFocused()
    expect(requests).toHaveLength(0)
  })

  test('los consejos de uso se ocultan y no vuelven al recargar', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, ASSISTANT_PATH)
    const tips = page.getByText(T.assistantTipsTitle)
    await expect(tips).toBeVisible()

    await page.getByRole('button', { name: T.assistantTipsClose }).click()
    await expect(tips).toBeHidden()

    await gotoHydrated(page, ASSISTANT_PATH)
    await expect(page.getByText(T.assistantEmpty)).toBeVisible()
    await expect(tips).toBeHidden()
  })

  test('cada pregunta envía la conversación completa', async ({ page }) => {
    const requests = await stubChat(page, [
      { json: FARMS_REPLY },
      { json: IRRIGATION_REPLY },
    ])
    await loginAs(page)
    await gotoHydrated(page, ASSISTANT_PATH)

    await ask(page, '¿Cuántas fincas tengo?')
    await expect(page.getByText(FARMS_REPLY.reply)).toBeVisible()
    await ask(page, 'Calcula el riego del lote El Abrevadero')

    await expect(page.getByText(IRRIGATION_REPLY.reply)).toBeVisible()
    await expect(page.getByText(T.assistantToolIrrigation)).toBeVisible()
    expect(requests[1].postDataJSON()).toEqual({
      messages: [
        { role: 'user', content: '¿Cuántas fincas tengo?' },
        { role: 'assistant', content: FARMS_REPLY.reply },
        { role: 'user', content: 'Calcula el riego del lote El Abrevadero' },
      ],
      language: 'es',
    })
  })

  test('si el modelo no está disponible lo dice y Reintentar repite la pregunta', async ({
    page,
  }) => {
    const requests = await stubChat(page, [
      { status: 503, json: { detail: 'The language model service is not reachable.' } },
      { json: FARMS_REPLY },
    ])
    await loginAs(page)
    await gotoHydrated(page, ASSISTANT_PATH)

    await ask(page, '¿Cuántas fincas tengo?')

    const alert = page
      .getByRole('alert')
      .filter({ hasText: T.assistantUnavailable })
    await expect(alert).toBeVisible()
    await alert.getByRole('button', { name: T.retry }).click()

    await expect(page.getByText(FARMS_REPLY.reply)).toBeVisible()
    await expect(alert).toBeHidden()
    expect(requests[1].postDataJSON()).toEqual(requests[0].postDataJSON())
  })

  test('el límite de preguntas por minuto tiene su propio mensaje', async ({
    page,
  }) => {
    await stubChat(page, [
      { status: 429, json: { detail: 'Request was throttled.' } },
    ])
    await loginAs(page)
    await gotoHydrated(page, ASSISTANT_PATH)

    await ask(page, 'hola')

    await expect(
      page.getByRole('alert').filter({ hasText: T.assistantThrottled }),
    ).toBeVisible()
  })

  test('nueva conversación vacía el chat', async ({ page }) => {
    await stubChat(page, [{ json: FARMS_REPLY }])
    await loginAs(page)
    await gotoHydrated(page, ASSISTANT_PATH)
    await ask(page, '¿Cuántas fincas tengo?')
    await expect(page.getByText(FARMS_REPLY.reply)).toBeVisible()

    await page.getByRole('button', { name: T.assistantNewChat }).click()

    await expect(page.getByText(FARMS_REPLY.reply)).toBeHidden()
    await expect(page.getByText(T.assistantEmpty)).toBeVisible()
  })
})
