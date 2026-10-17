import { test, expect, type APIRequestContext } from '@playwright/test'
import { E2E_USER } from '../frontend/helpers'

// Seed: plot 5 ("Lote Alto") belongs to Finca La Montaña, owned by another farmer.
const FOREIGN_PLOT_ID = 5
// Seed: SEED-0005 is the active sensor of E2E_USER's plot 2 that measures all three
// inputs of the irrigation model.
const FULL_SENSOR = { serial: 'SEED-0005', plotId: 2 }

async function accessToken(request: APIRequestContext): Promise<string> {
  const response = await request.post('/api/accounts/login/', {
    data: E2E_USER,
  })
  expect(response.ok()).toBeTruthy()
  return (await response.json()).tokens.access
}

async function apiSecret(
  request: APIRequestContext,
  access: string,
): Promise<string> {
  const response = await request.get('/api/accounts/me/', {
    headers: { Authorization: `Bearer ${access}` },
  })
  expect(response.ok()).toBeTruthy()
  return (await response.json()).farmer.api_secret
}

test.describe('API de predicciones', () => {
  test('sin token responde 401', async ({ request }) => {
    expect((await request.get('/api/predictions/models/')).status()).toBe(401)
    expect(
      (
        await request.post(
          `/api/predictions/plots/${FOREIGN_PLOT_ID}/irrigation/`,
        )
      ).status(),
    ).toBe(401)
  })

  test('el catálogo lista el modelo de riego con lógica difusa', async ({
    request,
  }) => {
    const headers = { Authorization: `Bearer ${await accessToken(request)}` }

    const response = await request.get('/api/predictions/models/', { headers })

    expect(response.ok()).toBeTruthy()
    expect(await response.json()).toContainEqual({
      key: 'fuzzy-irrigation',
      technique: 'fuzzy',
      target: 'irrigation',
    })
  })

  test('las definiciones describen las tres entradas y la salida', async ({
    request,
  }) => {
    const headers = { Authorization: `Bearer ${await accessToken(request)}` }

    const response = await request.get(
      '/api/predictions/fuzzy/irrigation/definitions/',
      {
        headers,
      },
    )

    expect(response.ok()).toBeTruthy()
    expect(Object.keys(await response.json()).sort()).toEqual([
      'irrigation_time',
      'moisture',
      'radiation',
      'temperature',
    ])
  })

  test('el lote de otro usuario responde 404', async ({ request }) => {
    const headers = { Authorization: `Bearer ${await accessToken(request)}` }
    const url = `/api/predictions/plots/${FOREIGN_PLOT_ID}/irrigation/`

    expect((await request.get(url, { headers })).status()).toBe(404)
    expect((await request.post(url, { headers })).status()).toBe(404)
  })

  test('con lecturas recientes crea una predicción que aparece en el historial', async ({
    request,
  }) => {
    const access = await accessToken(request)
    const headers = { Authorization: `Bearer ${access}` }
    // A second-precision "now" keeps each run on a fresh instant, so reruns never collide.
    const ingest = await request.post('/api/sensors/ingest/', {
      headers: { 'X-API-Key': await apiSecret(request, access) },
      data: {
        serial_number: FULL_SENSOR.serial,
        recorded_at: new Date(
          Math.floor(Date.now() / 1000) * 1000,
        ).toISOString(),
        readings: [
          { variable: 'soil_moisture', value: 30 },
          { variable: 'air_temperature', value: 18 },
          { variable: 'solar_radiation', value: 600 },
        ],
      },
    })
    expect(ingest.status()).toBe(201)
    const url = `/api/predictions/plots/${FULL_SENSOR.plotId}/irrigation/`

    const created = await request.post(url, { headers, data: { hours: 1 } })

    expect(created.status()).toBe(201)
    const prediction = await created.json()
    expect(prediction.plot).toBe(FULL_SENSOR.plotId)
    expect(prediction.avg_period_hours).toBe(1)
    expect(typeof prediction.irrigation_time_minutes).toBe('number')
    expect(Object.keys(prediction.input_memberships).sort()).toEqual([
      'moisture',
      'radiation',
      'temperature',
    ])
    // Seeded stations are not used in predictions (the fixture default), so each
    // input comes from the field sensors alone.
    for (const input of ['moisture', 'temperature', 'radiation']) {
      expect(typeof prediction.input_sources[input].field).toBe('number')
      expect(prediction.input_sources[input].station).toBeNull()
    }

    const history = await (await request.get(url, { headers })).json()
    expect(history.results[0].id).toBe(prediction.id)
  })
})
