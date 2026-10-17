<script setup lang="ts">
const props = defineProps<{ farmName: string; now: number }>()

const { t, locale } = useI18n()
const { user } = useAuth()

const greeting = computed(() => {
  const hour = new Date(props.now).getHours()
  const key = hour < 12 ? 'morning' : hour < 19 ? 'afternoon' : 'evening'
  const text = t(`dashboard.home.greeting.${key}`)
  const name = user.value?.farmer?.first_name
  return name
    ? t('dashboard.home.greeting.named', { greeting: text, name })
    : text
})

const today = computed(() =>
  new Intl.DateTimeFormat(locale.value, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(new Date(props.now)),
)
</script>

<template>
  <div
    class="relative shrink-0 overflow-hidden rounded-xl border border-default bg-linear-to-br from-primary/15 via-elevated/40 to-default p-6 sm:p-8"
  >
    <UIcon
      name="i-lucide-sprout"
      class="pointer-events-none absolute -right-6 -bottom-8 size-48 text-primary/10"
      aria-hidden="true"
    />
    <!-- The greeting depends on the viewer's clock and the profile, both
         client-side only, so the server renders the skeleton instead. -->
    <ClientOnly>
      <p class="text-sm font-medium text-primary first-letter:uppercase">
        {{ today }}
      </p>
      <p class="mt-1 text-2xl font-semibold text-highlighted sm:text-3xl">
        {{ greeting }}
      </p>
      <template #fallback>
        <USkeleton class="h-4 w-40" />
        <USkeleton class="mt-2 h-8 w-72" />
      </template>
    </ClientOnly>
    <p class="mt-2 text-muted">
      {{ t('dashboard.home.greeting.summary', { farm: farmName }) }}
    </p>
  </div>
</template>
