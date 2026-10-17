import { fileURLToPath } from 'url'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  modules: [
    '@nuxt/ui',
    '@nuxt/icon',
    '@nuxt/eslint',
    '@nuxtjs/i18n',
    '@vite-pwa/nuxt',
  ],
  pwa: {
    registerType: 'autoUpdate',
    // Icons, favicon and their <head> links are generated from public/logo.svg
    // by pwa-assets.config.ts at build time.
    pwaAssets: { config: true },
    manifest: {
      name: 'SAMVA',
      short_name: 'SAMVA',
      description:
        'Monitoreo de sensores y predicción de riego para fincas agrícolas.',
      lang: 'es',
      start_url: '/dashboard',
      scope: '/',
      display: 'standalone',
      theme_color: '#171717',
      background_color: '#171717',
    },
    workbox: {
      // Pages are server-rendered per user, so only the static build assets are
      // precached; navigations and /api/ always go to the network, which keeps
      // the dashboard from showing stale sensor readings as current.
      navigateFallback: null,
      globPatterns: ['**/*.{js,css,png,svg,ico,woff2}'],
    },
    client: {
      installPrompt: true,
    },
  },
  icon: {
    // Off the default `/api/_nuxt_icon`: nginx sends every `/api/` request to
    // Django, so icons not inlined by SSR would 404 behind the proxy.
    localApiEndpoint: '/_nuxt_icon',
  },
  i18n: {
    defaultLocale: 'es',
    strategy: 'prefix_except_default',
    // Locale metadata lives here; message files ship per layer
    // (layers/<name>/i18n/locales/{es,en}.json) and are merged by the module.
    locales: [
      { code: 'es', language: 'es-CO', name: 'Español' },
      { code: 'en', language: 'en', name: 'English' },
    ],
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_redirected',
      redirectOn: 'root',
      fallbackLocale: 'es',
    },
  },
  css: [
    fileURLToPath(
      new URL('./layers/common/app/assets/main.css', import.meta.url),
    ),
  ],
  eslint: {
    config: {
      stylistic: false,
    },
  },
  alias: {
    // The common HTTP stack only (fetcher, tokens, errors) — domain api modules
    // live inside their own layer and are not exposed here.
    '#api': fileURLToPath(
      new URL('./layers/common/app/utils/api', import.meta.url),
    ),
    // Reserved for genuinely cross-layer types; empty today.
    '#shared': fileURLToPath(
      new URL('./layers/common/shared', import.meta.url),
    ),
  },
  runtimeConfig: {
    apiBaseServer:
      process.env.NUXT_API_BASE_SERVER || 'http://localhost:8000/api',
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '/api',
      mediaBase: process.env.NUXT_PUBLIC_MEDIA_BASE || 'http://localhost:8000',
      // Swagger is served by Django and not proxied under the frontend's `/api`.
      apiDocsUrl:
        process.env.NUXT_PUBLIC_API_DOCS_URL ||
        'http://localhost:8000/api/docs/',
    },
  },

  // typescript: {
  //   typeCheck: true,
  // }
})
