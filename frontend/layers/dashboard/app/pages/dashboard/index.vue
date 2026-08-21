<script setup lang="ts">
definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t } = useI18n()

useHead(() => ({ title: t('dashboard.index.title') }))
</script>

<template>
  <UDashboardPanel id="home-dashboard">
    <template #header>
      <UDashboardNavbar
        :title="t('dashboard.index.title')"
        icon="i-lucide-house"
      />
    </template>

    <template #body>
      <UContainer class="flex flex-col gap-4 p-4">
        <p class="text-muted">
          {{ t('dashboard.index.welcome') }}
        </p>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
