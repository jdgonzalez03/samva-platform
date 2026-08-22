<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

defineProps<{
  collapsed?: boolean
}>()

const { t } = useI18n()
const { farms, selectedFarm, selectFarm, isPending, isError, refetchFarms } =
  useSelectedFarm()

const items = computed<DropdownMenuItem[][]>(() => [
  farms.value.map((farm) => ({
    label: farm.name,
    icon: 'i-lucide-tractor',
    // Checkbox type so the active farm is conveyed by state, not colour alone.
    type: 'checkbox' as const,
    checked: farm.id === selectedFarm.value?.id,
    onSelect: () => {
      selectFarm(farm.id)
    },
  })),
])
</script>

<template>
  <div v-if="isPending" aria-busy="true" class="flex items-center gap-3 w-full">
    <USkeleton class="size-8 rounded-md shrink-0" />
    <USkeleton v-if="!collapsed" class="h-3.5 flex-1" />
  </div>

  <div
    v-else-if="isError"
    class="flex items-center gap-2 w-full text-sm text-muted"
  >
    <span v-if="!collapsed">{{ t('farm.menu.error') }}</span>
    <UButton
      variant="link"
      color="neutral"
      size="xs"
      class="p-0"
      :aria-label="collapsed ? t('farm.menu.retry') : undefined"
      @click="refetchFarms"
    >
      {{ collapsed ? '' : t('farm.menu.retry') }}
    </UButton>
  </div>

  <UButton
    v-else-if="!selectedFarm"
    :label="collapsed ? undefined : t('farm.menu.empty')"
    :aria-label="collapsed ? t('farm.menu.empty') : undefined"
    icon="i-lucide-tractor"
    color="neutral"
    variant="ghost"
    block
    disabled
    :square="collapsed"
    :class="[!collapsed && 'py-2']"
  />

  <UDropdownMenu
    v-else
    :items="items"
    :content="{ align: 'center', collisionPadding: 12 }"
    :ui="{
      content: collapsed ? 'w-40' : 'w-(--reka-dropdown-menu-trigger-width)',
    }"
  >
    <UButton
      :label="collapsed ? undefined : selectedFarm.name"
      :trailing-icon="collapsed ? undefined : 'i-lucide-chevrons-up-down'"
      :aria-label="t('farm.menu.label', { name: selectedFarm.name })"
      icon="i-lucide-tractor"
      color="neutral"
      variant="ghost"
      block
      :square="collapsed"
      class="data-[state=open]:bg-elevated"
      :class="[!collapsed && 'py-2']"
      :ui="{
        trailingIcon: 'text-dimmed',
      }"
    />
  </UDropdownMenu>
</template>
