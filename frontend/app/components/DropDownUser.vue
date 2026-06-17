<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Profile } from '#shared/types/accounts/profile'

interface Props {
  user: Profile
}

const props = defineProps<Props>()

const colorMode = useColorMode()
const { logout } = useAuth()

const displayName = computed(() => {
  if (props.user.farmer?.first_name)
    return `${props.user.farmer.first_name} ${props.user.farmer.last_name ?? ''}`.trim()
  return props.user.email
})

const avatarUrl = getImageUrl(props.user.farmer.avatar)

const userItems = computed<DropdownMenuItem[][]>(() => [
  [
    { 
      label: 'Log out',
      icon: 'i-lucide-log-out',
      onSelect: () => {
        logout()
      }
    }
  ],
  [
    {
      label: 'Appearance',
      icon: 'i-lucide-sun-moon',
      children: [
        {
          label: 'Light',
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
          }
        },
        {
          label: 'Dark',
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
          }
        }
      ]
    }
  ]
])
</script>

<template>
  <UDropdownMenu 
    :items="userItems" 
    :content="{ align: 'center', collisionPadding: 12 }"
    :ui="{ content: 'w-(--reka-dropdown-menu-trigger-width) min-w-48' }">
    <UButton 
      :label="displayName" 
      :avatar="{
        src: avatarUrl,
        loading: 'lazy'
      }"
      trailing-icon="i-lucide-chevrons-up-down" 
      color="neutral" variant="ghost"
      square 
      class="w-full data-[state=open]:bg-elevated overflow-hidden" 
      :ui="{
        trailingIcon: 'text-dimmed ms-auto'
      }" />
  </UDropdownMenu>
</template>