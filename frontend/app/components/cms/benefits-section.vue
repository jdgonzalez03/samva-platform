<script setup lang="ts">
import { computed } from "vue"
import type { BenefitsBlock } from "#shared/types/cms/blocks"
import { getBlockIcon } from "#shared/utils/icons"

interface Props {
  block: BenefitsBlock
}

const props = defineProps<Props>()

const bgClass = computed(() => {
  const bgMap: Record<string, string> = {
    white: "bg-white",
    gray: "bg-gray-100",
    green: "bg-green-100",
  }
  return bgMap[props.block.value.background] || "bg-white"
})
</script>

<template>
  <section :class="[bgClass, 'w-full py-16']">
    <UContainer>
      <div class="text-center mb-12">
        <h2 class="text-3xl font-bold text-gray-900">{{ block.value.heading.title }}</h2>
        <p class="text-lg text-gray-600 mt-2 max-w-2xl mx-auto">{{ block.value.heading.text }}</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <UPageCard
          v-for="(item, index) in block.value.items"
          :key="index"
          :title="item.title"
          :description="item.description"
          :icon="getBlockIcon(item.icon)"
          variant="soft"
        />
      </div>
    </UContainer>
  </section>
</template>
