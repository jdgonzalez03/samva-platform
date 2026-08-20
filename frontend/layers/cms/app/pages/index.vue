<script setup lang="ts">
import { cmsApi } from '../utils/api/cms'

definePageMeta({
  layout: 'default',
})

const { data } = await useAsyncData('cms-landing', () => cmsApi.getLanding())

useHead({ title: () => data.value?.title ?? 'S.A.M.V.A.' })
</script>

<template>
  <div
    class="container flex flex-col items-center justify-center gap-12 px-4 py-4 pb-0 mx-auto"
  >
    <template v-for="block in data?.body ?? []" :key="block.id">
      <cms-hero-section v-if="block.type === 'hero'" :block="block" />
      <cms-vision-mision
        v-else-if="block.type === 'vision_mision'"
        :block="block"
      />
      <cms-benefits-section
        v-else-if="block.type === 'benefits'"
        :block="block"
      />
      <cms-team-section v-else-if="block.type === 'team'" :block="block" />
      <cms-feature-highlight
        v-else-if="block.type === 'feature_highlight'"
        :block="block"
      />
      <cms-cta-section
        v-else-if="block.type === 'cta_section'"
        :block="block"
      />
    </template>
  </div>
</template>
