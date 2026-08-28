import { test, expect } from '@playwright/test'
import { loginAs, selectFarm, statCardValue, T } from './helpers'

/** Plot counts of the seeded farms, as shown by the "Lotes" stat card. */
const PLOTS_FIRST = '3'
const PLOTS_SECOND = '2'

test.describe('Selector de fincas', () => {
  test('el dashboard muestra los lotes de la finca seleccionada por defecto', async ({
    page,
  }) => {
    await loginAs(page)

    // Farms are ordered by name, so the first one is selected on load.
    await expect(page.getByRole('button', { name: T.farmFirst })).toBeVisible()
    await expect(statCardValue(page, T.statPlots)).toHaveText(PLOTS_FIRST)
  })

  test('cambiar de finca pide los lotes de la nueva finca y actualiza el panel', async ({
    page,
  }) => {
    await loginAs(page)
    await expect(statCardValue(page, T.statPlots)).toHaveText(PLOTS_FIRST)

    await selectFarm(page, T.farmSecond)

    await expect(page.getByRole('button', { name: T.farmSecond })).toBeVisible()
    await expect(page.getByText(T.farmSecond).first()).toBeVisible()
    // The seeded farms hold a different number of plots, so the count itself
    // proves the panel was refetched for the newly selected farm.
    await expect(statCardValue(page, T.statPlots)).toHaveText(PLOTS_SECOND)
  })

  test('la finca seleccionada persiste tras recargar', async ({ page }) => {
    await loginAs(page)
    await expect(page.getByRole('button', { name: T.farmFirst })).toBeVisible()

    await selectFarm(page, T.farmSecond)
    await expect(page.getByRole('button', { name: T.farmSecond })).toBeVisible()

    await page.reload()
    await expect(page.getByRole('button', { name: T.farmSecond })).toBeVisible()
    await expect(statCardValue(page, T.statPlots)).toHaveText(PLOTS_SECOND)
  })

  test('si la carga de lotes falla, aparece el fallback de error y Reintentar recupera', async ({
    page,
  }) => {
    await page.route('**/farm/farms/*/plots/', (route) => route.abort())
    await loginAs(page)

    // Text-based fallback (not colour/icon alone) + a labeled Retry control.
    // "Reintentar" also labels the retry of each weather card, so the button is
    // located inside the plots alert rather than by name alone.
    const plotsAlert = page
      .getByRole('alert')
      .filter({ hasText: T.plotsLoadError })
    await expect(plotsAlert).toBeVisible()

    await page.unroute('**/farm/farms/*/plots/')
    await plotsAlert.getByRole('button', { name: T.retry }).click()
    await expect(statCardValue(page, T.statPlots)).toHaveText(PLOTS_FIRST)
  })

  test('si la carga de fincas falla, el sidebar muestra el fallback y Reintentar recupera', async ({
    page,
  }) => {
    await page.route('**/farm/farms/', (route) => route.abort())
    await loginAs(page)

    await expect(
      page.getByText(T.farmsUnavailable, { exact: true }),
    ).toBeVisible()

    await page.unroute('**/farm/farms/')
    await page.getByRole('button', { name: T.retry }).first().click()
    await expect(page.getByRole('button', { name: T.farmFirst })).toBeVisible()
  })
})
