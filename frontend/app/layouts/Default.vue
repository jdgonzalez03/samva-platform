<script setup lang="ts">
import Header from '~/components/Header.vue'
import Footer from '~/components/Footer.vue'

const colorMode = useColorMode()

onMounted(() => {
  colorMode.preference = 'light'
})

</script>

<template>
  <Header />
    <UMain>
      <slot />
    </UMain>
  <Footer />
</template>
