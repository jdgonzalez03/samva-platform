import { test, expect } from '@playwright/test'
import {
  gotoHydrated,
  LIVE_REFRESH_MS,
  loginAs,
  STUB_FARM,
  STUB_PLOT,
  STUB_STATIONS,
  statCardValue,
  stubSession,
  stubStations,
  T,
} from './helpers'

test.describe('Sidebar del dashboard', () => {
  test('el menú de usuario sin foto muestra las iniciales sin ensuciar su nombre accesible', async ({
    page,
  }) => {
    // The seeded farmer's avatar column is not stable across environments, so
    // the photoless state is forced on the response the sidebar reads.
    await page.route('**/accounts/me/', async (route) => {
      const response = await route.fetch()
      const body = await response.json()
      body.farmer.avatar = null
      await route.fulfill({ response, json: body })
    })

    await loginAs(page)
    await gotoHydrated(page, '/dashboard')

    const trigger = page.getByRole('button', { name: T.userMenu })
    await expect(trigger).toBeVisible()
    await expect(trigger).toContainText(T.userInitials)
    // The avatar is aria-hidden: the label alone names the control.
    await expect(trigger).toHaveAccessibleName(T.userDisplayName)
  })
})

test.describe('Mapa del dashboard', () => {
  test('el mapa base de calles carga tiles de OpenStreetMap y muestra su atribución', async ({
    page,
  }) => {
    // Tiles are stubbed so the spec never depends on (or loads) the real tile
    // server; recording the requests still proves which provider the map asks.
    const tileRequests: string[] = []
    await page.route('https://tile.openstreetmap.org/**', (route) => {
      tileRequests.push(route.request().url())
      return route.fulfill({ contentType: 'image/png', body: Buffer.alloc(0) })
    })

    await loginAs(page)
    await gotoHydrated(page, '/dashboard')

    const map = page.getByRole('region', { name: T.mapRegion })
    await expect(
      map.getByRole('link', { name: T.osmAttribution }),
    ).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright')
    await expect.poll(() => tileRequests.length).toBeGreaterThan(0)
  })
})

const PLOT_ID = 1

// Readings stamped relative to the run, so "Reportando" and the relative times
// hold on any day; the seed's own readings would age out.
function stubOverview(moisture = 12) {
  const now = Date.now()
  const hourly = Array.from({ length: 48 }, (_, index) => ({
    t: new Date(Math.floor(now / 3_600_000 - 47 + index) * 3_600_000).toISOString(),
    value: 20 + (index % 12),
    sample_count: 12,
  }))
  return {
    generated_at: new Date(now).toISOString(),
    conditions: [
      {
        semantic_key: 'soil_moisture',
        name: 'Humedad del suelo',
        unit: '%',
        value: moisture,
        recorded_at: new Date(now - 5 * 60_000).toISOString(),
        change_24h: -6,
        level: 'low',
        level_degrees: { low: 1, medium: 0, high: 0 },
      },
    ],
    series: [
      {
        variable_id: 4,
        semantic_key: 'soil_moisture',
        name: 'Humedad del suelo',
        unit: '%',
        bucket_seconds: 3600,
        points: hourly,
      },
    ],
    sensors: [
      {
        id: 1,
        name: 'Sensor 1',
        serial_number: 'SEED-0001',
        is_active: true,
        installed_at: null,
        last_seen_at: new Date(now - 5 * 60_000).toISOString(),
        status: 'online',
        variables: [{ semantic_key: 'soil_moisture', name: 'Humedad del suelo', unit: '%' }],
      },
    ],
    irrigation: null,
  }
}

test.describe('Detalle del lote', () => {
  test('muestra el estado, las condiciones con su nivel y tendencia, el mapa de calor y los sensores', async ({
    page,
  }) => {
    await page.route('**/farm/plots/*/overview/', (route) =>
      route.fulfill({ json: stubOverview() }),
    )
    await loginAs(page)
    await gotoHydrated(page, `/dashboard/plots/${PLOT_ID}`)

    await expect(page.getByRole('heading', { name: T.plotName, level: 1 })).toBeVisible()
    await expect(page.getByText(T.plotLive)).toBeVisible()

    const conditions = page.getByRole('region', { name: T.plotConditionsTitle })
    await expect(conditions.getByText(T.plotMoistureLevel)).toBeVisible()
    await expect(conditions.getByText(T.plotMoistureChange)).toBeVisible()

    await expect(page.getByRole('heading', { name: T.plotHeatmapTitle })).toBeVisible()
    await expect(page.getByText(T.plotSensorOnline)).toBeVisible()
    await expect(
      page.getByRole('link', { name: T.plotIrrigationCalculate }),
    ).toHaveAttribute('href', `/dashboard/predictions/fuzzy?plot=${PLOT_ID}`)
  })

  test('si el resumen falla, muestra el error y Reintentar lo recupera', async ({ page }) => {
    await page.route('**/farm/plots/*/overview/', (route) => route.abort())
    await loginAs(page)
    await gotoHydrated(page, `/dashboard/plots/${PLOT_ID}`)

    const alert = page.getByRole('alert').filter({ hasText: T.plotOverviewError })
    await expect(alert).toBeVisible()

    await page.unroute('**/farm/plots/*/overview/')
    await page.route('**/farm/plots/*/overview/', (route) =>
      route.fulfill({ json: stubOverview() }),
    )
    await alert.getByRole('button', { name: T.retry }).click()

    await expect(page.getByText(T.plotMoistureLevel)).toBeVisible()
  })
})

test.describe('Actualización en vivo del detalle del lote', () => {
  // Served without the backend, so the spec holds without seeded users.
  test.use({ serviceWorkers: 'block' })

  test('vuelve a pedir el resumen tras el intervalo y reemplaza los datos sin mostrar el skeleton', async ({
    page,
  }) => {
    await page.clock.install()
    await stubSession(page)
    let overviewRequests = 0
    let moisture = 12.3
    await page.route(
      (url) => url.pathname.endsWith(`/farm/plots/${STUB_PLOT.id}/overview/`),
      (route) => {
        overviewRequests += 1
        return route.fulfill({ json: stubOverview(moisture) })
      },
    )

    await gotoHydrated(page, `/dashboard/plots/${STUB_PLOT.id}`)
    const conditions = page.getByRole('region', { name: T.plotConditionsTitle })
    await expect(conditions.getByText(T.liveMoistureBefore, { exact: true })).toBeVisible()
    expect(overviewRequests).toBe(1)

    // A skeleton in between would unmount the section and mount a new one.
    const section = await conditions.elementHandle()
    moisture = 31.7
    await page.clock.fastForward(LIVE_REFRESH_MS)

    await expect.poll(() => overviewRequests).toBe(2)
    await expect(conditions.getByText(T.liveMoistureAfter, { exact: true })).toBeVisible()
    await expect(conditions.getByText(T.liveMoistureBefore, { exact: true })).toHaveCount(0)
    expect(await section!.evaluate((node) => node.isConnected)).toBe(true)
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0)
  })
})

// Seed: Finca El Tesoro (farm 1) holds plots 1 "Lote La Colina" and 2 "Lote El
// Abrevadero". Readings are stamped relative to the run so freshness holds.
function stubFarmOverview() {
  const now = Date.now()
  const minutesAgo = (minutes: number) => new Date(now - minutes * 60_000).toISOString()
  const moisture = (value: number, level: string, minutes: number) => ({
    semantic_key: 'soil_moisture',
    name: 'Humedad del suelo',
    unit: '%',
    value,
    recorded_at: minutesAgo(minutes),
    change_24h: -2,
    level,
    level_degrees: null,
  })
  const sensor = (id: number, plotId: number, status: string) => ({
    id,
    name: `Sensor ${id}`,
    serial_number: `SN-${id}`,
    plot_id: plotId,
    plot_name: plotId === 1 ? 'Lote La Colina' : 'Lote El Abrevadero',
    is_active: true,
    installed_at: null,
    last_seen_at: status === 'online' ? minutesAgo(5) : null,
    status,
    variables: [],
  })
  return {
    generated_at: new Date(now).toISOString(),
    conditions: [moisture(18, 'medium', 5)],
    series: [],
    plots: [
      {
        id: 2,
        name: 'Lote El Abrevadero',
        latest_reading_at: minutesAgo(5),
        conditions: [moisture(9, 'low', 5)],
        series: [],
        irrigation: {
          id: 1,
          irrigation_time_minutes: 12.5,
          output_label: 'little',
          avg_period_hours: 6,
          requested_at: minutesAgo(30),
        },
      },
      {
        id: 1,
        name: 'Lote La Colina',
        latest_reading_at: minutesAgo(180),
        conditions: [moisture(27, 'medium', 180)],
        series: [],
        irrigation: null,
      },
    ],
    sensors: [sensor(1, 2, 'online'), sensor(2, 1, 'never_seen')],
  }
}

test.describe('Dashboard de la finca', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/farm/farms/*/overview/', (route) =>
      route.fulfill({ json: stubFarmOverview() }),
    )
    await loginAs(page)
  })

  test('las tarjetas resumen cuentan sensores en línea y alertas', async ({ page }) => {
    await expect(statCardValue(page, T.homeSensorsOnline)).toHaveText(T.homeSensorsValue)
    // Dry soil, a stale plot, a plot without irrigation and a sensor that never reported.
    await expect(statCardValue(page, T.homeAlerts)).toHaveText('4')
  })

  test('"Necesita atención" prioriza el suelo seco y enlaza al lote', async ({ page }) => {
    const attention = page
      .getByRole('heading', { name: new RegExp(T.homeAttention) })
      .locator('xpath=ancestor::*[@data-slot="root"][1]')
    const links = attention.getByRole('link')

    await expect(links.first()).toContainText(T.homeDryAlert)
    await expect(links.first()).toHaveAttribute('href', '/dashboard/plots/2')
    await expect(attention.getByText(T.homeStaleAlert)).toBeVisible()
  })

  test('el ranking ordena los lotes del más seco al más húmedo', async ({ page }) => {
    const ranking = page
      .getByRole('heading', { name: T.homeRankingTitle, exact: true })
      .locator('xpath=ancestor::*[@data-slot="root"][1]')

    await expect(ranking.getByRole('link').first()).toHaveAttribute('href', '/dashboard/plots/2')
    await expect(ranking.getByRole('link').nth(1)).toHaveAttribute('href', '/dashboard/plots/1')
  })

  test('el riego suma los minutos recomendados de la finca', async ({ page }) => {
    await expect(page.getByText(T.homeIrrigationTotal)).toBeVisible()
    await expect(
      page.getByRole('region', { name: T.homeFarmConditions }).getByText('18'),
    ).toBeVisible()
  })
})

test.describe('Estaciones en el dashboard', () => {
  // Served without the backend, so the spec holds without seeded users.
  test.use({ serviceWorkers: 'block' })

  test.beforeEach(async ({ page }) => {
    await stubSession(page)
  })

  test('muestra una tarjeta por estación con su estado en texto y "Ver detalle" abre la estación', async ({
    page,
  }) => {
    await stubStations(page)
    await gotoHydrated(page, '/dashboard')

    const section = page.getByRole('region', { name: T.stationsTitle })
    for (const [station, status] of [
      [STUB_STATIONS.online, T.stationStatusOnline],
      [STUB_STATIONS.stale, T.stationStatusStale],
    ] as const) {
      const card = section
        .getByRole('heading', { name: station.name })
        .locator('xpath=ancestor::*[@data-slot="root"][1]')
      await expect(card.getByText(status, { exact: true })).toBeVisible()
      await expect(card.getByText('Temperatura del aire', { exact: true })).toBeVisible()
    }

    await section
      .getByRole('link', { name: `${T.stationDetailFor} ${STUB_STATIONS.online.name}` })
      .click()
    await expect(page).toHaveURL(new RegExp(`/dashboard/stations/${STUB_STATIONS.online.id}$`))
  })

  test('una finca sin estaciones muestra el estado vacío', async ({ page }) => {
    await page.route(
      (url) => url.pathname.endsWith(`/api/sensors/farms/${STUB_FARM.id}/stations/`),
      (route) => route.fulfill({ json: [] }),
    )
    await gotoHydrated(page, '/dashboard')

    await expect(
      page.getByRole('region', { name: T.stationsTitle }).getByText(T.stationsEmpty),
    ).toBeVisible()
  })
})

// Seed names, stats stubbed: Finca El Tesoro holds plots 1 and 2, Finca San
// Vicente holds plot 3.
function stubPlotSummaries() {
  const now = Date.now()
  const plot = (id: number, name: string, farm: { id: number; name: string }, moisture: number | null) => ({
    id,
    name,
    description: '',
    area_hectares: '4.94',
    sensor_count: 2,
    has_geometry: true,
    farm,
    latest_reading_at: moisture === null ? null : new Date(now - 5 * 60_000).toISOString(),
    conditions:
      moisture === null
        ? []
        : [
            {
              semantic_key: 'soil_moisture',
              name: 'Humedad del suelo',
              unit: '%',
              value: moisture,
              recorded_at: new Date(now - 5 * 60_000).toISOString(),
              change_24h: null,
              level: 'low',
              level_degrees: null,
            },
          ],
    irrigation:
      id === 2
        ? {
            id: 7,
            irrigation_time_minutes: 12.5,
            output_label: 'little',
            avg_period_hours: 6,
            requested_at: new Date(now - 60_000).toISOString(),
          }
        : null,
  })
  const tesoro = { id: 1, name: T.farmFirst }
  const vicente = { id: 2, name: T.farmSecond }
  return [
    plot(2, T.plotAbrevadero, tesoro, 9),
    plot(1, T.plotName, tesoro, null),
    plot(3, T.plotManantial, vicente, 30),
  ]
}

test.describe('Mis lotes', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/farm/plots/', (route) => route.fulfill({ json: stubPlotSummaries() }))
    await loginAs(page)
  })

  test('el sidebar abre la página con una tarjeta por lote y sus datos', async ({ page }) => {
    await page.getByRole('link', { name: T.navPlots }).click()

    await expect(page).toHaveURL(/\/dashboard\/plots$/)
    await expect(page.getByText(T.plotsIndexSummary)).toBeVisible()
    const card = page.getByRole('link', { name: T.plotAbrevadero }).locator('..')
    await expect(card).toContainText(T.farmFirst)
    await expect(card).toContainText(T.plotsMoistureValue)
    await expect(card).toContainText(T.plotsIrrigationBadge)
  })

  test('filtrar por finca y buscar por nombre reduce las tarjetas', async ({ page }) => {
    await gotoHydrated(page, `/dashboard/plots?farm=2`)
    await expect(page.getByText(T.plotManantial, { exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: T.plotName })).toHaveCount(0)

    await gotoHydrated(page, `/dashboard/plots?q=colina`)
    await expect(page.getByText(T.plotName, { exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: T.plotAbrevadero })).toHaveCount(0)

    await page.getByRole('textbox', { name: T.plotsSearch }).fill('zzz')
    await expect(page.getByText(T.plotsNoMatches)).toBeVisible()
    await page.getByRole('button', { name: T.plotsClearFilters }).click()
    await expect(page.getByText(T.plotManantial, { exact: true })).toBeVisible()
  })

  test('la tarjeta lleva al detalle del lote', async ({ page }) => {
    await gotoHydrated(page, '/dashboard/plots')

    // UPageCard's `<a>` has no box of its own, so Enter follows it as a
    // keyboard user would.
    await page.getByRole('link', { name: T.plotName }).press('Enter')

    await expect(page).toHaveURL(/\/dashboard\/plots\/1$/)
  })
})

