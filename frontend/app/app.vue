<script setup lang="ts">
import { en, es } from '@nuxt/ui/locale'

const { locale } = useI18n()
const i18nHead = useLocaleHead()

useHead(() => ({
  htmlAttrs: { lang: i18nHead.value.htmlAttrs?.lang },
}))

const uiLocale = computed(() => (locale.value === 'en' ? en : es))
</script>

<template>
  <UApp :locale="uiLocale">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
