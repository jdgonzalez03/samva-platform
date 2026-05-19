<script setup lang="ts">
import Logo from '~/components/Logo.vue'
</script>

<template>
  <UHeader>
    <template #title>
      <Logo class="h-6 w-auto" />
    </template>

    <template #right>
      <UButton
        to="/dashboard"
        class="flex items-center gap-2"
      >
        Ir al Dashboard
        <UIcon name="i-lucide-layout-dashboard" class="size-5" />
      </UButton>
    </template>
  </UHeader>
</template>
