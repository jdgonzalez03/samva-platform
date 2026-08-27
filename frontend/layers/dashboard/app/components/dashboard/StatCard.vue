<script setup lang="ts">
defineProps<{
  title: string
  icon: string
}>()
</script>

<template>
  <UPageCard
    :icon="icon"
    :title="title"
    variant="subtle"
    :ui="{
      container: 'gap-y-1.5',
      wrapper: 'items-start',
      leading:
        'p-2.5 rounded-full bg-primary/10 ring ring-inset ring-primary/25 flex-col',
      title: 'font-normal text-muted text-xs uppercase',
    }"
    class="lg:rounded-none lg:first:rounded-l-lg lg:last:rounded-r-lg hover:z-1"
  >
    <slot />
  </UPageCard>
</template>
