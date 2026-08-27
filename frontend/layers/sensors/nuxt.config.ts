import { fileURLToPath } from 'url'

export default defineNuxtConfig({
  $meta: { name: 'sensors' },
  imports: {
    dirs: [fileURLToPath(new URL('./app/composables', import.meta.url))],
  },
  i18n: {
    locales: [
      { code: 'es', file: 'es.json' },
      { code: 'en', file: 'en.json' },
    ],
  },
})
