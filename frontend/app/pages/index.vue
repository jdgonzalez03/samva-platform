<script setup lang="ts">
definePageMeta({
  layout: 'default',
})
import { useRuntimeConfig } from '#imports'
import type { LandingData } from '#shared/types/cms/landing'
import VisionMision from '../components/cms/vision-mision.vue'
import HeroSection from '../components/cms/hero-section.vue'
import BenefitsSection from '../components/cms/benefits-section.vue'

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
  <div class="container flex flex-col items-center justify-center gap-12 px-4 py-4 mx-auto">
    <template v-if="data?.body" v-for="block in data.body" :key="block.id">
      <hero-section v-if="block.type === 'hero'" :block="block" />
      <vision-mision v-else-if="block.type === 'vision_mision'" :block="block" />
      <benefits-section v-else-if="block.type === 'benefits'" :block="block" />
    </template>
  </div>
</template>