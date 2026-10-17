<script setup lang="ts">
import { TIPS_DISMISSED_KEY } from '../../constants/assistant'

const { t, tm, rt } = useI18n()

// Hidden until mounted: the dismissal lives in this browser's storage, which
// the server cannot read, so rendering it there would flash and then vanish.
const visible = ref(false)

const items = computed(() =>
  (tm('assistant.tips.items') as unknown[]).map((item) =>
    rt(item as Parameters<typeof rt>[0]),
  ),
)

onMounted(() => {
  try {
    visible.value = localStorage.getItem(TIPS_DISMISSED_KEY) !== '1'
  } catch {
    visible.value = true
  }
})

const dismiss = (): void => {
  visible.value = false
  try {
    localStorage.setItem(TIPS_DISMISSED_KEY, '1')
  } catch {
    // Private mode or blocked storage: the tips simply come back next visit.
  }
}
</script>

<template>
  <UAlert
    v-if="visible"
    :title="t('assistant.tips.title')"
    icon="i-lucide-lightbulb"
    color="info"
    variant="subtle"
    close
    class="text-start"
  >
    <!-- Own button: the default one carries Nuxt UI's untranslated label. -->
    <template #close>
      <UButton
        icon="i-lucide-x"
        color="neutral"
        variant="link"
        :aria-label="t('assistant.tips.close')"
        @click="dismiss"
      />
    </template>
    <template #description>
      <ul class="mt-1 list-disc ps-4 space-y-1">
        <li v-for="item in items" :key="item">{{ item }}</li>
      </ul>
    </template>
  </UAlert>
</template>
