import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import {
  gotoHydrated,
  LIVE_REFRESH_MS,
  STUB_STATIONS,
  stubSession,
  stubStationCard,
  stubStations,
  T,
} from './helpers'

const LIST_PATH = '/dashboard/stations'
const STATION = STUB_STATIONS.online
const DETAIL_PATH = `${LIST_PATH}/${STATION.id}`

/** Readings the stubbed station holds in any range: three pages of 20. */
const READING_COUNT = 45
const PAGE_SIZE = 20

const DAY_MS = 86_400_000

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']

interface StationRequests {
  station: number
  series: URL[]
  readings: URL[]
  exports: URL[]
}

// Serves the detail, series, readings and export endpoints of STATION, and
// records every request so a spec can assert what the page asked for.
async function stubStationDetail(page: Page): Promise<StationRequests> {
  const requests: StationRequests = { station: 0, series: [], readings: [], exports: [] }
  const base = `/api/sensors/stations/${STATION.id}/`

  await page.route(
    (url) => url.pathname.endsWith(base),
    (route) => {
      requests.station += 1
      return route.fulfill({
        json: {
          ...stubStationCard(STATION, 'online'),
          variables: [
            { variable_id: 1, semantic_key: 'air_temperature', name: 'Temperatura del aire', unit: '°C' },
            { variable_id: 3, semantic_key: 'relative_humidity', name: 'Humedad relativa', unit: '%' },
          ],
        },
      })
    },
  )
  await page.route(
    (url) => url.pathname.endsWith(`${base}series/`),
    (route) => {
      const url = new URL(route.request().url())
      requests.series.push(url)
      const from = Date.parse(url.searchParams.get('date_from')!)
      const to = Date.parse(url.searchParams.get('date_to')!)
      const bucketSeconds = to - from > 2 * DAY_MS ? 3600 : 900
      return route.fulfill({
        json: [
          {
            variable_id: 1,
            semantic_key: 'air_temperature',
            name: 'Temperatura del aire',
            unit: '°C',
            bucket_seconds: bucketSeconds,
            points: [0, 1, 2, 3].map((index) => ({
              t: new Date(from + index * bucketSeconds * 1000).toISOString(),
              value: 20 + index,
              sample_count: 3,
            })),
          },
        ],
      })
    },
  )
  await page.route(
    (url) => url.pathname.endsWith(`${base}readings/`),
    (route) => {
      const url = new URL(route.request().url())
      requests.readings.push(url)
      const pageNumber = Number(url.searchParams.get('page') ?? '1')
      const first = (pageNumber - 1) * PAGE_SIZE
      const size = Math.max(0, Math.min(PAGE_SIZE, READING_COUNT - first))
      return route.fulfill({
        json: {
          count: READING_COUNT,
          page: pageNumber,
          page_size: PAGE_SIZE,
          results: Array.from({ length: size }, (_, index) => ({
            id: first + index + 1,
            recorded_at: new Date(Date.now() - (first + index) * 300_000).toISOString(),
            variable_id: 1,
            semantic_key: 'air_temperature',
            variable_name: 'Temperatura del aire',
            value: 20 + index,
            unit: '°C',
          })),
        },
      })
    },
  )
  await page.route(
    (url) => url.pathname.includes(`${base}export/`),
    (route) => {
      requests.exports.push(new URL(route.request().url()))
      return route.fulfill({
        contentType: 'text/csv; charset=utf-8',
        body: 'recorded_at,station,variable,semantic_key,value,unit\n',
      })
    },
  )
  return requests
}

function spanDays(url: URL): number {
  const from = Date.parse(url.searchParams.get('date_from')!)
  const to = Date.parse(url.searchParams.get('date_to')!)
  return Math.round((to - from) / DAY_MS)
}

function spanHours(url: URL): number {
  const from = Date.parse(url.searchParams.get('date_from')!)
  const to = Date.parse(url.searchParams.get('date_to')!)
  return Math.round((to - from) / 3_600_000)
}

test.describe('Estaciones meteorológicas', () => {
  // Served without the backend, so the spec holds without seeded users.
  test.use({ serviceWorkers: 'block' })

  test.beforeEach(async ({ page }) => {
    await stubSession(page)
    await stubStations(page)
  })

  test('el sidebar abre la lista con una tarjeta por estación y su estado en texto', async ({
    page,
  }) => {
    await gotoHydrated(page, '/dashboard')
    await page.getByRole('link', { name: T.navStations, exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`${LIST_PATH}$`))

    for (const [station, status] of [
      [STUB_STATIONS.online, T.stationStatusOnline],
      [STUB_STATIONS.stale, T.stationStatusStale],
    ] as const) {
      const card = page.getByRole('heading', { name: station.name, level: 2 })
        .locator('xpath=ancestor::*[@data-slot="root"][1]')
      await expect(card).toBeVisible()
      await expect(card.getByText(status, { exact: true })).toBeVisible()
    }

    await stubStationDetail(page)
    await page.getByRole('link', { name: `${T.stationDetailFor} ${STATION.name}` }).click()
    await expect(page).toHaveURL(new RegExp(`${DETAIL_PATH}$`))
    await expect(page.getByRole('heading', { name: STATION.name, level: 1 })).toBeVisible()
  })

  test('el detalle muestra las condiciones actuales, las gráficas y las lecturas', async ({
    page,
  }) => {
    await stubStationDetail(page)
    await gotoHydrated(page, DETAIL_PATH)

    const conditions = page.getByRole('region', { name: T.stationConditions })
    await expect(conditions.getByRole('heading', { name: 'Temperatura del aire' })).toBeVisible()
    await expect(conditions.getByText('24,5', { exact: false })).toBeVisible()
    await expect(conditions.getByRole('heading', { name: 'Humedad relativa' })).toBeVisible()

    const charts = page.getByRole('region', { name: T.stationCharts })
    await expect(charts.getByRole('figure')).toHaveCount(1)

    const readings = page.getByRole('region', { name: T.stationReadings })
    await expect(readings.locator('tbody tr')).toHaveCount(PAGE_SIZE)
  })

  test('cambiar el periodo pide la serie del nuevo rango y lo guarda en la URL', async ({
    page,
  }) => {
    const requests = await stubStationDetail(page)
    await gotoHydrated(page, DETAIL_PATH)
    await expect.poll(() => requests.series.length).toBe(1)
    expect(spanDays(requests.series[0]!)).toBe(1)

    const range = page.getByRole('group', { name: T.stationRange })
    await range.getByRole('button', { name: T.range7d }).click()

    await expect(page).toHaveURL(/range=7d/)
    await expect(range.getByRole('button', { name: T.range7d })).toHaveAttribute('aria-pressed', 'true')
    await expect.poll(() => requests.series.length).toBe(2)
    expect(spanDays(requests.series[1]!)).toBe(7)
    expect(spanDays(requests.readings.at(-1)!)).toBe(7)
  })

  test('los periodos cortos piden la serie de la última hora y de las últimas 6 horas', async ({
    page,
  }) => {
    const requests = await stubStationDetail(page)
    await gotoHydrated(page, DETAIL_PATH)
    await expect.poll(() => requests.series.length).toBe(1)

    const range = page.getByRole('group', { name: T.stationRange })
    for (const [label, hours] of [[T.range1h, 1], [T.range6h, 6]] as const) {
      const before = requests.series.length
      await range.getByRole('button', { name: label }).click()

      await expect(page).toHaveURL(new RegExp(`range=${hours}h`))
      await expect.poll(() => requests.series.length).toBe(before + 1)
      expect(spanHours(requests.series.at(-1)!)).toBe(hours)
    }
  })

  test('la tabla pagina de a 20 lecturas y guarda la página en la URL', async ({ page }) => {
    const requests = await stubStationDetail(page)
    await gotoHydrated(page, DETAIL_PATH)

    const readings = page.getByRole('region', { name: T.stationReadings })
    await expect(readings.locator('tbody tr')).toHaveCount(PAGE_SIZE)

    await readings.getByRole('button', { name: `${T.paginationPage} 3` }).click()

    await expect(page).toHaveURL(/page=3/)
    await expect(readings.locator('tbody tr')).toHaveCount(READING_COUNT - 2 * PAGE_SIZE)
    expect(requests.readings.at(-1)!.searchParams.get('page')).toBe('3')
  })

  test('exportar pide el CSV de la estación con el rango visible y descarga el archivo', async ({
    page,
  }) => {
    const requests = await stubStationDetail(page)
    await gotoHydrated(page, DETAIL_PATH)
    await expect(page.getByRole('region', { name: T.stationReadings }).locator('tbody tr')).toHaveCount(PAGE_SIZE)

    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: T.exportLabel }).click()
    await page.getByRole('menuitem', { name: T.exportCsv }).click()

    await expect.poll(() => requests.exports.length).toBe(1)
    const url = requests.exports[0]!
    expect(url.pathname).toMatch(new RegExp(`/api/sensors/stations/${STATION.id}/export/csv/$`))
    expect(spanDays(url)).toBe(1)
    // The export covers the whole range, so it carries no page.
    expect(url.searchParams.has('page')).toBe(false)
    expect((await download).suggestedFilename()).toMatch(
      /^historial-estacion-estacion-la-loma-\d{8}_\d{8}\.csv$/,
    )
  })

  test('una estación ajena o inexistente muestra el estado de no encontrada', async ({ page }) => {
    // stubSession answers every unstubbed endpoint with 404, as the backend
    // does for a station of another farmer.
    await gotoHydrated(page, `${LIST_PATH}/9999`)

    await expect(page.getByRole('heading', { name: T.stationNotFound }).first()).toBeVisible()
    await page.getByRole('link', { name: T.stationBackToList }).click()
    await expect(page).toHaveURL(new RegExp(`${LIST_PATH}$`))
  })

  test('la lista y el detalle no tienen violaciones graves de accesibilidad', async ({ page }) => {
    await stubStationDetail(page)

    await gotoHydrated(page, LIST_PATH)
    await expect(page.getByRole('heading', { name: STATION.name, level: 2 })).toBeVisible()
    const listResults = await new AxeBuilder({ page })
      .withTags(WCAG_TAGS)
      .include('[id$="-panel-sensors-stations"]')
      .analyze()
    expect(listResults.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical'))
      .toEqual([])

    await gotoHydrated(page, DETAIL_PATH)
    await expect(page.getByRole('region', { name: T.stationReadings }).locator('tbody tr')).toHaveCount(PAGE_SIZE)
    const detailResults = await new AxeBuilder({ page })
      .withTags(WCAG_TAGS)
      .include('[id$="-panel-sensors-station"]')
      .analyze()
    expect(detailResults.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical'))
      .toEqual([])
  })
})

test.describe('Actualización en vivo de las estaciones', () => {
  test.use({ serviceWorkers: 'block' })

  test('el detalle vuelve a pedir la estación, la serie y la primera página tras el intervalo', async ({
    page,
  }) => {
    await page.clock.install()
    await stubSession(page)
    const requests = await stubStationDetail(page)

    await gotoHydrated(page, DETAIL_PATH)
    await expect(page.getByRole('region', { name: T.stationReadings }).locator('tbody tr')).toHaveCount(PAGE_SIZE)
    await expect.poll(() => requests.series.length).toBe(1)
    const before = { station: requests.station, readings: requests.readings.length }

    await page.clock.fastForward(LIVE_REFRESH_MS)

    await expect.poll(() => requests.series.length).toBe(2)
    await expect.poll(() => requests.station).toBeGreaterThan(before.station)
    await expect.poll(() => requests.readings.length).toBeGreaterThan(before.readings)
    // The polled window slides to the moment of the poll.
    expect(Date.parse(requests.series[1]!.searchParams.get('date_to')!)).toBeGreaterThan(
      Date.parse(requests.series[0]!.searchParams.get('date_to')!),
    )
  })

  test('la lista vuelve a pedir las estaciones tras el intervalo', async ({ page }) => {
    await page.clock.install()
    await stubSession(page)
    const stations = await stubStations(page)

    await gotoHydrated(page, LIST_PATH)
    await expect(page.getByRole('heading', { name: STATION.name, level: 2 })).toBeVisible()
    const before = stations.requests

    await page.clock.fastForward(LIVE_REFRESH_MS)

    await expect.poll(() => stations.requests).toBeGreaterThan(before)
  })
})
