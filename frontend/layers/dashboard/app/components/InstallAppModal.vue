<script setup lang="ts">
// Manual install steps for browsers that never raise `beforeinstallprompt`
// (Safari on iOS, Firefox, in-app browsers) or have not raised it yet.
const open = defineModel<boolean>('open', { default: false })

const { t } = useI18n()

// iPadOS reports itself as a Mac, so a touch-capable "Mac" is an iPad.
const isIOS = ref(false)
onMounted(() => {
  isIOS.value =
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
})

const steps = computed(() =>
  isIOS.value
    ? [
        { icon: 'i-lucide-share', text: t('dashboard.installHelp.iosStep1') },
        {
          icon: 'i-lucide-square-plus',
          text: t('dashboard.installHelp.iosStep2'),
        },
        { icon: 'i-lucide-check', text: t('dashboard.installHelp.iosStep3') },
      ]
    : [
        {
          icon: 'i-lucide-ellipsis-vertical',
          text: t('dashboard.installHelp.otherStep1'),
        },
        {
          icon: 'i-lucide-download',
          text: t('dashboard.installHelp.otherStep2'),
        },
        {
          icon: 'i-lucide-check',
          text: t('dashboard.installHelp.otherStep3'),
        },
      ],
)
</script>

<template>
  <UModal
    v-model:open="open"
    :title="t('dashboard.installHelp.title')"
    :description="t('dashboard.installHelp.description')"
    :ui="{ footer: 'justify-end' }"
  >
    <template #body>
      <ol class="flex flex-col gap-4">
        <li
          v-for="(step, index) in steps"
          :key="step.icon"
          class="flex items-center gap-3"
        >
          <span
            class="flex size-8 shrink-0 items-center justify-center rounded-full bg-elevated text-sm font-semibold"
            aria-hidden="true"
            >{{ index + 1 }}</span
          >
          <UIcon :name="step.icon" class="size-5 shrink-0 text-muted" />
          <span class="text-sm">{{ step.text }}</span>
        </li>
      </ol>
    </template>
    <template #footer="{ close }">
      <UButton :label="t('dashboard.installHelp.close')" @click="close" />
    </template>
  </UModal>
</template>
