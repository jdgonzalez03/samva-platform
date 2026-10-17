import { test, expect, type APIRequestContext } from '@playwright/test'
import { apiAccessToken, apiSecretOf } from '../frontend/helpers'

// Seeded in backend/sensors/fixtures/initial_sensors.json: plot 1 of farm 1, owned by E2E_USER.
const SEED_SENSOR = { serial: 'SEED-0001', farmId: 1, plotId: 1 }
// Plot 5 hangs off farm 3, owned by another seeded farmer.
const OTHER_FARMERS_SENSOR = 'SEED-0009'

interface ReadingRow {
  recorded_at: string
  semantic_key: string
  value: number | null
}

test.describe('POST /api/sensors/ingest/', () => {
  let access: string
  let secret: string

  test.beforeAll(async ({ request }) => {
    access = await apiAccessToken(request)
    secret = await apiSecretOf(request, access)
  })

  function ingest(request: APIRequestContext, body: object, key: string | null = secret) {
    return request.post('/api/sensors/ingest/', {
      data: body,
      headers: key ? { 'X-API-Key': key } : {},
    })
  }

  test('una lectura enviada con el secret del perfil aparece en el historial', async ({
    request,
  }) => {
    // A second-precision "now" keeps each run on a fresh instant, so reruns never collide.
    const recordedAt = new Date(Math.floor(Date.now() / 1000) * 1000).toISOString()
    const body = {
      serial_number: SEED_SENSOR.serial,
      recorded_at: recordedAt,
      readings: [{ variable: 'soil_moisture', value: 42.4242 }],
    }

    const first = await ingest(request, body)
    expect(first.status()).toBe(201)
    expect(await first.json()).toEqual({ created: 1, duplicates: 0 })

    const resent = await ingest(request, body)
    expect(resent.status()).toBe(201)
    expect(await resent.json()).toEqual({ created: 0, duplicates: 1 })

    const history = await request.get(
      `/api/sensors/farms/${SEED_SENSOR.farmId}/history/readings/`,
      {
        headers: { Authorization: `Bearer ${access}` },
        params: { plot: SEED_SENSOR.plotId, variable: 'soil_moisture' },
      },
    )
    expect(history.ok()).toBeTruthy()
    const rows: ReadingRow[] = (await history.json()).results
    const stored = rows.filter((row) => Date.parse(row.recorded_at) === Date.parse(recordedAt))
    expect(stored).toHaveLength(1)
    expect(stored[0].value).toBe(42.4242)
  })

  test('sin X-API-Key responde 401', async ({ request }) => {
    const response = await ingest(request, {}, null)
    expect(response.status()).toBe(401)
  })

  test('un secret inválido responde 401', async ({ request }) => {
    const response = await ingest(request, {}, 'smv_not-a-real-key')
    expect(response.status()).toBe(401)
  })

  test('el sensor de otro usuario responde 404', async ({ request }) => {
    const response = await ingest(request, {
      serial_number: OTHER_FARMERS_SENSOR,
      recorded_at: new Date().toISOString(),
      readings: [{ variable: 'soil_moisture', value: 30 }],
    })
    expect(response.status()).toBe(404)
  })
})

test.describe('POST /api/accounts/me/api-secret/regenerate/', () => {
  test('el secret anterior deja de autenticar sensores', async ({ request }) => {
    const access = await apiAccessToken(request)
    const original = await apiSecretOf(request, access)

    const response = await request.post('/api/accounts/me/api-secret/regenerate/', {
      headers: { Authorization: `Bearer ${access}` },
    })
    expect(response.ok()).toBeTruthy()
    const regenerated = (await response.json()).api_secret
    expect(regenerated).not.toBe(original)
    expect(await apiSecretOf(request, access)).toBe(regenerated)

    const body = {
      serial_number: SEED_SENSOR.serial,
      recorded_at: new Date(Math.floor(Date.now() / 1000) * 1000).toISOString(),
      readings: [{ variable: 'soil_moisture', value: 30 }],
    }
    const withOld = await request.post('/api/sensors/ingest/', {
      data: body,
      headers: { 'X-API-Key': original },
    })
    expect(withOld.status()).toBe(401)
    const withNew = await request.post('/api/sensors/ingest/', {
      data: body,
      headers: { 'X-API-Key': regenerated },
    })
    expect(withNew.status()).toBe(201)
  })
})
