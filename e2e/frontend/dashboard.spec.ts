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
    await gotoHydrated(page, '/dashboard?view=map')

    const map = page.getByRole('region', { name: T.mapRegion })
    await expect(
      map.getByRole('link', { name: T.osmAttribution }),
    ).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright')
    await expect.poll(() => tileRequests.length).toBeGreaterThan(0)
  })
})
