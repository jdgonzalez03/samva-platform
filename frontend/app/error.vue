<script setup lang="ts">
import type { NuxtError } from '#app'
import { en, es } from '@nuxt/ui/locale'

const props = defineProps<{
  error: NuxtError
}>()

const { t, locale } = useI18n()
const localePath = useLocalePath()
const i18nHead = useLocaleHead()

const isNotFound = computed(() => props.error.status === 404)

const heading = computed(() =>
  isNotFound.value
    ? t('common.error.notFoundHeading')
    : t('common.error.genericHeading'),
)

const description = computed(() =>
  isNotFound.value
    ? t('common.error.notFoundDescription')
    : t('common.error.genericDescription'),
)

// error.vue replaces app.vue, so it binds <html lang> itself.
useHead(() => ({
  title: isNotFound.value
    ? t('common.error.notFoundTitle')
    : t('common.error.genericTitle'),
  htmlAttrs: { lang: i18nHead.value.htmlAttrs?.lang },
}))

const uiLocale = computed(() => (locale.value === 'en' ? en : es))

const goHome = () => clearError({ redirect: localePath('/') })
</script>

<template>
  <UApp :locale="uiLocale">
    <UContainer
      class="min-h-screen flex flex-col items-center justify-center text-center gap-4 py-16"
    >
      <UIcon
        name="i-lucide-tractor"
        class="size-16 text-primary"
        aria-hidden="true"
      />
      <p class="text-6xl font-bold text-primary" aria-hidden="true">
        {{ error.status }}
      </p>
      <h1 class="text-2xl font-semibold text-highlighted">
        {{ heading }}
      </h1>
      <p class="text-muted max-w-md">
        {{ description }}
      </p>
      <UButton
        size="lg"
        color="primary"
        icon="i-lucide-house"
        class="mt-2"
        @click="goHome"
      >
        {{ t('common.error.backHome') }}
      </UButton>
    </UContainer>
  </UApp>
</template>
