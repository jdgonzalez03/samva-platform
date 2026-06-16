<script setup lang="ts">
const colorMode = useColorMode()

onMounted(() => {
  colorMode.preference = 'light'
})
</script>

<template>
  <div
    class="fixed inset-0 bg-cover bg-center z-0"
    style="background-image: url('/images/bg-login-page.svg')"
  />

  <UMain>
    <slot />
  </UMain>
</template>