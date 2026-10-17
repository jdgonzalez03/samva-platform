import { test, expect } from '@playwright/test'
import { gotoHydrated, loginAs, T } from './helpers'

// The manifest and service worker only exist in a production build (the dev
// server leaves them out so HMR is never served from a cache); the icons and
// head links they point at are generated in dev too, and are checked here.
test.describe('App instalable (PWA)', () => {
  test('el head anuncia el favicon, el icono de Apple y el color del tema', async ({
    page,
    request,
  }) => {
    await gotoHydrated(page, '/login')

    await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute(
      'content',
      '#171717',
    )
    const iconHrefs = await page
      .locator('link[rel="icon"], link[rel="apple-touch-icon"]')
      .evaluateAll((links) => links.map((link) => link.getAttribute('href')))
    expect(iconHrefs).toEqual(
      expect.arrayContaining([
        '/favicon.ico',
        '/logo.svg',
        '/apple-touch-icon-180x180.png',
      ]),
    )

    for (const href of iconHrefs) {
      const response = await request.get(href!)
      expect(response.ok(), href!).toBeTruthy()
    }
  })

  test('el sidebar siempre ofrece instalar la app y, sin aviso del navegador, explica los pasos', async ({
    page,
  }) => {
    await loginAs(page)

    await page.getByRole('button', { name: T.installApp }).click()
    const steps = page.getByRole('dialog', { name: T.installHelpTitle })
    await expect(steps).toBeVisible()
    await expect(steps.getByRole('listitem')).toHaveCount(3)

    await steps.getByRole('button', { name: T.installHelpClose }).click()
    await expect(steps).toHaveCount(0)
  })

  test('con el aviso del navegador, la entrada abre la instalación nativa', async ({
    page,
  }) => {
    await loginAs(page)
    const installEntry = page.getByRole('button', { name: T.installApp })
    await expect(installEntry).toBeVisible()

    // Chromium fires `beforeinstallprompt` only for an installable production
    // build; the spec stands in for it with an event exposing the same API.
    await page.evaluate(() => {
      const event = new Event('beforeinstallprompt') as Event & {
        prompt: () => Promise<void>
        userChoice: Promise<{ outcome: string; platform: string }>
      }
      event.prompt = async () => {
        ;(window as unknown as { promptShown: boolean }).promptShown = true
      }
      event.userChoice = Promise.resolve({ outcome: 'accepted', platform: 'web' })
      window.dispatchEvent(event)
    })

    await installEntry.click()
    await expect
      .poll(() =>
        page.evaluate(() => (window as unknown as { promptShown?: boolean }).promptShown),
      )
      .toBe(true)
    await expect(page.getByRole('dialog', { name: T.installHelpTitle })).toHaveCount(0)
  })
})
