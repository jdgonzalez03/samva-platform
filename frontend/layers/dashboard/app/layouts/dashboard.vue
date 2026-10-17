<script setup lang="ts">
import TractorIcon from '../../../common/app/components/icons/TractorIcon.vue'

const { user, profilePending, profileError, refetchProfile } = useAuth()
const { t } = useI18n()
const localePath = useLocalePath()

const colorMode = useColorMode()
if (colorMode.preference === 'light') {
  colorMode.preference = 'dark'
}
// Plain strings to routes the sensors, predictions and assistant layers own —
// the dashboard layer gains no dependency on them.
const links = computed(() => [
  {
    label: t('dashboard.nav.dashboard'),
    icon: 'i-lucide-layout-dashboard',
    to: localePath('/dashboard'),
    exact: true,
  },
  {
    label: t('dashboard.nav.plots'),
    icon: 'i-lucide-land-plot',
    to: localePath('/dashboard/plots'),
  },
  {
    label: t('dashboard.nav.history'),
    icon: 'i-lucide-history',
    to: localePath('/dashboard/history'),
  },
  {
    label: t('dashboard.nav.sensors'),
    icon: 'i-lucide-radio-tower',
    to: localePath('/dashboard/sensors'),
  },
  {
    label: t('dashboard.nav.stations'),
    icon: 'i-lucide-cloud-sun',
    to: localePath('/dashboard/stations'),
  },
  {
    label: t('dashboard.nav.predictions'),
    icon: 'i-lucide-brain-circuit',
    to: localePath('/dashboard/predictions'),
    exact: true,
  },
  // A sibling indented under "Predicciones" rather than one of its `children`:
  // a vertical UNavigationMenu renders the expand chevron of a parent that is
  // also a link as a `<span aria-expanded>`, which axe flags as critical.
  {
    label: t('dashboard.nav.fuzzyLogic'),
    icon: 'i-lucide-waves',
    to: localePath('/dashboard/predictions/fuzzy'),
    class: 'in-data-[collapsed=false]:ps-7',
  },
  {
    label: t('dashboard.nav.assistant'),
    icon: 'i-lucide-bot',
    to: localePath('/dashboard/assistant'),
    class: 'in-data-[collapsed=false]:ps-7',
  },
  {
    label: t('dashboard.nav.profile'),
    icon: 'i-lucide-user',
    to: localePath('/dashboard/profile'),
  },
])

// Undefined on the server. Only some browsers raise the native install prompt
// (never iOS), so without it the entry opens manual steps instead.
const { $pwa } = useNuxtApp()
const installHelpOpen = ref(false)

// Whether the app is already installed is only known in the browser; showing
// the entry after mount keeps the hydrated markup identical to the SSR one.
const mounted = ref(false)
onMounted(() => {
  mounted.value = true
})

const installApp = async () => {
  if ($pwa?.showInstallPrompt) {
    await $pwa.install()
    return
  }
  installHelpOpen.value = true
}

const installLink = computed(() =>
  mounted.value && !$pwa?.isPWAInstalled
    ? [
        {
          label: t('dashboard.help.installApp'),
          icon: 'i-lucide-download',
          onSelect: () => {
            void installApp()
          },
        },
      ]
    : [],
)

const helpLinks = computed(() => [
  ...installLink.value,
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
    <InstallAppModal v-model:open="installHelpOpen" />
  </UDashboardGroup>
</template>
