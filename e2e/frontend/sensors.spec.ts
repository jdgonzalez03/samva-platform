import { readFileSync } from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import {
  apiAccessToken,
  apiSecretOf,
  gotoHydrated,
  ingestReading,
  LIVE_REFRESH_MS,
  loginAs,
  LORA_USER,
  selectFarm,
  STUB_FARM,
  STUB_PLOT,
  stubSession,
  T,
} from './helpers'

const HISTORY_PATH = '/dashboard/history'

/** Page size the readings endpoint serves and `HistoryTable` renders. */
const PAGE_SIZE = 20

/**
 * Variables the seeded sensors of every mapped plot measure (air temperature,
 * solar radiation, relative humidity, soil moisture) — one chart each.
 */
const VARIABLE_COUNT = 4

/** `semantic_key` of `T.varAirTemperature`, as it travels in the URL. */
const AIR_TEMPERATURE_KEY = 'air_temperature'

/** `semantic_key` of `T.varCo2`, one of the variables the LoRa demo probes add. */
const CO2_KEY = 'co2'

/** Header row of the CSV export, fixed by the contract (never translated). */
const CSV_HEADER = 'recorded_at,plot,sensor,variable,semantic_key,value,unit'

/**
 * Picks a value in one of the filter selects. The listbox closes on selection,
 * so — unlike the sidebar farm dropdown — nothing has to be dismissed after.
 */
async function selectFilter(
  page: Page,
  filterLabel: string,
  optionName: string,
): Promise<void> {
  await page.getByRole('combobox', { name: filterLabel }).click()
  await page.getByRole('option', { name: optionName }).click()
}

test.describe('Historial de sensores', () => {
  test('la vista abre con un gráfico por cada variable del lote seleccionado', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, HISTORY_PATH)

    const charts = page.getByRole('region', { name: T.chartsRegion })
    const averages = page.getByRole('region', { name: T.averagesRegion })

    // One line chart per variable the plot measures, each captioned with its
    // own name and unit — geometry is never asserted, the caption is.
    await selectFilter(page, T.filterPlot, T.plotFirst)
    await expect(page).toHaveURL(/[?&]plot=\d+/)
    await expect(charts.locator('figure')).toHaveCount(VARIABLE_COUNT)
    await expect(
      charts.locator('figcaption').filter({ hasText: T.varAirTemperature }),
    ).toHaveCount(1)

    // A single variable narrows the grid to that one chart.
    await selectFilter(page, T.filterVariable, T.varAirTemperature)
    await expect(page).toHaveURL(
      new RegExp(`[?&]variable=${AIR_TEMPERATURE_KEY}`),
    )
    await expect(charts.locator('figure')).toHaveCount(1)
    await expect(charts.locator('figcaption')).toContainText(
      T.varAirTemperature,
    )

    // Back to farm-wide: grouped bars, one chart per variable, and the textual
    // summary names the per-plot averages the bars draw.
    await page.getByRole('button', { name: T.filtersReset }).click()
    await expect(page).not.toHaveURL(/[?&]plot=/)
    await expect(averages.locator('figure')).toHaveCount(VARIABLE_COUNT)
    await expect(
      averages
        .locator('figure')
        .filter({ hasText: T.varAirTemperature })
        .locator('p.sr-only'),
    ).toContainText(T.plotFirst)
  })

  test('la tabla muestra 20 filas y la página siguiente trae lecturas distintas', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, `${HISTORY_PATH}?view=table`)

    // `UTable` inserts an empty separator `<tr>`, so data rows are counted in
    // the body rather than with `getByRole('row')`.
    const rows = page.locator('tbody tr')
    await expect(rows).toHaveCount(PAGE_SIZE)
    const firstPage = await rows.allInnerTexts()

    await page
      .getByRole('navigation', { name: T.paginationLabel })
      // Exact: the last-page button ("Página 265") contains this name.
      .getByRole('button', { name: `${T.paginationPage} 2`, exact: true })
      .click()
    await expect(page).toHaveURL(/[?&]page=2/)

    // The query keeps the previous page on screen while the next one loads, so
    // the rows are re-read until they actually change.
    await expect
      .poll(async () => (await rows.allInnerTexts()).join(' | '))
      .not.toBe(firstPage.join(' | '))
    await expect(rows).toHaveCount(PAGE_SIZE)

    // No row repeats across pages: the readings share instants, and only the
    // `-id` tiebreak keeps the two pages from overlapping.
    const secondPage = await rows.allInnerTexts()
    expect(secondPage.filter((row) => firstPage.includes(row))).toEqual([])
  })

  test('exportar a CSV descarga un archivo con las lecturas filtradas', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, `${HISTORY_PATH}?view=table`)

    await selectFilter(page, T.filterPlot, T.plotFirst)
    await expect(page).toHaveURL(/[?&]plot=\d+/)
    await expect(page.locator('tbody tr')).toHaveCount(PAGE_SIZE)
    const plotId = new URL(page.url()).searchParams.get('plot')

    const exportRequest = page.waitForRequest((request) =>
      request.url().includes('/history/export/csv/'),
    )
    // The file arrives as a `blob:` URL clicked synthetically, not as a server
    // navigation — Chromium still raises the download event for it.
    const download = page.waitForEvent('download')

    await page.getByRole('button', { name: T.exportLabel }).click()
    await page.getByRole('menuitem', { name: T.exportCsv }).click()

    const requestUrl = new URL((await exportRequest).url())
    expect(requestUrl.searchParams.get('plot')).toBe(plotId)
    // The export covers the whole filtered set, so it carries no page.
    expect(requestUrl.searchParams.has('page')).toBe(false)

    const file = await download
    expect(file.suggestedFilename()).toMatch(
      /^historial-sensores-[a-z0-9-]+-\d{8}_\d{8}\.csv$/,
    )

    const path = await file.path()
    const content = readFileSync(path, 'utf8')
    // The file opens with a UTF-8 BOM so Excel reads the accents right.
    const lines = content.replace(/^\uFEFF/, '').trim().split(/\r?\n/)
    expect(lines[0]).toBe(CSV_HEADER)
    // Far more than the twenty rows on screen.
    expect(lines.length).toBeGreaterThan(PAGE_SIZE + 1)
  })

  test('cambiar de finca reinicia el lote sin provocar errores', async ({
    page,
  }) => {
    const notFound: string[] = []
    page.on('response', (response) => {
      if (response.status() === 404 && response.url().includes('/api/')) {
        notFound.push(response.url())
      }
    })

    await loginAs(page)
    await gotoHydrated(page, HISTORY_PATH)

    const charts = page.getByRole('region', { name: T.chartsRegion })
    await selectFilter(page, T.filterPlot, T.plotFirst)
    await expect(charts.locator('figure')).toHaveCount(VARIABLE_COUNT)

    await selectFarm(page, T.farmSecond)

    // The plot belonged to the previous farm, so it drops out of the URL
    // instead of being sent to endpoints that would not recognise it.
    await expect(page).not.toHaveURL(/[?&]plot=/)
    const averages = page.getByRole('region', { name: T.averagesRegion })
    await expect(averages.locator('figure')).toHaveCount(VARIABLE_COUNT)
    await expect(page.getByRole('alert')).toHaveCount(0)
    expect(notFound).toEqual([])
  })

  test('los filtros viajan en la URL y sobreviven a una recarga', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, HISTORY_PATH)

    await selectFilter(page, T.filterPlot, T.plotFirst)
    await selectFilter(page, T.filterVariable, T.varAirTemperature)
    await selectFilter(page, T.filterRange, T.range30d)

    await expect(page).toHaveURL(/[?&]plot=\d+/)
    await expect(page).toHaveURL(
      new RegExp(`[?&]variable=${AIR_TEMPERATURE_KEY}`),
    )
    await expect(page).toHaveURL(/[?&]range=30d/)
    const shared = page.url()

    await page.reload()

    expect(page.url()).toBe(shared)
    await expect(
      page.getByRole('combobox', { name: T.filterPlot }),
    ).toContainText(T.plotFirst)
    await expect(
      page.getByRole('combobox', { name: T.filterVariable }),
    ).toContainText(T.varAirTemperature)
    await expect(
      page.getByRole('combobox', { name: T.filterRange }),
    ).toContainText(T.range30d)
    await expect(
      page.getByRole('region', { name: T.chartsRegion }).locator('figure'),
    ).toHaveCount(1)
  })
})

// Needs the seeded readings inside the default window (`make seed-sensors`).
test.describe('Historial de las sondas LoRa', () => {
  test('una variable nueva de las sondas se puede elegir y graficar', async ({
    page,
  }) => {
    await loginAs(page, LORA_USER.email, LORA_USER.password)
    await gotoHydrated(page, HISTORY_PATH)
    await selectFarm(page, T.loraFarm, T.loraFarmDefault)

    await selectFilter(page, T.filterPlot, T.loraPlot)
    await selectFilter(page, T.filterVariable, T.varCo2)

    await expect(page).toHaveURL(new RegExp(`[?&]variable=${CO2_KEY}`))
    const charts = page.getByRole('region', { name: T.chartsRegion })
    await expect(charts.locator('figure')).toHaveCount(1)
    await expect(charts.locator('figcaption')).toContainText(T.varCo2)
  })
})

// Seeded in backend/sensors/fixtures/initial_sensors.json on Finca El Tesoro,
// the default farm: SEED-0001 is active, SEED-0004 is switched off.
const ACTIVE_SERIAL = 'SEED-0001'
const INACTIVE_SERIAL = 'SEED-0004'

test.describe('Mis sensores', () => {
  test('el sidebar lleva a la lista de sensores con su serial y estado', async ({
    page,
    request,
  }) => {
    const access = await apiAccessToken(request)
    const apiKey = await apiSecretOf(request, access)
    expect((await ingestReading(request, apiKey, ACTIVE_SERIAL)).status()).toBe(201)

    await loginAs(page)
    await page.getByRole('link', { name: T.navSensors }).click()
    await expect(page).toHaveURL(/\/dashboard\/sensors$/)
    await expect(page.getByRole('heading', { name: T.navSensors })).toBeVisible()

    const table = page.getByRole('table', { name: T.sensorsTableFarmFirst })
    const reporting = table.locator('tbody tr', { hasText: ACTIVE_SERIAL })
    await expect(reporting).toContainText(T.sensorStatusOnline)
    // The age sits in a <time> carrying the exact instant the page was fed.
    await expect(reporting.locator('time')).toHaveAttribute('datetime', /Z$/)

    const switchedOff = table.locator('tbody tr', { hasText: INACTIVE_SERIAL })
    await expect(switchedOff).toContainText(T.sensorStatusInactive)
  })

  test('cambiar de finca muestra los sensores de la nueva finca', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/sensors')
    await expect(
      page.getByRole('table', { name: T.sensorsTableFarmFirst }),
    ).toBeVisible()

    await selectFarm(page, T.farmSecond)

    const table = page.getByRole('table', { name: `Sensores de ${T.farmSecond}` })
    await expect(table).toBeVisible()
    await expect(table.locator('tbody tr', { hasText: ACTIVE_SERIAL })).toHaveCount(0)
  })
})

/** A local calendar day `days` before today, as `?from=`/`?to=` carry it. */
function calendarDaysAgo(days: number): string {
  const date = new Date(Date.now() - days * 86_400_000)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** Stubs the series endpoint and records the `date_to` of every request. */
async function recordSeriesRequests(page: Page): Promise<string[]> {
  const dateTos: string[] = []
  await page.route(
    (url) => url.pathname.endsWith(`/sensors/farms/${STUB_FARM.id}/history/series/`),
    (route) => {
      dateTos.push(new URL(route.request().url()).searchParams.get('date_to') ?? '')
      return route.fulfill({ json: [] })
    },
  )
  return dateTos
}

test.describe('Rangos cortos del historial', () => {
  // Served without the backend, so the spec holds without seeded users.
  test.use({ serviceWorkers: 'block' })

  test('la última hora y las últimas 6 horas piden la serie de ese lapso', async ({
    page,
  }) => {
    await stubSession(page)
    const spans: number[] = []
    await page.route(
      (url) => url.pathname.endsWith(`/sensors/farms/${STUB_FARM.id}/history/series/`),
      (route) => {
        const url = new URL(route.request().url())
        const from = Date.parse(url.searchParams.get('date_from')!)
        const to = Date.parse(url.searchParams.get('date_to')!)
        spans.push(Math.round((to - from) / 3_600_000))
        return route.fulfill({ json: [] })
      },
    )
    await gotoHydrated(page, `${HISTORY_PATH}?view=chart&plot=${STUB_PLOT.id}`)
    await expect.poll(() => spans.length).toBeGreaterThan(0)

    for (const [label, hours] of [[T.range1h, 1], [T.range6h, 6]] as const) {
      await selectFilter(page, T.filterRange, label)

      await expect(page).toHaveURL(new RegExp(`[?&]range=${hours}h`))
      await expect.poll(() => spans.at(-1)).toBe(hours)
    }
  })
})

test.describe('Actualización en vivo del historial', () => {
  // Served without the backend, so the spec holds without seeded users.
  test.use({ serviceWorkers: 'block' })

  test.beforeEach(async ({ page }) => {
    await page.clock.install()
    await stubSession(page)
  })

  test('el rango por defecto vuelve a pedir la serie y desliza la ventana hasta ahora', async ({
    page,
  }) => {
    const dateTos = await recordSeriesRequests(page)
    await gotoHydrated(page, `${HISTORY_PATH}?view=chart&plot=${STUB_PLOT.id}`)
    await expect.poll(() => dateTos.length).toBe(1)

    await page.clock.fastForward(LIVE_REFRESH_MS)

    await expect.poll(() => dateTos.length).toBe(2)
    expect(Date.parse(dateTos[1]!)).toBeGreaterThan(Date.parse(dateTos[0]!))
  })

  test('un rango fijo en el pasado no vuelve a pedir la serie', async ({ page }) => {
    const dateTos = await recordSeriesRequests(page)
    const from = calendarDaysAgo(20)
    const to = calendarDaysAgo(14)
    await gotoHydrated(
      page,
      `${HISTORY_PATH}?view=chart&plot=${STUB_PLOT.id}&range=custom&from=${from}&to=${to}`,
    )
    await expect.poll(() => dateTos.length).toBe(1)

    await page.clock.fastForward(LIVE_REFRESH_MS * 3)

    // Let any request the fast-forward fired reach the route before counting.
    await page.waitForTimeout(500)
    expect(dateTos).toHaveLength(1)
  })
})
