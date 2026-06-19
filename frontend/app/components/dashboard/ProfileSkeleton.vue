<script setup lang="ts">
</script>

<template>
  <UDashboardPanel id="profile-dashboard">
    <template #header>
      <UDashboardNavbar title="Profile" icon="i-lucide-user" />
    </template>

    <template #body>
      <UContainer class="p-4 space-y-8">
        <div class="flex items-center gap-4">
          <USkeleton class="size-20 rounded-full shrink-0" />
          <div class="space-y-2">
            <USkeleton class="h-5 w-48" />
            <USkeleton class="h-4 w-32" />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="i in 8" :key="i" class="space-y-2">
            <USkeleton class="h-3.5 w-24" />
            <USkeleton class="h-10 w-full rounded-md" />
          </div>
        </div>

        <USkeleton class="h-10 w-32 rounded-md" />
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
