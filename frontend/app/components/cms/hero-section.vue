<script setup lang="ts">
import { computed } from 'vue'
import TractorIcon from '~/components/icons/TractorIcon.vue'
import type { StreamBlock, HeroBlock } from '#shared/types/cms/blocks'

interface Props {
  block: HeroBlock
}

const props = defineProps<Props>()

const ctaUrl = computed(() => props.block.value.cta_button.url || '#')

const buttonIconComponent = computed(() => {
  const icon = props.block.value.cta_button.icon?.trim().toLowerCase() || ''
  if (!icon || icon.includes('agriculture')) {
    return TractorIcon
  }
  return undefined
})

</script>

<template>
  <div class="relative w-full overflow-hidden bg-cover bg-center text-white"
    style="background-image: url('/images/hero-image.jpg');">
    <div class="absolute inset-0 bg-black/40 pointer-events-none" />

    <div class="relative z-10">
      <UPageHero :headline="block.value.badge">
        <template #headline>
          <p
            class="text-sm font-semibold uppercase tracking-wide text-primary-500 bg-primary/10 px-3 py-1 rounded-full inline-block mb-4 border border-primary/20">
            {{ block.value.badge }}
          </p>
        </template>

        <template #title>
          <p class="text-white">{{ block.value.title.title }} </p>
          <span class="text-primary">
            {{ block.value.title.highlight_text }}
          </span>
        </template>

        <template #description>
          <p class="text-lg text-white max-w-2xl text-center mx-auto">
            {{ block.value.description }}
          </p>
        </template>

        <template #links>
          <UButton color="primary" :href="ctaUrl" class="inline-flex items-center gap-2" size="xl">
            <component v-if="buttonIconComponent" :is="buttonIconComponent" class="size-5 text-white" />
            {{ block.value.cta_button.text }}
          </UButton>
        </template>
      </UPageHero>
    </div>
  </div>
</template>
