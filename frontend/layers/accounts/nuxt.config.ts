import { fileURLToPath } from 'url'

export default defineNuxtConfig({
  $meta: { name: 'accounts' },
  imports: {
    // Exposes `accountsApi` as an auto-import: the auth layer consumes it for
    // session restore/login without a runtime cross-layer file import.
    dirs: [fileURLToPath(new URL('./app/utils/api', import.meta.url))],
  },
  i18n: {
    locales: [
      { code: 'es', file: 'es.json' },
      { code: 'en', file: 'en.json' },
    ],
  },
})
