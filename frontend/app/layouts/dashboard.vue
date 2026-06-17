<script setup lang="ts">

import TracktorIcon from '../components/icons/TractorIcon.vue'

const colorMode = useColorMode()
if (colorMode.preference === 'light') {
  colorMode.preference = 'dark'
}
const links = [
  { label: 'Dashboard', icon: 'i-lucide-layout-dashboard', to: '/dashboard' },
  { label: 'Historial', icon: 'i-lucide-history', to: '/dashboard/history' },
  { label: 'Predicciones', icon: 'i-lucide-trending-up', to: '/dashboard/predictions' },
]

const helpLinks = [
  { label: 'Feedback', icon: 'i-lucide-message-circle', to: 'mailto:jdgonzalez.urrego@unillanos.edu.co', target: '_blank' }, 
  { label: 'Help & Support', icon: 'i-lucide-info', to: 'https://wa.me/573014980859', target: '_blank' },
]
</script>

<template>
  <UDashboardGroup>
    <UDashboardSidebar side="left" collapsible>
      <template #header="{ collapsed }">
        <div class="flex items-center gap-2 px-3 py-1">
          <div class="text-primary">
            <TracktorIcon />
          </div>
          <Transition name="fade">
            <span v-if="!collapsed" class="text-lg font-bold truncate">SAMVA</span>
          </Transition>
        </div>
      </template>

      <UNavigationMenu :items="links" orientation="vertical" class="px-2" />
      <UNavigationMenu :items="helpLinks" orientation="vertical" class="mt-auto" />

      <template #footer>
        <DropDownUser />
      </template>
    </UDashboardSidebar>
    <slot />
  </UDashboardGroup>
</template>
