<script setup lang="ts">
import { computed } from 'vue'
import type { CTASectionBlock } from '#shared/types/cms/blocks'
import { getBlockIcon } from '#shared/utils/icons'

interface Props {
  block: CTASectionBlock
}

const props = defineProps<Props>()

const buttonIcon = computed(() => getBlockIcon(props.block.value.cta_button.icon))
</script>

<template>
  <section class="bg-primary py-16 w-screen">
    <UContainer>
      <div class="text-center max-w-3xl mx-auto">
        <h2 class="text-4xl font-bold text-white">
          {{ block.value.heading.title }}
        </h2>

        <p class="text-lg text-white/80 mt-4">
          {{ block.value.heading.text }}
        </p>

        <UButton
          color="primary"
          :icon="buttonIcon"
          :href="block.value.cta_button.url"
          size="xl"
          class="bg-white text-gray-900 hover:bg-gray-100 mt-8"
        >
          {{ block.value.cta_button.text }}
        </UButton>
      </div>
    </UContainer>
  </section>
</template>
