import { test, expect } from '@playwright/test'

test.describe('Página principal /', () => {
  test('carga sin errores', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (err) => errors.push(err.message))

    await page.goto('/')
    await expect(page.locator('body')).toBeVisible()
    expect(errors).toEqual([])
  })

  test('el header se renderiza con botón Ir al Dashboard', async ({ page }) => {
    await page.goto('/')
    const btn = page.getByRole('link', { name: /ir al dashboard/i })
    await expect(btn).toBeVisible()
  })

  test('el hero section es visible con título de agricultura de precisión', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(/agricultura de precisión/i)).toBeVisible()
  })

  test('la sección visión y misión es visible', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(/nuestra visión/i)).toBeVisible()
    await expect(page.getByText(/nuestra misión/i)).toBeVisible()
  })

  test('el footer se renderiza con texto S.A.M.V.A.', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(/s\.a\.m\.v\.a/i)).toBeVisible()
  })

  test('el botón Ir al Dashboard navega a /dashboard', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /ir al dashboard/i }).click()
    await expect(page).toHaveURL(/\/dashboard/)
  })
})
