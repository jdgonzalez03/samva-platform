<script setup lang="ts">
import Logo from './Logo.vue'

// Chrome text stays fixed Spanish (out of i18n scope); only the route target
// is locale-aware so the /en prefix survives the navigation.
const localePath = useLocalePath()
</script>

<template>
  <UHeader>
    <template #title>
      <Logo class="h-6 w-auto" />
    </template>

    <template #right>
      <UButton :to="localePath('/dashboard')" class="flex items-center gap-2">
        Ir al Dashboard
        <UIcon name="i-lucide-layout-dashboard" class="size-5" />
      </UButton>
    </template>
  </UHeader>
</template>
