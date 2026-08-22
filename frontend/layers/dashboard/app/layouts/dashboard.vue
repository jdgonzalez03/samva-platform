<script setup lang="ts">
import TractorIcon from '../../../common/app/components/icons/TractorIcon.vue'

const { user, profilePending, profileError, refetchProfile } = useAuth()
const { t } = useI18n()
const localePath = useLocalePath()

const colorMode = useColorMode()
if (colorMode.preference === 'light') {
  colorMode.preference = 'dark'
}
// History/Predictions stay hidden until those pages exist.
const links = computed(() => [
  {
    label: t('dashboard.nav.dashboard'),
    icon: 'i-lucide-layout-dashboard',
    to: localePath('/dashboard'),
  },
  {
    label: t('dashboard.nav.profile'),
    icon: 'i-lucide-user',
    to: localePath('/dashboard/profile'),
  },
])

const helpLinks = computed(() => [
  {
    label: t('dashboard.help.feedback'),
    icon: 'i-lucide-message-circle',
    to: 'mailto:jdgonzalez.urrego@unillanos.edu.co',
    target: '_blank',
  },
  {
    label: t('dashboard.help.support'),
    icon: 'i-lucide-info',
    to: 'https://wa.me/573014980859',
    target: '_blank',
  },
])
</script>

<template>
  <UDashboardGroup>
    <UDashboardSidebar side="left">
      <template #header="{ collapsed }">
        <NuxtLink
          :to="localePath('/dashboard')"
          class="flex items-center gap-2 px-3 py-1"
        >
          <div class="text-primary">
            <TractorIcon />
          </div>
          <Transition name="fade">
            <span v-if="!collapsed" class="text-lg font-bold truncate"
              >SAMVA</span
            >
          </Transition>
        </NuxtLink>
      </template>
      <template #default="{ collapsed }">
        <USeparator />
        <FarmsMenu :collapsed="collapsed" />
        <USeparator />
        <UNavigationMenu
          :items="links"
          :collapsed="collapsed"
          orientation="vertical"
          class="px-2"
        />
        <UNavigationMenu
          :items="helpLinks"
          :collapsed="collapsed"
          orientation="vertical"
          class="mt-auto"
        />
      </template>

      <template #footer>
        <div
          v-if="profilePending"
          aria-busy="true"
          class="flex items-center gap-3 w-full"
        >
          <USkeleton class="size-8 rounded-full shrink-0" />
          <div class="flex flex-col gap-1.5 flex-1 min-w-0">
            <USkeleton class="h-3.5 w-32" />
            <USkeleton class="h-3 w-24" />
          </div>
        </div>
        <DropDownUser v-else-if="user" :user="user" />
        <div
          v-else-if="profileError"
          class="flex items-center gap-2 w-full text-sm text-muted"
        >
          <span>{{ t('dashboard.profileUnavailable') }}</span>
          <UButton
            variant="link"
            color="neutral"
            size="xs"
            class="p-0"
            @click="refetchProfile"
          >
            {{ t('dashboard.retry') }}
          </UButton>
        </div>
      </template>
    </UDashboardSidebar>
    <div class="flex flex-1 min-w-0 overflow-hidden">
      <slot />
    </div>
  </UDashboardGroup>
</template>
