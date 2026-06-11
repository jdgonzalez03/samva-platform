import { test, expect } from '@playwright/test'
import type { LandingData, HeroValue, VisionMisionValue, BenefitsValue } from './types'

test.describe('GET /api/cms/landing/', () => {
  let data: LandingData

  test.beforeAll(async ({ request }) => {
    const response = await request.get('/api/cms/landing/')
    expect(response.ok()).toBeTruthy()
    data = await response.json()
  })

  test('responde 200', async ({ request }) => {
    const response = await request.get('/api/cms/landing/')
    expect(response.ok()).toBeTruthy()
  })

  test('tiene title (string) y body (array)', () => {
    expect(typeof data.title).toBe('string')
    expect(Array.isArray(data.body)).toBeTruthy()
  })

  test('body tiene al menos 1 bloque', () => {
    expect(data.body.length).toBeGreaterThanOrEqual(1)
  })

  test('cada bloque tiene type (string), id (string) y value (object)', () => {
    for (const block of data.body) {
      expect(typeof block.type).toBe('string')
      expect(typeof block.id).toBe('string')
      expect(typeof block.value).toBe('object')
      expect(block.value).not.toBeNull()
    }
  })

  test('existe bloque hero con estructura válida', () => {
    const hero = data.body.find((b) => b.type === 'hero')
    expect(hero).toBeDefined()

    const val = hero!.value as unknown as HeroValue
    expect(typeof val.badge).toBe('string')
    expect(typeof val.title).toBe('object')
    expect(typeof val.title.title).toBe('string')
    expect(typeof val.title.highlight_text).toBe('string')
    expect(typeof val.description).toBe('string')
    expect(typeof val.cta_button).toBe('object')
    expect(typeof val.cta_button.text).toBe('string')
    expect(typeof val.cta_button.icon).toBe('string')
    expect(typeof val.cta_button.url).toBe('string')
  })

  test('existe bloque vision_mision con estructura válida', () => {
    const vm = data.body.find((b) => b.type === 'vision_mision')
    expect(vm).toBeDefined()

    const val = vm!.value as unknown as VisionMisionValue
    expect(typeof val.background).toBe('string')
    expect(typeof val.vision.title).toBe('string')
    expect(typeof val.vision.description).toBe('string')
    expect(typeof val.vision.icon).toBe('string')
    expect(typeof val.mision.title).toBe('string')
    expect(typeof val.mision.description).toBe('string')
    expect(typeof val.mision.icon).toBe('string')
  })

  test('existe bloque benefits con estructura válida', () => {
    const benefits = data.body.find((b) => b.type === 'benefits')
    expect(benefits).toBeDefined()

    const val = benefits!.value as unknown as BenefitsValue
    expect(typeof val.background).toBe('string')
    expect(typeof val.heading.title).toBe('string')
    expect(typeof val.heading.text).toBe('string')
    expect(Array.isArray(val.items)).toBeTruthy()
    expect(val.items.length).toBeGreaterThanOrEqual(1)

    for (const item of val.items) {
      expect(typeof item.title).toBe('string')
      expect(typeof item.description).toBe('string')
      expect(typeof item.icon).toBe('string')
    }
  })

  test('existe bloque team con miembros', () => {
    const team = data.body.find((b) => b.type === 'team')
    expect(team).toBeDefined()
    expect(Array.isArray((team!.value as unknown as { members: unknown[] }).members)).toBeTruthy()
    expect((team!.value as unknown as { members: unknown[] }).members.length).toBeGreaterThanOrEqual(1)
  })

  test('existe bloque feature_highlight', () => {
    const fh = data.body.find((b) => b.type === 'feature_highlight')
    expect(fh).toBeDefined()
  })

  test('existe bloque cta_section con botón', () => {
    const cta = data.body.find((b) => b.type === 'cta_section')
    expect(cta).toBeDefined()

    const val = cta!.value as unknown as { cta_button: { text: string; icon: string; url: string } }
    expect(typeof val.cta_button.text).toBe('string')
    expect(typeof val.cta_button.url).toBe('string')
  })
})
