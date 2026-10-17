import {
  expect,
  type APIRequestContext,
  type Locator,
  type Page,
} from '@playwright/test'

export const E2E_USER = {
  email: process.env.E2E_USER_EMAIL ?? 'juan.perez@email.com',
  password: process.env.E2E_USER_PASSWORD ?? 'Test@1234!',
}

// Seed: owns Finca La Montaña, whose plot "Lote El Rodeo" carries the LoRa demo
// probes 101–109 — kept off E2E_USER's farms, whose specs count variables.
export const LORA_USER = {
  email: 'maria.lopez@email.com',
  password: E2E_USER.password,
}

/**
 * Every UI string the specs select by (roles, toasts, labels).
 * This map is the locale seam: when i18n lands, only these values change
 * (to the Spanish defaults) — never the spec logic.
 */
export const T = {
  // login page
  signIn: 'Iniciar sesión',
  loginSuccessToast: 'Bienvenido de nuevo',
  loginErrorToast: 'Error al iniciar sesión',
  emailValidation: 'Ingresa un correo electrónico válido',
  // sidebar user dropdown (trigger shows the user's display name;
  // last_name is stable — first_name is edited by profile.spec.ts)
  userMenu: 'Pérez',
  // seeded farmer has no avatar, so the trigger falls back to their initials
  userDisplayName: 'Juan Pérez',
  userInitials: 'JP',
  logout: 'Cerrar sesión',
  // profile page
  firstName: 'Nombre',
  saveChanges: 'Guardar cambios',
  profileUpdatedToast: 'Perfil actualizado',
  changeAvatar: 'Cambiar foto de perfil',
  profileLoadError: 'No pudimos cargar tu perfil. Inténtalo de nuevo.',
  retry: 'Reintentar',
  // profile page — API access card
  apiSecretTitle: 'Acceso API',
  showApiSecret: 'Mostrar secreto de API',
  hideApiSecret: 'Ocultar secreto de API',
  copyApiSecret: 'Copiar secreto de API',
  apiSecretCopiedToast: 'Secreto copiado',
  apiDocsLink: 'Ver documentación de la API',
  regenerateApiSecret: 'Regenerar secreto de API',
  regenerateApiSecretDialog: '¿Regenerar el secreto de API?',
  regenerateApiSecretConfirm: 'Regenerar',
  regenerateApiSecretCancel: 'Cancelar',
  apiSecretRegeneratedToast: 'Secreto regenerado',
  // sidebar profile fallback
  profileUnavailable: 'Perfil no disponible.',
  // farm switcher + dashboard stat cards (seed: juan.perez owns three farms,
  // ordered by name, so El Tesoro is the default selection)
  farmFirst: 'Finca El Tesoro',
  farmSecond: 'Finca San Vicente',
  statPlots: 'Lotes',
  farmsUnavailable: 'Fincas no disponibles.',
  plotsLoadError: 'No se pudieron cargar los lotes.',
  // predictions (sidebar entry + child, catalogue card, fuzzy irrigation view)
  navPredictions: 'Predicciones',
  navFuzzyLogic: 'Lógica difusa',
  fuzzyIrrigationCard: 'Riego con lógica difusa',
  fuzzyTitle: 'Lógica difusa: riego',
  calculatePrediction: 'Calcular predicción',
  predictionResultTitle: 'Tiempo de riego recomendado',
  predictionEmpty: 'Elige un lote y calcula una predicción para ver el resultado.',
  missingReadings: 'No disponible en este momento: humedad del suelo, radiación solar',
  missingAllReadings:
    'No disponible en este momento: humedad del suelo, temperatura del aire, radiación solar',
  predictionPlot: 'Lote',
  // the three input cards of the fuzzy view and their per-source breakdown
  inputMoisture: 'Humedad del suelo',
  inputTemperature: 'Temperatura del aire',
  inputRadiation: 'Radiación solar',
  sourceField: 'Sensores de campo:',
  sourceStation: 'Estación:',
  sourceUsed: 'Usado:',
  // sr-only text of a source without readings (the visible "—" is aria-hidden)
  sourceNone: 'sin datos',
  // seed: SEED-0005 on this plot measures all three model inputs
  plotFullInputs: 'Lote El Abrevadero',
  // seed: Finca El Tesoro plot without any sensor
  plotNoSensors: 'Lote Sin Mapear',
  predictionHistoryTitle: 'Predicciones anteriores',
  predictionHistoryEmpty: 'Todavía no hay predicciones para este lote.',
  // stubbed prediction: 10.14 min, "very_little" group, "nothing" fired at 0.6
  predictionMinutes: '10,1 min',
  predictionLabel: 'Muy poco',
  predictionActivation: 'Sin riego 60',
  // plot detail (/dashboard/plots/1 — seed: "Lote La Colina" of Finca El Tesoro)
  plotName: 'Lote La Colina',
  plotConditionsTitle: 'Condiciones actuales',
  plotLive: 'Reportando',
  plotMoistureLevel: 'Nivel Bajo',
  plotMoistureChange: '-6 % en 24 h',
  plotHeatmapTitle: 'Mapa de calor por hora',
  plotIrrigationCalculate: 'Calcular predicción',
  plotSensorOnline: 'En línea',
  plotOverviewError: 'No se pudieron cargar los datos del lote.',
  // home dashboard (farm overview)
  homeAlerts: 'Alertas',
  homeAttention: 'Necesita atención',
  homeDryAlert: 'Suelo seco en Lote El Abrevadero',
  homeStaleAlert: 'Lote La Colina sin lecturas recientes',
  homeSensorsOnline: 'Sensores en línea',
  homeSensorsValue: '1 de 2',
  homeRankingTitle: 'Lotes',
  homeIrrigationTotal: 'Total recomendado: 12,5 min',
  homeFarmConditions: 'Condiciones de la finca',
  // "Mis lotes" (/dashboard/plots)
  navPlots: 'Mis lotes',
  plotsIndexTitle: 'Mis lotes',
  plotsIndexSummary: '3 lotes en 2 fincas',
  plotsSearch: 'Buscar lote',
  plotsFarmFilter: 'Finca',
  plotsNoMatches: 'Ningún lote coincide con los filtros.',
  plotsClearFilters: 'Limpiar filtros',
  plotsMoistureValue: '9 %',
  plotsIrrigationBadge: 'Riego 12,5 min',
  plotAbrevadero: 'Lote El Abrevadero',
  plotManantial: 'Lote El Manantial',
  // dashboard map (street basemap attribution links to OSM's copyright page)
  mapRegion: 'Mapa de la finca, Finca El Tesoro',
  osmAttribution: 'OpenStreetMap',
  // sidebar PWA install entry
  installApp: 'Instalar app',
  installHelpTitle: 'Instalar SAMVA',
  installHelpClose: 'Entendido',
  // my sensors page (/dashboard/sensors)
  navSensors: 'Mis sensores',
  sensorsTableFarmFirst: 'Sensores de Finca El Tesoro',
  sensorStatusOnline: 'En línea',
  sensorStatusInactive: 'Inactivo',
  // sensor history page (/dashboard/history)
  navHistory: 'Historial',
  filterPlot: 'Lote',
  filterVariable: 'Variable ambiental',
  filterRange: 'Rango de fechas',
  filtersReset: 'Limpiar filtros',
  range30d: 'Últimos 30 días',
  range1h: 'Última hora',
  range6h: 'Últimas 6 horas',
  chartsRegion: 'Gráficos del historial',
  averagesRegion: 'Promedios por lote',
  paginationLabel: 'Paginación de las lecturas',
  // the pagination buttons are named `Página <n>`
  paginationPage: 'Página',
  exportLabel: 'Exportar',
  exportCsv: 'Descargar CSV',
  // seeded values the history page renders straight from the API (not translated)
  plotFirst: 'Lote La Colina',
  varAirTemperature: 'Temperatura del aire',
  // LORA_USER's farms, ordered by name (El Edén is the default selection)
  loraFarmDefault: 'Finca El Edén',
  loraFarm: 'Finca La Montaña',
  loraPlot: 'Lote El Rodeo',
  varCo2: 'CO₂',
  // live refresh (values of the stubbed soil-moisture condition before/after a poll)
  liveMoistureBefore: '12,3 %',
  liveMoistureAfter: '31,7 %',
  // weather stations (home cards, /dashboard/stations, /dashboard/stations/<id>)
  navStations: 'Estaciones',
  stationsTitle: 'Estaciones meteorológicas',
  // a card's "Ver detalle" link is named after its station
  stationDetailFor: 'Ver detalle de',
  stationStatusOnline: 'En línea',
  stationStatusStale: 'Sin datos recientes',
  stationsEmpty: 'Esta finca no tiene estaciones meteorológicas.',
  stationConditions: 'Condiciones actuales',
  stationCharts: 'Gráficas',
  stationReadings: 'Lecturas',
  stationRange: 'Periodo',
  range7d: 'Últimos 7 días',
  stationNotFound: 'Estación no encontrada',
  stationBackToList: 'Ver todas las estaciones',
  exportJson: 'Descargar JSON',
  // assistant (chatbot) page (/dashboard/assistant)
  navAssistant: 'Asistente',
  assistantTitle: 'Asistente',
  assistantEmpty: '¿En qué te ayudo hoy?',
  assistantSuggestionFarms: '¿Cuántas fincas tengo?',
  // quick actions that need a plot only prefill the prompt with this text
  assistantActionCalculate: 'Calcular riego',
  assistantPromptCalculate: 'Calcula el riego del lote ',
  assistantTipsTitle: 'Consejos para obtener mejores respuestas',
  assistantTipsClose: 'Ocultar consejos',
  assistantPrompt: 'Escribe tu pregunta…',
  assistantSend: 'Enviar pregunta',
  assistantNewChat: 'Nueva conversación',
  assistantToolFarms: 'Consultó tus fincas',
  assistantToolIrrigation: 'Calculó una prescripción de riego',
  assistantUnavailable: 'El asistente no está disponible en este momento.',
  assistantThrottled:
    'Hiciste muchas preguntas seguidas. Espera un minuto e inténtalo de nuevo.',
  // error page (error.vue)
  errorTitle: '404 — Página no encontrada',
  errorHeading: 'Página no encontrada',
  backHome: 'Volver al inicio',
}

/** English strings + switcher labels used only by the i18n specs. */
export const T_EN = {
  signIn: 'Sign in',
  loginTitle: 'Sign in',
  loginHeading: 'Welcome back',
  logout: 'Log out',
  profileLink: 'Profile',
  errorTitle: '404 — Page not found',
  errorHeading: 'Page not found',
  backHome: 'Back to home',
  assistantSuggestionFarms: 'How many farms do I have?',
}

export const SWITCHER = {
  loginTrigger: 'Cambiar idioma',
  dashboardSubmenu: 'Idioma',
  spanish: 'Español',
  english: 'English',
}

/**
 * Navigates and waits for Vue hydration: interacting with a form before
 * hydration triggers a native (full-page) submit instead of the Vue handler.
 */
// Absolute, so specs of the frontend project (baseURL :3000) can reach the API too.
const BACKEND_URL = process.env.E2E_BACKEND_URL ?? 'http://localhost:8000'

export async function apiAccessToken(
  request: APIRequestContext,
): Promise<string> {
  const response = await request.post(`${BACKEND_URL}/api/accounts/login/`, {
    data: E2E_USER,
  })
  expect(response.ok()).toBeTruthy()
  return (await response.json()).tokens.access
}

export async function apiSecretOf(
  request: APIRequestContext,
  access: string,
): Promise<string> {
  const response = await request.get(`${BACKEND_URL}/api/accounts/me/`, {
    headers: { Authorization: `Bearer ${access}` },
  })
  expect(response.ok()).toBeTruthy()
  return (await response.json()).farmer.api_secret
}

// Pushes one soil-moisture reading as the seeded sensor would; second precision
// keeps every call on a fresh instant so reruns never collide as duplicates.
export async function ingestReading(
  request: APIRequestContext,
  apiKey: string,
  serialNumber: string,
  value = 30,
) {
  return ingestReadings(request, apiKey, serialNumber, [
    { variable: 'soil_moisture', value },
  ])
}

export async function ingestReadings(
  request: APIRequestContext,
  apiKey: string,
  serialNumber: string,
  readings: { variable: string; value: number }[],
) {
  return request.post(`${BACKEND_URL}/api/sensors/ingest/`, {
    data: {
      serial_number: serialNumber,
      recorded_at: new Date(Math.floor(Date.now() / 1000) * 1000).toISOString(),
      readings,
    },
    headers: { 'X-API-Key': apiKey },
  })
}

export async function gotoHydrated(page: Page, path: string): Promise<void> {
  await page.goto(path)
  await page.waitForFunction(() => {
    const root = document.querySelector('#__nuxt') as { __vue_app__?: unknown } | null
    return Boolean(root?.__vue_app__)
  })
}

/**
 * The value rendered inside the dashboard stat card carrying the given visible
 * title. The title and the value sit in sibling subtrees of the card root, so
 * the lookup climbs from the label to the card before descending again.
 */
export function statCardValue(page: Page, title: string): Locator {
  return page
    .getByText(title, { exact: true })
    .locator('xpath=ancestor::*[@data-slot="root"][1]')
    .locator('p')
    .first()
}

/**
 * Opens the sidebar farm switcher and picks a farm. The dropdown overlay
 * aria-hides the rest of the page while open, so it must be dismissed before
 * anything in the background can be located again.
 */
export async function selectFarm(
  page: Page,
  farmName: string,
  currentFarm: string = T.farmFirst,
): Promise<void> {
  await page.getByRole('button', { name: currentFarm }).click()
  await page.getByRole('menuitemcheckbox', { name: farmName }).click()
  await page.keyboard.press('Escape')
}

/**
 * Logs in through the real login form and waits for the dashboard.
 * Credentials default to E2E_USER (overridable via E2E_USER_EMAIL /
 * E2E_USER_PASSWORD env vars).
 */
export async function loginAs(
  page: Page,
  email: string = E2E_USER.email,
  password: string = E2E_USER.password,
): Promise<void> {
  await gotoHydrated(page, '/login')
  const emailInput = page.locator('input[type="email"]')
  const passwordInput = page.locator('input[type="password"]')
  // A late re-render of the form can wipe a field filled right after
  // hydration, so both are re-filled until they hold their values.
  await expect(async () => {
    await emailInput.fill(email)
    await passwordInput.fill(password)
    await expect(emailInput).toHaveValue(email, { timeout: 500 })
    await expect(passwordInput).toHaveValue(password, { timeout: 500 })
  }).toPass()
  await page.locator('button[type="submit"]').click()
  await expect(page).toHaveURL(/\/dashboard/)
}

/** Polling interval of the live views (`LIVE_REFRESH_INTERVAL_MS` in the frontend). */
export const LIVE_REFRESH_MS = 30_000

/** The one farm and plot `stubSession` serves (ids and names match the seed). */
export const STUB_FARM = { id: 1, name: T.farmFirst }
export const STUB_PLOT = { id: 1, name: T.plotName }

/**
 * A logged-in session served without the backend: seeds the tokens the auth
 * middleware reads and stubs the profile, farm list, plot list and plot detail
 * every dashboard page loads; any other API call answers 404. For specs that
 * observe frontend behaviour (polling, rendering) and must not depend on
 * seeded users. Routes a spec registers afterwards take precedence.
 */
export async function stubSession(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem('accessToken', 'e2e-access')
    localStorage.setItem('refreshToken', 'e2e-refresh')
  })
  const now = new Date().toISOString()
  const plot = {
    ...STUB_PLOT,
    description: '',
    geometry: null,
    centroid: null,
    label_point: null,
    area_hectares: '4.94',
    sensor_count: 1,
  }
  const byPath = (path: string) => (url: URL) => url.pathname.endsWith(path)
  // A glob like `**/api/**` would also catch dev-server modules such as
  // `/_nuxt/@fs/.../utils/api/tokens.ts`, and the app would never boot.
  await page.route((url) => url.pathname.startsWith('/api/'), (route) =>
    route.fulfill({ status: 404, json: { detail: 'No encontrado.' } }),
  )
  await page.route(byPath('/api/accounts/me/'), (route) =>
    route.fulfill({
      json: {
        id: 1,
        email: E2E_USER.email,
        farmer: {
          id: 1,
          first_name: 'Juan',
          last_name: 'Pérez',
          document_type: null,
          document_number: null,
          gender: null,
          phone_number: null,
          city: null,
          department: null,
          address: null,
          avatar: null,
          is_active: true,
          api_secret: 'e2e-secret',
          organization: null,
          created_at: now,
        },
      },
    }),
  )
  await page.route(byPath('/api/farm/farms/'), (route) =>
    route.fulfill({
      json: [{ ...STUB_FARM, address: '', location: null, boundary: null, created_at: now }],
    }),
  )
  await page.route(byPath(`/api/farm/farms/${STUB_FARM.id}/plots/`), (route) =>
    route.fulfill({ json: [plot] }),
  )
  await page.route(byPath(`/api/farm/plots/${STUB_PLOT.id}/`), (route) =>
    route.fulfill({
      json: { ...plot, farm: STUB_FARM, created_at: now, updated_at: now },
    }),
  )
}

/** The two stations `stubStations` serves for `STUB_FARM` (17 matches the dev DB's station id). */
export const STUB_STATIONS = {
  online: { id: 17, name: 'Estación La Loma' },
  stale: { id: 18, name: 'Estación El Bajo' },
}

/**
 * A weather-station card as `GET sensors/farms/<id>/stations/` serves it,
 * stamped relative to the run so the relative times stay plausible.
 */
export function stubStationCard(
  station: { id: number; name: string },
  status: string,
  temperature = 24.5,
) {
  const now = Date.now()
  const minutesAgo = (minutes: number) => new Date(now - minutes * 60_000).toISOString()
  const readingAt = minutesAgo(status === 'online' ? 5 : 90)
  return {
    id: station.id,
    farm_id: STUB_FARM.id,
    name: station.name,
    provider: 'weatherlink',
    is_active: true,
    status,
    last_reading_at: readingAt,
    latest: [
      { variable_id: 1, semantic_key: 'air_temperature', name: 'Temperatura del aire', unit: '°C', value: temperature, recorded_at: readingAt },
      { variable_id: 3, semantic_key: 'relative_humidity', name: 'Humedad relativa', unit: '%', value: 81, recorded_at: readingAt },
    ],
    sparkline: {
      semantic_key: 'air_temperature',
      unit: '°C',
      points: [3, 2, 1].map((hours, index) => ({
        t: minutesAgo(hours * 60),
        value: 20 + index,
      })),
    },
  }
}

/**
 * Serves `STUB_FARM`'s station list (one online, one stale) on top of
 * `stubSession`. Returns the request counter so live specs can watch polls.
 */
export async function stubStations(page: Page): Promise<{ requests: number }> {
  const counter = { requests: 0 }
  await page.route(
    (url) => url.pathname.endsWith(`/api/sensors/farms/${STUB_FARM.id}/stations/`),
    (route) => {
      counter.requests += 1
      return route.fulfill({
        json: [
          stubStationCard(STUB_STATIONS.online, 'online'),
          stubStationCard(STUB_STATIONS.stale, 'stale'),
        ],
      })
    },
  )
  return counter
}
