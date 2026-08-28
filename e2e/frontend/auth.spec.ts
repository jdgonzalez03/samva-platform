import { test, expect } from '@playwright/test'
import { gotoHydrated, loginAs, E2E_USER, T } from './helpers'

test.describe('Autenticación', () => {
  test('login con credenciales válidas redirige a /dashboard con toast de éxito', async ({
    page,
  }) => {
    await loginAs(page)
    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByText(T.loginSuccessToast, { exact: true })).toBeVisible()
    // The toast fires inside a live region so it is announced (AC-A11Y-6).
    await expect(
      page
        .getByRole('alert')
        .or(page.getByRole('status'))
        .filter({ hasText: T.loginSuccessToast }),
    ).toBeVisible()
    // The sidebar links to the history page; predictions have no page yet.
    await expect(
      page.getByRole('link', { name: T.navHistory, exact: true }),
    ).toHaveAttribute('href', '/dashboard/history')
    await expect(page.getByRole('link', { name: /predic/i })).toHaveCount(0)
  })

  test('la validación del email expone el error traducido vía aria-invalid y aria-describedby', async ({
    page,
  }) => {
    await gotoHydrated(page, '/login')
    const email = page.locator('input[type="email"]')
    await email.fill('no-es-un-correo')
    await page.locator('button[type="submit"]').click()

    // Translated zod message rendered as text (not colour alone)…
    await expect(
      page.getByText(T.emailValidation, { exact: true }),
    ).toBeVisible()
    // …and programmatically linked to the field.
    await expect(email).toHaveAttribute('aria-invalid', 'true')
    const describedby = (await email.getAttribute('aria-describedby')) ?? ''
    expect(describedby).not.toBe('')
    const referenced = await Promise.all(
      describedby
        .split(/\s+/)
        .filter(Boolean)
        .map((id) =>
          page
            .locator(`[id="${id}"]`)
            .innerText()
            .catch(() => ''),
        ),
    )
    expect(referenced.join(' ')).toContain(T.emailValidation)
  })

  test('login con credenciales inválidas muestra toast de error y permanece en /login', async ({
    page,
  }) => {
    await gotoHydrated(page, '/login')
    await page.locator('input[type="email"]').fill(E2E_USER.email)
    await page.locator('input[type="password"]').fill('definitely-wrong-password')
    await page.locator('button[type="submit"]').click()
    await expect(page.getByText(T.loginErrorToast, { exact: true })).toBeVisible()
    await expect(page).toHaveURL(/\/login/)
  })

  test('logout desde el dropdown de usuario vuelve a /login y limpia tokens', async ({
    page,
  }) => {
    await loginAs(page)
    await page.getByRole('button', { name: T.userMenu }).click()
    await page.getByRole('menuitem', { name: T.logout }).click()
    await expect(page).toHaveURL(/\/login/)
    const tokens = await page.evaluate(() => ({
      access: localStorage.getItem('accessToken'),
      refresh: localStorage.getItem('refreshToken'),
    }))
    expect(tokens.access).toBeNull()
    expect(tokens.refresh).toBeNull()
  })

  test('visita anónima directa a /dashboard redirige a /login', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
  })

  test('visita anónima directa a /dashboard/profile redirige a /login', async ({
    page,
  }) => {
    await page.goto('/dashboard/profile')
    await expect(page).toHaveURL(/\/login/)
  })

  test('usuario autenticado que visita /login es redirigido a /dashboard', async ({
    page,
  }) => {
    await loginAs(page)
    await page.goto('/login')
    await expect(page).toHaveURL(/\/dashboard/)
  })
})
