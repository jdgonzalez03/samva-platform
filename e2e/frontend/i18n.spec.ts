import { test, expect } from '@playwright/test'
import { gotoHydrated, loginAs, E2E_USER, T, T_EN, SWITCHER } from './helpers'

test.describe('Internacionalización (es/en)', () => {
  test('el switcher del login cambia a inglés: URL /en/login, textos y <html lang>', async ({
    page,
  }) => {
    await gotoHydrated(page, '/login')
    await expect(page.locator('html')).toHaveAttribute('lang', /^es/)

    await page.getByRole('button', { name: SWITCHER.loginTrigger }).click()
    await page.getByRole('menuitemcheckbox', { name: SWITCHER.english }).click()

    await expect(page).toHaveURL(/\/en\/login/)
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
    // The document title follows the new language too (AC-A11Y-3).
    await expect(page).toHaveTitle(new RegExp(T_EN.loginTitle))
    await expect(page.getByText(T_EN.loginHeading).first()).toBeVisible()
    await expect(page.getByRole('button', { name: T_EN.signIn })).toBeVisible()
  })

  test('el switcher del login es operable con teclado y devuelve el foco', async ({
    page,
  }) => {
    await gotoHydrated(page, '/login')
    const trigger = page.getByRole('button', { name: SWITCHER.loginTrigger })
    await trigger.focus()
    await page.keyboard.press('Enter')

    const options = page.getByRole('menuitemcheckbox')
    await expect(options).toHaveCount(2)
    // The current language is exposed as checked (aria-checked).
    await expect(
      page.getByRole('menuitemcheckbox', { name: SWITCHER.spanish }),
    ).toHaveAttribute('aria-checked', 'true')

    // Arrow keys move between the language options.
    await page.keyboard.press('ArrowDown')
    await expect(
      page.getByRole('menuitemcheckbox', { name: SWITCHER.english }),
    ).toBeFocused()

    await page.keyboard.press('Escape')
    await expect(options).toHaveCount(0)
    await expect(trigger).toBeFocused()
  })

  test('login en /en/login conserva el prefijo: redirige a /en/dashboard', async ({
    page,
  }) => {
    await gotoHydrated(page, '/en/login')
    await page.locator('input[type="email"]').fill(E2E_USER.email)
    await page.locator('input[type="password"]').fill(E2E_USER.password)
    await page.locator('button[type="submit"]').click()
    await expect(page).toHaveURL(/\/en\/dashboard/)
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  })

  test('el submenú Idioma del dashboard cambia idioma y URL, y persiste tras recargar', async ({
    page,
  }) => {
    await loginAs(page)

    await page.getByRole('button', { name: T.userMenu }).click()
    await page.getByRole('menuitem', { name: SWITCHER.dashboardSubmenu }).click()
    await page.getByRole('menuitemcheckbox', { name: SWITCHER.english }).click()

    await expect(page).toHaveURL(/\/en\/dashboard/)
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
    // The menu stays open (its strings switch in place); the user menu now
    // shows the English logout entry. Close it to reach the sidebar links.
    await expect(page.getByRole('menuitem', { name: T_EN.logout })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('link', { name: T_EN.profileLink })).toBeVisible()

    // The choice persists across a full reload (URL prefix + strings).
    await page.reload()
    await expect(page).toHaveURL(/\/en\/dashboard/)
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
    await expect(page.getByRole('link', { name: T_EN.profileLink })).toBeVisible()

    // Cookie persistence: the root URL now redirects to the chosen locale.
    await page.goto('/')
    await expect(page).toHaveURL(/\/en\/?$/)
  })

  test('la fecha "Miembro desde" del perfil se formatea según el locale activo', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, '/en/dashboard/profile')

    // en: "Member since <Month YYYY>" with an English month name (a
    // hardcoded locale would fail this or the Spanish assertion below).
    await expect(
      page
        .getByText(
          /Member since\s+(January|February|March|April|May|June|July|August|September|October|November|December) \d{4}/,
        )
        .first(),
    ).toBeVisible()

    await gotoHydrated(page, '/dashboard/profile')
    await expect(
      page
        .getByText(
          /Miembro desde\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) de \d{4}/i,
        )
        .first(),
    ).toBeVisible()
  })

  test('/en muestra la landing en español sin errores', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (err) => errors.push(err.message))

    await page.goto('/en')
    await expect(page.getByText(/agricultura de precisión/i).first()).toBeVisible()
    await expect(page.getByRole('link', { name: /ir al dashboard/i })).toBeVisible()
    expect(errors).toEqual([])
  })

  test('logout desde /en/dashboard conserva el prefijo: vuelve a /en/login', async ({
    page,
  }) => {
    await gotoHydrated(page, '/en/login')
    await page.locator('input[type="email"]').fill(E2E_USER.email)
    await page.locator('input[type="password"]').fill(E2E_USER.password)
    await page.locator('button[type="submit"]').click()
    await expect(page).toHaveURL(/\/en\/dashboard/)

    await page.getByRole('button', { name: T.userMenu }).click()
    await page.getByRole('menuitem', { name: T_EN.logout }).click()
    await expect(page).toHaveURL(/\/en\/login/)
  })
})

test.describe('Detección del idioma del navegador', () => {
  // Fresh en-US context (overrides the project's es-CO pin): first visit to
  // the root must detect the browser language, redirect, and set the cookie.
  test.use({ locale: 'en-US' })

  test('primera visita con navegador en inglés redirige a /en y persiste la cookie', async ({
    page,
  }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/en\/?$/)
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')

    const cookie = (await page.context().cookies()).find(
      (c) => c.name === 'i18n_redirected',
    )
    expect(cookie?.value).toBe('en')
  })
})
