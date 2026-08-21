<script setup lang="ts">
import * as z from 'zod'
import type { FetchError } from 'ofetch'
import TractorIcon from '../../../common/app/components/icons/TractorIcon.vue'

import type { FormSubmitEvent, AuthFormField } from '@nuxt/ui'

definePageMeta({
  layout: 'login',
  middleware: ['guest'],
})

const { t } = useI18n()
const localePath = useLocalePath()

useHead(() => ({ title: t('auth.login.pageTitle') }))

const { login, loading } = useAuth()
const toast = useToast()

const fields = computed<AuthFormField[]>(() => [
  {
    name: 'email',
    label: t('auth.login.emailLabel'),
    type: 'email',
    placeholder: t('auth.login.emailPlaceholder'),
    required: true,
  },
  {
    name: 'password',
    label: t('auth.login.passwordLabel'),
    type: 'password',
    placeholder: t('auth.login.passwordPlaceholder'),
    required: true,
  },
])

// Rebuilt per locale so zod validation messages follow the active language.
const schema = computed(() =>
  z.object({
    email: z.email(t('auth.validation.email')),
    password: z.string().min(6, t('auth.validation.password')),
  }),
)

type Schema = z.output<typeof schema.value>

async function onSubmit(payload: FormSubmitEvent<Schema>) {
  try {
    await login({ email: payload.data.email, password: payload.data.password })
    toast.add({
      title: t('auth.login.successTitle'),
      description: t('auth.login.successDescription'),
      color: 'success',
    })
    await navigateTo(localePath('/dashboard'))
  } catch (error) {
    const fetchError = error as FetchError<{ error?: string }>
    toast.add({
      title: t('auth.login.errorTitle'),
      description: fetchError.data?.error ?? t('auth.login.errorDescription'),
      color: 'error',
    })
  }
}
</script>

<template>
  <UContainer
    class="relative min-h-screen flex flex-col items-center justify-center"
  >
    <div class="absolute top-4 right-4">
      <LanguageSwitcher />
    </div>
    <UPageCard>
      <UAuthForm
        :title="t('auth.login.title')"
        :description="t('auth.login.description')"
        :icon="TractorIcon"
        :fields="fields"
        :schema="schema"
        :submit="{
          label: t('auth.login.submit'),
          color: 'primary',
        }"
        :loading="loading"
        @submit="onSubmit"
      />
    </UPageCard>
  </UContainer>
</template>
