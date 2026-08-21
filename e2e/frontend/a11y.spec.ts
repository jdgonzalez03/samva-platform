import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { gotoHydrated, loginAs, T } from './helpers'

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']

/**
 * Runs an axe WCAG 2.2 AA scan and returns only serious/critical violations,
 * shaped for a readable diff on failure.
 */
async function severeViolations(page: Page, exclude?: string) {
  let builder = new AxeBuilder({ page }).withTags(WCAG_TAGS)
  if (exclude) builder = builder.exclude(exclude)
  const results = await builder.analyze()
  return results.violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => ({
      id: v.id,
      impact: v.impact,
      help: v.help,
      nodes: v.nodes.map((n) => n.target.join(' ')),
    }))
}

// KNOWN VIOLATION (qa.md finding F1): the login submit button renders white
// text on the light-mode primary green (#00c950) — 2.21:1, fails WCAG 1.4.3.
// Excluded so the scan stays a regression gate for everything else; remove
// this exclusion when the button colour is fixed.
const LOGIN_SUBMIT_KNOWN_CONTRAST = 'button[type="submit"]'

test.describe('Accesibilidad (axe, WCAG 2.2 AA)', () => {
  test('login sin violaciones serias/críticas (es y en)', async ({ page }) => {
    await gotoHydrated(page, '/login')
    expect(await severeViolations(page, LOGIN_SUBMIT_KNOWN_CONTRAST)).toEqual([])

    await gotoHydrated(page, '/en/login')
    expect(await severeViolations(page, LOGIN_SUBMIT_KNOWN_CONTRAST)).toEqual([])
  })

  test('dashboard y perfil sin violaciones serias/críticas (es)', async ({
    page,
  }) => {
    await loginAs(page)
    // Let the login toast expire so the scan sees the steady-state page.
    await expect(
      page.getByText(T.loginSuccessToast, { exact: true }),
    ).toBeHidden({ timeout: 15000 })
    expect(await severeViolations(page)).toEqual([])

    await gotoHydrated(page, '/dashboard/profile')
    await expect(
      page.getByRole('textbox', { name: T.firstName }),
    ).not.toHaveValue('')
    expect(await severeViolations(page)).toEqual([])
  })

  test('dashboard y perfil sin violaciones serias/críticas (en)', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, '/en/dashboard')
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
    expect(await severeViolations(page)).toEqual([])

    await gotoHydrated(page, '/en/dashboard/profile')
    await expect(page.getByRole('textbox').first()).not.toHaveValue('')
    expect(await severeViolations(page)).toEqual([])
  })
})
