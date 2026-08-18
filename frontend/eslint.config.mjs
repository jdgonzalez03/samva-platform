// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  // Project-specific overrides
  {
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
)
