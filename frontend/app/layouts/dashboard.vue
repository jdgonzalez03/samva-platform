<script setup lang="ts">

import TracktorIcon from '../components/icons/TractorIcon.vue'

const { user, loading } = useAuth() 

const colorMode = useColorMode()
if (colorMode.preference === 'light') {
  colorMode.preference = 'dark'
}
const links = [
  { label: 'Dashboard', icon: 'i-lucide-layout-dashboard', to: '/dashboard' },
  { label: 'History', icon: 'i-lucide-history', to: '/dashboard/history' },
  { label: 'Predictions', icon: 'i-lucide-trending-up', to: '/dashboard/predictions' },
  { label: 'Profile', icon: 'i-lucide-user', to: '/dashboard/profile'}
]

const helpLinks = [
  { label: 'Feedback', icon: 'i-lucide-message-circle', to: 'mailto:jdgonzalez.urrego@unillanos.edu.co', target: '_blank' }, 
  { label: 'Help & Support', icon: 'i-lucide-info', to: 'https://wa.me/573014980859', target: '_blank' },
]
</script>

<template>
  <UDashboardGroup>
    <UDashboardSidebar side="left">
      <template #header="{ collapsed }">
        <div class="flex items-center gap-2 px-3 py-1 cursor-pointer" @click="navigateTo('/dashboard')">
          <div class="text-primary">
            <TracktorIcon />
          </div>
          <Transition name="fade">
            <span v-if="!collapsed" class="text-lg font-bold truncate">SAMVA</span>
          </Transition>
        </div>
      </template>
      <USeparator />
      <DashboardFarmsMenu />
      <USeparator />
      <UNavigationMenu :items="links" orientation="vertical" class="px-2" />
      <UNavigationMenu :items="helpLinks" orientation="vertical" class="mt-auto" />

      <template #footer>
        <div v-if="loading" class="flex items-center gap-3 w-full">
          <USkeleton class="size-8 rounded-full shrink-0" />
          <div class="flex flex-col gap-1.5 flex-1 min-w-0">
            <USkeleton class="h-3.5 w-32" />
            <USkeleton class="h-3 w-24" />
          </div>
        </div>
        <DropDownUser v-else-if="user" :user="user" />
      </template>
    </UDashboardSidebar>
    <div class="flex flex-1 min-w-0 overflow-hidden">
      <slot />
    </div>
  </UDashboardGroup>
</template>
