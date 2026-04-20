<script setup lang="ts">
import TractorIcon from '~/components/icons/TractorIcon.vue'

interface Props {
  isBgWhite?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isBgWhite: true
})
</script>

<template>
  <div class="flex items-center gap-2">
    <TractorIcon class="h-6 w-6 text-primary" />
    <h1 class="font-bold" :class="props.isBgWhite ? 'text-black' : 'text-white'">S.A.M.V.A.</h1>
  </div>
</template>