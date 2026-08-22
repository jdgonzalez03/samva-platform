import { fileURLToPath } from 'url'

export default defineNuxtConfig({
  $meta: { name: 'farm' },
  imports: {
    // Exposes the farm composables as auto-imports: the dashboard layer consumes
    // `useSelectedFarm`/`useFarmPlotsQuery` without a runtime cross-layer import.
    dirs: [fileURLToPath(new URL('./app/composables', import.meta.url))],
  },
  i18n: {
    locales: [
      { code: 'es', file: 'es.json' },
      { code: 'en', file: 'en.json' },
    ],
  },
})
