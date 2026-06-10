<script setup lang="ts">
definePageMeta({
  layout: 'default',
})
import { useRuntimeConfig } from '#imports'
import type { LandingData } from '#shared/types/cms/landing'
import HeroSection from '../components/cms/hero-section.vue'

// TODO: Extract maybe to a composable or something, but for now it's fine here
const config = useRuntimeConfig()
const { data } = await useFetch<LandingData>(
  `${config.public.apiBase}/cms/landing/`,
  {
    baseURL: config.apiBaseServer,
    server: true,
  }
)

</script>

<template>
  <div class="container flex flex-col items-center justify-center gap-12 px-4 py-16 mx-auto">
    <template v-if="data?.body" v-for="block in data.body" :key="block.id">
      <HeroSection v-if="block.type === 'hero'" :block="block" />
    </template>
  </div>
</template>