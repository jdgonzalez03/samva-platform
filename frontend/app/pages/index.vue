<script setup lang="ts">
definePageMeta({
  layout: 'default',
})
import { useRuntimeConfig } from '#imports'
import type { LandingData } from '#shared/types/cms/landing'

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
  <div class="container flex flex-col items-center justify-center gap-12 px-4 py-4 pb-0 mx-auto">
    <template v-if="data?.body" v-for="block in data.body" :key="block.id">
      <cms-hero-section v-if="block.type === 'hero'" :block="block" />
      <cms-vision-mision v-else-if="block.type === 'vision_mision'" :block="block" />
      <cms-benefits-section v-else-if="block.type === 'benefits'" :block="block" />
      <cms-team-section v-else-if="block.type === 'team'" :block="block" />
      <cms-feature-highlight v-else-if="block.type === 'feature_highlight'" :block="block" />
      <cms-cta-section v-else-if="block.type === 'cta_section'" :block="block" />
    </template>
  </div>
</template>