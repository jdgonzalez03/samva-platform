import { readFileSync } from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { gotoHydrated, loginAs, selectFarm, T } from './helpers'

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
