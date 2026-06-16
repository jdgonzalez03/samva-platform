<script setup lang="ts">
definePageMeta({
  layout: 'login',
  middleware: ['guest'],
})

import * as z from 'zod'
import TractorIcon from '~/components/icons/TractorIcon.vue'

import type { FormSubmitEvent, AuthFormField } from '@nuxt/ui'

const { login, loading } = useAuth()
const toast = useToast()

const fields: AuthFormField[] = [{
  name: 'email',
  label: 'Email',
  type: 'email',
  placeholder: 'you@example.com',
  required: true,
}, {
  name: 'password',
  label: 'Password',
  type: 'password',
  placeholder: '••••••••',
  required: true,
}]

const schema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters long'),
})

type Schema = z.output<typeof schema>

async function onSubmit(payload: FormSubmitEvent<Schema>) {
  try {
    await login({ email: payload.data.email, password: payload.data.password })
    toast.add({ title: 'Welcome back', description: 'You have been logged in successfully', color: 'success' })
    await navigateTo('/dashboard')
  } catch (error: any) {
    toast.add({
      title: 'Login Failed',
      description: error.message || 'An error occurred while logging in',
      color: 'error',
    })
  }
}

</script>

<template>
  <UContainer class="min-h-screen flex flex-col items-center justify-center">
    <UPageCard>
      <UAuthForm
        title="Welcome back"
        description="Enter your credentials to access your S.A.M.V.A account."
        :icon="TractorIcon"
        :fields="fields"
        :submit="{
          label: 'Sign in',
          color: 'primary',
        }"
        :loading="loading"
        @submit="onSubmit"
      />
    </UPageCard>
  </UContainer>
</template>