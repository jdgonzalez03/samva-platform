import { test, expect, type Locator, type Page } from '@playwright/test'
import {
  apiAccessToken,
  apiSecretOf,
  gotoHydrated,
  ingestReadings,
  loginAs,
  T,
} from './helpers'

const IRRIGATION_URL = '**/api/predictions/plots/*/irrigation/**'
const FUZZY_PATH = '/dashboard/predictions/fuzzy'

// Seed: the active sensor of `T.plotFullInputs` that measures all three inputs.
const FULL_SENSOR_SERIAL = 'SEED-0005'

const INPUT_TITLES = [T.inputMoisture, T.inputTemperature, T.inputRadiation]

const PREDICTION = {
  id: 901,
  plot: 1,
  avg_moisture: 40,
  avg_temperature: 17,
  avg_radiation: 600,
  avg_period_hours: 6,
  irrigation_time_minutes: 10.14,
  output_label: 'very_little',
  input_memberships: {
    moisture: { low: 0, medium: 0.333, high: 0.667 },
    temperature: { low: 0, medium: 0.6, high: 0.4 },
    radiation: { low: 0, medium: 1, high: 0 },
  },
  output_activation: {
    nothing: 0.6,
    very_little: 0.333,
    little: 0.333,
    long: 0,
    very_long: 0,
  },
  clipped_inputs: [],
  requested_at: '2026-09-29T15:00:00Z',
}

// Station readings only for temperature, so moisture and radiation show the
// "no data" placeholder in their station row.
const PREDICTION_WITH_SOURCES = {
  ...PREDICTION,
  avg_temperature: 17.5,
  input_sources: {
    moisture: { field: 40, station: null },
    temperature: { field: 17, station: 18 },
    radiation: { field: 600, station: null },
  },
}

const emptyHistory = { count: 0, page: 1, page_size: 10, results: [] }

// The seed has no sensor readings, so the view is driven by stubbed responses;
// the real calculation is covered by backend/api_predictions.spec.ts.
async function stubIrrigation(
  page: Page,
  post: { status: number; json: object },
  history: object = emptyHistory,
) {
  await page.route(IRRIGATION_URL, (route) =>
    route.request().method() === 'POST'
      ? route.fulfill(post)
      : route.fulfill({ json: history }),
  )
}

/** The fuzzy view's card for one model input, found by its heading. */
function inputCard(page: Page, title: string): Locator {
  return page
    .getByRole('heading', { name: title, exact: true, level: 3 })
    .locator('xpath=ancestor::*[@data-slot="root"][1]')
}

/**
 * The value next to one breakdown label. A null source renders an aria-hidden
 * "—" plus sr-only text, and the separators are aria-hidden too, so values are
 * matched loosely rather than by exact text.
 */
function sourceValue(card: Locator, label: string): Locator {
  return card
    .locator('dt', { hasText: label })
    .locator('xpath=following-sibling::dd[1]')
}

/** "Usado:" repeats the averaged headline value of its card. */
async function expectUsedMatchesHeadline(card: Locator): Promise<void> {
  // Both are re-read together, so a re-render between reads cannot split them.
  await expect
    .poll(async () => {
      const used = await sourceValue(card, T.sourceUsed).innerText()
      const headline = await card.locator('p').first().innerText()
      return used.trim() === headline.trim() && headline.trim() !== ''
    })
    .toBe(true)
}

async function selectPlot(page: Page, plotName: string): Promise<void> {
  await page.getByRole('combobox', { name: T.predictionPlot }).click()
  await page.getByRole('option', { name: plotName }).click()
}

async function calculate(page: Page): Promise<number> {
  const created = page.waitForResponse(
    (response) =>
      response.url().includes('/irrigation/') &&
      response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: T.calculatePrediction }).click()
  return (await created).status()
}

test.describe('Predicciones', () => {
  test('el sidebar lleva al catálogo y la tarjeta abre la vista de lógica difusa', async ({
    page,
  }) => {
    await loginAs(page)

    await page.getByRole('link', { name: T.navPredictions }).click()
    await expect(page).toHaveURL(/\/dashboard\/predictions$/)

    // UPageCard's `<a>` has no box of its own (its overlay span takes the clicks), so
    // Playwright cannot click it; Enter follows it exactly as a keyboard user would.
    await page.getByRole('link', { name: T.fuzzyIrrigationCard }).press('Enter')
    await expect(page).toHaveURL(/\/dashboard\/predictions\/fuzzy/)
    await expect(
      page.getByRole('heading', { name: T.fuzzyTitle }),
    ).toBeVisible()
  })

  test('el hijo "Lógica difusa" del sidebar abre la vista directamente', async ({
    page,
  }) => {
    await loginAs(page)

    await page.getByRole('link', { name: T.navFuzzyLogic, exact: true }).click()

    await expect(page).toHaveURL(/\/dashboard\/predictions\/fuzzy/)
  })

  test('calcular muestra los minutos, el grupo y las pertenencias', async ({
    page,
  }) => {
    await stubIrrigation(page, { status: 201, json: PREDICTION })
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/predictions/fuzzy')
    await expect(page.getByText(T.predictionEmpty)).toBeVisible()
    await expect(page.getByText(T.predictionHistoryEmpty)).toBeVisible()

    await page.getByRole('button', { name: T.calculatePrediction }).click()

    await expect(page.getByText(T.predictionResultTitle)).toBeVisible()
    await expect(page.getByText(T.predictionMinutes).first()).toBeVisible()
    await expect(
      page.getByText(T.predictionLabel, { exact: true }).first(),
    ).toBeVisible()
    await expect(
      page.getByText(new RegExp(`${T.predictionActivation}\\s*%`)),
    ).toBeVisible()
    await expect(page.getByRole('progressbar')).toHaveCount(9)
  })

  test('sin lecturas recientes explica qué variables faltan', async ({
    page,
  }) => {
    await stubIrrigation(page, {
      status: 422,
      json: {
        detail: 'No recent readings for: soil_moisture, solar_radiation',
        missing: ['soil_moisture', 'solar_radiation'],
      },
    })
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/predictions/fuzzy')

    await page.getByRole('button', { name: T.calculatePrediction }).click()

    // USkeleton also renders with role="alert", so the message is matched by its text.
    await expect(
      page.getByRole('alert').filter({ hasText: T.missingReadings }),
    ).toBeVisible()
  })

  test('al abrir la vista muestra la última predicción del lote y su historial', async ({
    page,
  }) => {
    await stubIrrigation(
      page,
      { status: 201, json: PREDICTION },
      { count: 1, page: 1, page_size: 10, results: [PREDICTION] },
    )
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/predictions/fuzzy')

    await expect(page.getByText(T.predictionResultTitle)).toBeVisible()
    await expect(page.getByText(T.predictionHistoryTitle)).toBeVisible()
    await expect(page.locator('tbody tr')).toHaveCount(1)
  })

  test('cada entrada desglosa los sensores de campo, la estación y el valor usado', async ({
    page,
  }) => {
    await stubIrrigation(
      page,
      { status: 201, json: PREDICTION_WITH_SOURCES },
      { count: 1, page: 1, page_size: 10, results: [PREDICTION_WITH_SOURCES] },
    )
    await loginAs(page)
    await gotoHydrated(page, FUZZY_PATH)

    const moisture = inputCard(page, T.inputMoisture)
    await expect(sourceValue(moisture, T.sourceField)).toContainText('40')
    await expect(sourceValue(moisture, T.sourceStation)).toContainText(
      T.sourceNone,
    )
    const temperature = inputCard(page, T.inputTemperature)
    await expect(sourceValue(temperature, T.sourceField)).toContainText('17')
    await expect(sourceValue(temperature, T.sourceStation)).toContainText('18')
    await expectUsedMatchesHeadline(temperature)
    await expect(sourceValue(temperature, T.sourceUsed)).toContainText('17,5')
  })
})

// Driven by the real backend: SEED-0005 reports all three inputs, and the seeded
// weather stations are not used in predictions (the fixture default), so every
// station row reads "no data".
test.describe('Predicciones con lecturas reales', () => {
  test('tras calcular, cada entrada muestra su desglose por fuente', async ({
    page,
    request,
  }) => {
    const access = await apiAccessToken(request)
    // The history table shows minutes, so readings of one minute with equal values
    // render as identical rows and trip sensors.spec's page-overlap check; the
    // per-second offset (never 0) keeps them apart, and apart from the whole
    // values backend/api_predictions.spec.ts ingests into the same sensor.
    const offset = (new Date().getSeconds() + 1) / 10
    const ingest = await ingestReadings(
      request,
      await apiSecretOf(request, access),
      FULL_SENSOR_SERIAL,
      [
        { variable: 'soil_moisture', value: 30 + offset },
        { variable: 'air_temperature', value: 18 + offset },
        { variable: 'solar_radiation', value: 600 + offset },
      ],
    )
    expect(ingest.status()).toBe(201)

    await loginAs(page)
    await gotoHydrated(page, FUZZY_PATH)
    await selectPlot(page, T.plotFullInputs)
    expect(await calculate(page)).toBe(201)

    for (const title of INPUT_TITLES) {
      const card = inputCard(page, title)
      await expect(sourceValue(card, T.sourceField)).toHaveText(/\d/)
      await expect(sourceValue(card, T.sourceStation)).toContainText(
        T.sourceNone,
      )
      await expectUsedMatchesHeadline(card)
    }
  })

  test('un lote sin lecturas avisa que la predicción no está disponible', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, FUZZY_PATH)
    await selectPlot(page, T.plotNoSensors)
    expect(await calculate(page)).toBe(422)

    // USkeleton also renders with role="alert", so the message is matched by its text.
    await expect(
      page.getByRole('alert').filter({ hasText: T.missingAllReadings }),
    ).toBeVisible()
  })
})
