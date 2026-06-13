<script setup lang="ts">
import { computed } from 'vue'
import type { FeatureHighlightBlock } from '#shared/types/cms/blocks'
import { getBlockIcon } from '#shared/utils/icons'
import { getBlockBackground } from '#shared/utils/block'

interface Props {
  block: FeatureHighlightBlock
}

const props = defineProps<Props>()

type BadgeColor = 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral'

const validBadgeColors: BadgeColor[] = ['primary', 'secondary', 'success', 'info', 'warning', 'error', 'neutral']

const bgClass = computed(() => getBlockBackground(props.block.value.background))
const imagen = computed(() => props.block.value.imagen)
const badgeIcon = computed(() => getBlockIcon(props.block.value.badge.icon))
const listIcon = computed(() => getBlockIcon(props.block.value.items.list_icon))
const badgeColor = computed<BadgeColor>(() => {
  const status = props.block.value.badge.status
  return validBadgeColors.includes(status as BadgeColor)
    ? (status as BadgeColor)
    : 'primary'
})
const contentCenter = computed(() => imagen ? '' : 'max-w-3xl mx-auto')
</script>

<template>
  <section :class="[bgClass, 'w-full py-16']">
    <UContainer>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        <div>
          <img
            v-if="imagen"
            :src="imagen.url"
            :alt="imagen.title"
            class="rounded-xl shadow-lg w-full"
          />
          <USkeleton v-else class="rounded-xl w-full aspect-4/3" />
        </div>

        <div :class="contentCenter">
          <UBadge
            :label="block.value.badge.text"
            :color="badgeColor"
            :icon="badgeIcon"
            size="lg"
          />

          <h2 class="text-3xl font-bold mt-4">
            {{ block.value.title.title }}
            <span class="text-primary">{{ block.value.title.highlight_text }}</span>
          </h2>

          <p class="text-lg text-gray-600 mt-4">
            {{ block.value.description }}
          </p>

          <ul class="mt-6 space-y-3">
            <li
              v-for="(item, index) in block.value.items.items"
              :key="index"
              class="flex items-start gap-3"
            >
              <UIcon :name="listIcon" class="size-5 text-primary mt-0.5 shrink-0" />
              <span>{{ item.text }}</span>
            </li>
          </ul>
        </div>
      </div>
    </UContainer>
  </section>
</template>
