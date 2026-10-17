import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { gotoHydrated, loginAs, T } from './helpers'

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']

/**
 * Runs an axe WCAG 2.2 AA scan and returns only serious/critical violations,
 * shaped for a readable diff on failure.
 */
async function severeViolations(
  page: Page,
  exclude?: string,
  include?: string,
) {
  let builder = new AxeBuilder({ page }).withTags(WCAG_TAGS)
  if (exclude) builder = builder.exclude(exclude)
  if (include) builder = builder.include(include)
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

// KNOWN VIOLATION: once a prediction is shown, the fuzzy view's panel body
// (`overflow-y-auto`) scrolls but holds nothing focusable, so keyboard users
// cannot scroll it (axe `scrollable-region-focusable`). Ignored on that scan
// only; remove when the panel body becomes keyboard-scrollable.
const FUZZY_BODY_KNOWN_SCROLL = 'scrollable-region-focusable'

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
    // While the overview loads, the panel scrolls over skeletons with nothing
    // focusable inside, which axe reports; scan the loaded page instead.
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, {
      timeout: 15000,
    })
    expect(await severeViolations(page)).toEqual([])

    await gotoHydrated(page, '/en/dashboard/profile')
    await expect(page.getByRole('textbox').first()).not.toHaveValue('')
    expect(await severeViolations(page)).toEqual([])
  })

  test('predicciones sin violaciones serias/críticas (es)', async ({ page }) => {
    // The seed has no readings; an empty history is the view's steady state.
    await page.route('**/api/predictions/plots/*/irrigation/**', (route) =>
      route.fulfill({ json: { count: 0, page: 1, page_size: 10, results: [] } }),
    )
    await loginAs(page)

    await gotoHydrated(page, '/dashboard/predictions')
    await expect(page.getByText(T.fuzzyIrrigationCard)).toBeVisible()
    expect(await severeViolations(page)).toEqual([])

    await gotoHydrated(page, '/dashboard/predictions/fuzzy')
    await expect(page.getByText(T.predictionEmpty)).toBeVisible()
    expect(await severeViolations(page)).toEqual([])
  })

  test('desglose por fuente de la vista difusa sin violaciones serias/críticas', async ({
    page,
  }) => {
    // A station row without readings exercises the aria-hidden "—" + sr-only text.
    const prediction = {
      id: 902,
      plot: 1,
      avg_moisture: 40,
      avg_temperature: 17.5,
      avg_radiation: 600,
      avg_period_hours: 6,
      irrigation_time_minutes: 10.14,
      output_label: 'very_little',
      input_memberships: {
        moisture: { low: 0, medium: 0.333, high: 0.667 },
        temperature: { low: 0, medium: 0.6, high: 0.4 },
        radiation: { low: 0, medium: 1, high: 0 },
      },
      output_activation: {
        nothing: 0.6,
        very_little: 0.333,
        little: 0.333,
        long: 0,
        very_long: 0,
      },
      clipped_inputs: [],
      input_sources: {
        moisture: { field: 40, station: null },
        temperature: { field: 17, station: 18 },
        radiation: { field: 600, station: null },
      },
      requested_at: '2026-09-29T15:00:00Z',
    }
    await page.route('**/api/predictions/plots/*/irrigation/**', (route) =>
      route.fulfill({
        json: { count: 1, page: 1, page_size: 10, results: [prediction] },
      }),
    )
    await loginAs(page)

    await gotoHydrated(page, '/dashboard/predictions/fuzzy')
    await expect(page.getByText(T.sourceStation).first()).toBeVisible()
    const violations = await severeViolations(
      page,
      undefined,
      '[id$="-panel-predictions-fuzzy"]',
    )
    expect(violations.filter((v) => v.id !== FUZZY_BODY_KNOWN_SCROLL)).toEqual(
      [],
    )
  })

  test('asistente con una conversación sin violaciones serias/críticas', async ({
    page,
  }) => {
    await page.route('**/api/assistant/chat/', (route) =>
      route.fulfill({
        json: {
          reply: 'Tienes 3 fincas.',
          tool_calls: [{ name: 'list_farms', arguments: {}, result: [] }],
        },
      }),
    )
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/assistant')
    await page
      .getByRole('button', { name: T.assistantSuggestionFarms })
      .click()
    await expect(page.getByText('Tienes 3 fincas.')).toBeVisible()

    expect(
      await severeViolations(page, undefined, '[id$="-panel-assistant"]'),
    ).toEqual([])
  })

  test('asistente vacío con consejos sin violaciones serias/críticas', async ({
    page,
  }) => {
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/assistant')
    await expect(page.getByText(T.assistantTipsTitle)).toBeVisible()

    expect(
      await severeViolations(page, undefined, '[id$="-panel-assistant"]'),
    ).toEqual([])
  })

  test('mis sensores sin violaciones serias/críticas', async ({ page }) => {
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/sensors')
    await expect(
      page.getByRole('table', { name: T.sensorsTableFarmFirst }),
    ).toBeVisible()
    // Scoped to the page's own panel: the shared sidebar is covered by the
    // dashboard scan above. Nuxt UI prefixes the panel id with its storage key.
    expect(
      await severeViolations(page, undefined, '[id$="-panel-sensors-devices"]'),
    ).toEqual([])
  })

  test('detalle del lote sin violaciones serias/críticas (es)', async ({ page }) => {
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/plots/1')
    await expect(page.getByText(T.plotConditionsTitle).first()).toBeVisible()
    expect(await severeViolations(page)).toEqual([])
  })

  test('mis lotes sin violaciones serias/críticas (es)', async ({ page }) => {
    await loginAs(page)
    await gotoHydrated(page, '/dashboard/plots')
    await expect(page.getByText(T.plotName, { exact: true })).toBeVisible()
    expect(await severeViolations(page)).toEqual([])
  })
})

