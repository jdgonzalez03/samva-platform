<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
// Type-only cross-layer import: erased at build, runtime deps stay domain → common.
import type { Profile } from '../../../accounts/app/types/profile'

interface Props {
  user: Profile
}

const props = defineProps<Props>()

const colorMode = useColorMode()
const { logout } = useAuth()
const { t, locale, locales } = useI18n()
const switchLocalePath = useSwitchLocalePath()

const displayName = computed(() => {
  if (props.user.farmer?.first_name)
    return `${props.user.farmer.first_name} ${props.user.farmer.last_name ?? ''}`.trim()
  return props.user.email
})

const avatarUrl = computed(() => getImageUrl(props.user.farmer.avatar))

const userItems = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: t('dashboard.userMenu.logout'),
      icon: 'i-lucide-log-out',
      onSelect: () => {
        logout()
      },
    },
  ],
  [
    {
      label: t('dashboard.userMenu.appearance'),
      icon: 'i-lucide-sun-moon',
      children: [
        {
          label: t('dashboard.userMenu.light'),
          icon: 'i-lucide-sun',
          type: 'checkbox',
          checked: colorMode.value === 'light',
          onUpdateChecked(checked: boolean) {
            if (checked) {
              colorMode.preference = 'light'
            }
          },
          onSelect(e: Event) {
            e.preventDefault()
          },
        },
        {
          label: t('dashboard.userMenu.dark'),
          icon: 'i-lucide-moon',
          type: 'checkbox',
          checked: colorMode.value === 'dark',
          onUpdateChecked(checked: boolean) {
            if (checked) {
              colorMode.preference = 'dark'
            }
          },
          onSelect(e: Event) {
            e.preventDefault()
          },
        },
      ],
    },
    {
      label: t('dashboard.userMenu.language'),
      icon: 'i-lucide-globe',
      children: locales.value.map((l) => ({
        // Each option is labeled in its own language (AC-A11Y-2).
        label: l.name ?? l.code,
        type: 'checkbox' as const,
        checked: locale.value === l.code,
        onUpdateChecked(checked: boolean) {
          if (checked) void navigateTo(switchLocalePath(l.code))
        },
        onSelect(e: Event) {
          e.preventDefault()
        },
      })),
    },
  ],
])
</script>

<template>
  <UDropdownMenu
    :items="userItems"
    :content="{ align: 'center', collisionPadding: 12 }"
    :ui="{ content: 'w-(--reka-dropdown-menu-trigger-width) min-w-48' }"
  >
    <UButton
      :label="displayName"
      :avatar="{
        src: avatarUrl,
        loading: 'lazy',
      }"
      trailing-icon="i-lucide-chevrons-up-down"
      color="neutral"
      variant="ghost"
      square
      class="w-full data-[state=open]:bg-elevated overflow-hidden"
      :ui="{
        trailingIcon: 'text-dimmed ms-auto',
      }"
    />
  </UDropdownMenu>
</template>
