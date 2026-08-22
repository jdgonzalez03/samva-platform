import { test, expect, type Page } from '@playwright/test'
import { gotoHydrated, loginAs, T } from './helpers'

/**
 * Opens the sidebar farm switcher and picks a farm. The dropdown overlay
 * aria-hides the rest of the page while open, so it must be dismissed before
 * anything in the background can be located again.
 */
async function selectFarm(page: Page, farmName: string): Promise<void> {
  await page.getByRole('button', { name: T.farmFirst }).click()
  await page.getByRole('menuitemcheckbox', { name: farmName }).click()
  await page.keyboard.press('Escape')
}

test.describe('Selector de fincas', () => {
  test('el dashboard muestra los lotes de la finca seleccionada por defecto', async ({
    page,
  }) => {
    await loginAs(page)

    // Farms are ordered by name, so the first one is selected on load.
    await expect(page.getByRole('button', { name: T.farmFirst })).toBeVisible()
    await expect(page.getByText(T.plotCount, { exact: true })).toBeVisible()
  })

  test('cambiar de finca pide los lotes de la nueva finca y actualiza el panel', async ({
    page,
  }) => {
    // Both seeded farms have 2 plots, so the count alone cannot prove the
    // refetch — record which farm's plots were requested.
    const plotsUrls: string[] = []
    page.on('request', (request) => {
      if (/\/farm\/farms\/\d+\/plots\/$/.test(request.url()))
        plotsUrls.push(request.url())
    })

    await loginAs(page)
    await expect(page.getByText(T.plotCount, { exact: true })).toBeVisible()

    await selectFarm(page, T.farmSecond)

    await expect(page.getByRole('button', { name: T.farmSecond })).toBeVisible()
    await expect(page.getByText(T.farmSecond).first()).toBeVisible()
    await expect(page.getByText(T.plotCount, { exact: true })).toBeVisible()
    await expect
      .poll(() => new Set(plotsUrls).size)
      .toBeGreaterThan(1)
  })

  test('la finca seleccionada persiste tras recargar', async ({ page }) => {
    await loginAs(page)
    await expect(page.getByRole('button', { name: T.farmFirst })).toBeVisible()

    await selectFarm(page, T.farmSecond)
    await expect(page.getByRole('button', { name: T.farmSecond })).toBeVisible()

    await page.reload()
    await expect(page.getByRole('button', { name: T.farmSecond })).toBeVisible()
    await expect(page.getByText(T.plotCount, { exact: true })).toBeVisible()
  })

  test('si la carga de lotes falla, aparece el fallback de error y Reintentar recupera', async ({
    page,
  }) => {
    await page.route('**/farm/farms/*/plots/', (route) => route.abort())
    await loginAs(page)

    // Text-based fallback (not colour/icon alone) + a labeled Retry control.
    await expect(
      page.getByText(T.plotsLoadError, { exact: true }),
    ).toBeVisible()

    await page.unroute('**/farm/farms/*/plots/')
    await page.getByRole('button', { name: T.retry }).click()
    await expect(page.getByText(T.plotCount, { exact: true })).toBeVisible()
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
