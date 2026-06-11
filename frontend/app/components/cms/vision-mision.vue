<script setup lang="ts">
import { computed } from 'vue'
import type { VisionMisionBlock } from '#shared/types/cms/blocks'
import { getBlockBackground } from '#shared/utils/block'

interface Props {
  block: VisionMisionBlock
}

const props = defineProps<Props>()

const bgClass = computed(() => getBlockBackground(props.block.value.background))

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