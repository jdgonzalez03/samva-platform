import { fileURLToPath } from 'url'

export default defineNuxtConfig({
  $meta: { name: 'common' },
  imports: {
    // Shared constants (e.g. `LIVE_REFRESH_INTERVAL_MS`) as auto-imports, so
    // domain layers use them without a cross-layer file import.
    dirs: [fileURLToPath(new URL('./app/constants', import.meta.url))],
  },
  i18n: {
    locales: [
      { code: 'es', file: 'es.json' },
      { code: 'en', file: 'en.json' },
    ],
  },
})
