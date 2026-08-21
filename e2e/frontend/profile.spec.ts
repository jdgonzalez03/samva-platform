import { test, expect } from '@playwright/test'
import { gotoHydrated, loginAs, E2E_USER, T } from './helpers'

test.describe('Perfil de usuario', () => {
  test('editar el nombre lo guarda, persiste tras recargar y se restaura', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/profile')

    const firstName = page.getByRole('textbox', { name: T.firstName })
    const saveButton = page.getByRole('button', { name: T.saveChanges })
    const successToast = page.getByText(T.profileUpdatedToast, { exact: true })

    // The form fills asynchronously once the profile query resolves.
    await expect(firstName).not.toHaveValue('')
    const original = await firstName.inputValue()
    const edited = `${original} E2E`

    await firstName.fill(edited)
    await saveButton.click()
    await expect(successToast).toBeVisible()

    // Persistence: the saved value survives a full reload.
    await page.reload()
    await expect(firstName).toHaveValue(edited)

    // Restore the original value so the spec stays idempotent.
    await firstName.fill(original)
    await saveButton.click()
    await expect(successToast.first()).toBeVisible()
    await page.reload()
    await expect(firstName).toHaveValue(original)
  })

  test('el control de avatar es alcanzable con Tab, con nombre accesible y anillo de foco', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/profile')

    const firstName = page.getByRole('textbox', { name: T.firstName })
    await expect(firstName).not.toHaveValue('')

    // The sr-only file input is exposed as a button with its aria-label.
    const avatarInput = page.getByRole('button', { name: T.changeAvatar })
    await expect(avatarInput).toHaveAccessibleName(T.changeAvatar)

    // Keyboard reachability: a bounded Tab walk from the document start must
    // land on the control (it follows the sidebar focusables in tab order).
    await page.evaluate(() => (document.activeElement as HTMLElement)?.blur())
    let reached = false
    for (let i = 0; i < 25; i++) {
      await page.keyboard.press('Tab')
      if (await avatarInput.evaluate((el) => el === document.activeElement)) {
        reached = true
        break
      }
    }
    expect(reached, 'Tab nunca llegó al input de avatar').toBe(true)
    await expect(avatarInput).toBeFocused()

    // Visible focus indicator: the wrapping label paints a ring
    // (focus-within box-shadow) while the input holds focus.
    const ring = await avatarInput.evaluate(
      (el) => getComputedStyle(el.closest('label')!).boxShadow,
    )
    expect(ring).not.toBe('none')
  })

  test('si la recarga del perfil falla, aparece el fallback de error y Reintentar recupera', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/profile')

    const firstName = page.getByRole('textbox', { name: T.firstName })
    await expect(firstName).not.toHaveValue('')

    // Fail only profile reads: the PATCH save must succeed so its cache
    // invalidation triggers the failing refetch (Vue Query error state).
    await page.route('**/accounts/me/', (route) =>
      route.request().method() === 'GET' ? route.abort() : route.continue(),
    )
    await page.getByRole('button', { name: T.saveChanges }).click()

    // Text-based fallback (not colour/icon alone) + a labeled Retry control.
    await expect(
      page.getByText(T.profileLoadError, { exact: true }),
    ).toBeVisible()
    const retry = page.getByRole('button', { name: T.retry })
    await expect(retry).toBeVisible()

    // Retry refetches once the network is back and the form recovers.
    await page.unroute('**/accounts/me/')
    await retry.click()
    await expect(firstName).not.toHaveValue('')
  })

  test('si el perfil no carga al iniciar sesión, el sidebar muestra el fallback y Reintentar recupera', async ({
    page,
  }) => {
    // Real failure path: profile unreachable right after login. The login
    // mutation stores tokens, then its profile fetch fails; navigating back
    // into the dashboard (SPA history, no full reload — a reload would hit
    // auth-init's clean-up redirect) renders both error fallbacks.
    await loginAs(page)
    await page.getByRole('button', { name: T.userMenu }).click()
    await page.getByRole('menuitem', { name: T.logout }).click()
    await expect(page).toHaveURL(/\/login/)

    await page.route('**/accounts/me/', (route) => route.abort())
    await page.locator('input[type="email"]').fill(E2E_USER.email)
    await page.locator('input[type="password"]').fill(E2E_USER.password)
    await page.locator('button[type="submit"]').click()
    await expect(
      page.getByText(T.loginErrorToast, { exact: true }),
    ).toBeVisible()

    // Tokens are set but the profile query is in error state with no data.
    await page.goBack()
    await expect(page).toHaveURL(/\/dashboard/)
    await expect(
      page.getByText(T.profileUnavailable, { exact: true }),
    ).toBeVisible()

    const retry = page.getByRole('button', { name: T.retry })
    await page.unroute('**/accounts/me/')
    await retry.click()
    await expect(page.getByRole('button', { name: T.userMenu })).toBeVisible()
  })
})
