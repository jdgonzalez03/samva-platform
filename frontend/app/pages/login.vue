<script setup lang="ts">
definePageMeta({
  layout: 'login',
})

import * as z from 'zod';
import TractorIcon from '~/components/icons/TractorIcon.vue';

import type { FormSubmitEvent, AuthFormField } from '@nuxt/ui';
// TODO: Must be moved to a composable or a separate file to clean up the component and avoid unnecessary re-renders
const fields: AuthFormField[] = [{
  name: 'email',
  label: 'Email',
  type: 'email',
  placeholder: 'Enter your email',
  required: true
}, {
  name: 'password',
  label: 'Password',
  type: 'password',
  placeholder: 'Enter your password',
  required: true
}]

const schema = z.object({
  email: z.email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters long')
})

type Schema = z.output<typeof schema>

function onSubmit(payload: FormSubmitEvent<Schema>) {
  console.log('Form submitted with values:', payload);
}

</script>

<template>
  <UContainer class="min-h-screen flex flex-col items-center justify-center">
    <UPageCard>
      <UAuthForm
        title="Login"
        description="Enter your credentials to access your account."
        :icon="TractorIcon"
        :fields="fields"
        @submit="onSubmit"
      />
    </UPageCard>
  </UContainer>
</template>