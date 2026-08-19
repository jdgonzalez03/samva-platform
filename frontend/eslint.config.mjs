// @ts-check
import eslintConfigPrettier from 'eslint-config-prettier'
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  // Project-specific overrides
  {
    rules: {
      'vue/multi-word-component-names': 'off',
      // Formatting rule not covered by eslint-config-prettier
      'vue/first-attribute-linebreak': 'off',
    },
  },
  // Formatting is Prettier's job — disable any ESLint rule that conflicts with it
  eslintConfigPrettier,
)
