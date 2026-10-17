import {
  defineConfig,
  minimal2023Preset,
} from '@vite-pwa/assets-generator/config'

// The padded icons (maskable, Apple touch) fill their margin with the logo's own
// green so the rounded square blends into a full-bleed tile once the OS masks it.
const LOGO_GREEN = '#16a34a'

export default defineConfig({
  headLinkOptions: { preset: '2023' },
  preset: {
    ...minimal2023Preset,
    maskable: {
      ...minimal2023Preset.maskable,
      resizeOptions: { background: LOGO_GREEN },
    },
    apple: {
      ...minimal2023Preset.apple,
      resizeOptions: { background: LOGO_GREEN },
    },
  },
  images: ['public/logo.svg'],
})
