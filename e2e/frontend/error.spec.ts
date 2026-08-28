import { test, expect } from '@playwright/test'
import { gotoHydrated, T, T_EN } from './helpers'

/**
 * A path no route matches. It is deliberately not under `/dashboard`: those
 * paths now resolve to real pages, and an authenticated area would redirect to
 * the login form instead of rendering the 404.
 */
const MISSING_PATH = '/pagina-inexistente'

test.describe('Página de error (error.vue)', () => {
  test('ruta inexistente en español: 404 con título, encabezado y enlace al inicio operable con teclado', async ({
    page,
  }) => {
    await gotoHydrated(page, MISSING_PATH)

    await expect(page).toHaveTitle(new RegExp(T.errorTitle))
    await expect(page.locator('html')).toHaveAttribute('lang', /^es/)
    await expect(
      page.getByRole('heading', { level: 1, name: T.errorHeading }),
    ).toBeVisible()

    // Keyboard operability: the back-home control is focusable and Enter
    // activates it, navigating back to the Spanish home.
    const backHome = page.getByRole('button', { name: T.backHome })
    await backHome.focus()
    await expect(backHome).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/^https?:\/\/[^/]+\/$/)
  })

  test('ruta inexistente en inglés: textos traducidos y el enlace al inicio conserva /en', async ({
    page,
  }) => {
    await gotoHydrated(page, `/en${MISSING_PATH}`)

    await expect(page).toHaveTitle(new RegExp(T_EN.errorTitle))
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
    await expect(
      page.getByRole('heading', { level: 1, name: T_EN.errorHeading }),
    ).toBeVisible()

    const backHome = page.getByRole('button', { name: T_EN.backHome })
    await backHome.focus()
    await expect(backHome).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/en\/?$/)
  })
})
