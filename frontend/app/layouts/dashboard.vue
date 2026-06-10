<script setup lang="ts">
const colorMode = useColorMode()

if (colorMode.preference === 'light') {
  colorMode.preference = 'dark'
}
</script>

<template>
  <slot />
</template>