import { test, expect } from '@playwright/test'
import { gotoHydrated, loginAs, T } from './helpers'

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
