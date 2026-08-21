<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const { t, locale, locales } = useI18n()
const switchLocalePath = useSwitchLocalePath()

const items = computed<DropdownMenuItem[]>(() =>
  locales.value.map((l) => ({
    // Each option is labeled in its own language (name from the i18n config).
    label: l.name ?? l.code,
    type: 'checkbox',
    checked: locale.value === l.code,
    onUpdateChecked: (checked: boolean) => {
      if (checked) void navigateTo(switchLocalePath(l.code))
    },
    onSelect: (e: Event) => {
      e.preventDefault()
    },
  })),
)
</script>

<template>
  <UDropdownMenu :items="items" :content="{ align: 'end' }">
    <UButton
      icon="i-lucide-globe"
      color="neutral"
      variant="ghost"
      :aria-label="t('common.changeLanguage')"
    />
  </UDropdownMenu>
</template>
