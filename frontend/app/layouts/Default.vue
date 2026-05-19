<script setup lang="ts">
import Header from '~/components/Header.vue'
import Footer from '~/components/Footer.vue'
</script>

<template>
  <UApp>
    <Header />

    <UMain>
      <slot />
    </UMain>

    <Footer />
  </UApp>
</template>
