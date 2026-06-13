<script setup lang="ts">
import { computed } from 'vue'
import type { TeamBlock } from '#shared/types/cms/blocks'
import { getBlockBackground } from '#shared/utils/block'
interface Props {
  block: TeamBlock
}

const props = defineProps<Props>()

const bgClass = computed(() => getBlockBackground(props.block.value.background))
</script>

<template>
  <section :class="[bgClass, 'w-full py-16']">
    <UContainer>
      <div class="text-center mb-12">
        <h2 class="text-3xl font-bold text-gray-900">{{ block.value.heading.title }}</h2>
        <p class="text-lg text-gray-600 mt-2 max-w-2xl mx-auto">{{ block.value.heading.text }}</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <UPageCard
          v-for="(member, index) in block.value.members"
          :key="index"
          variant="soft"
          spotlight
        >
          <div class="flex flex-col items-center text-center">
            <UUser
              :name="member.name"
              :description="member.description"
              orientation="vertical"
            >
              <template #avatar>
                <div class="flex justify-center">
                  <UAvatar
                    v-if="member.image"
                    :src="member.image.url"
                    :alt="member.image.title"
                    size="xl"
                  />
                  <USkeleton v-else class="rounded-full size-16" />
                </div>
              </template>
            </UUser>

            <p class="text-sm font-medium text-primary-600 mt-3">
              {{ member.role }}
            </p>
          </div>
        </UPageCard>
      </div>
    </UContainer>
  </section>
</template>
