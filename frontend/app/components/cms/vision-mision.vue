<script setup lang="ts">
import { computed } from 'vue'
import type { VisionMisionBlock } from '#shared/types/cms/blocks'

interface Props {
  block: VisionMisionBlock
}

const props = defineProps<Props>()

const bgClass = computed(() => {
  if (props.block.value.background) {
    return `bg-${props.block.value.background}`
  }
  return 'bg-white'
})

</script>

<template>
  <div :class="bgClass" class="w-full grid grid-cols-1 gap-8 md:grid-cols-2">
    <UPageCard
      :title="block.value.vision.title"
      :description="block.value.vision.description"
      icon="i-lucide-eye"
      variant="soft"
      spotlight
    />

    <UPageCard
      :title="block.value.mision.title"
      :description="block.value.mision.description"
      icon="i-lucide-flag"
      variant="soft"
      spotlight
    />
  </div>
</template>