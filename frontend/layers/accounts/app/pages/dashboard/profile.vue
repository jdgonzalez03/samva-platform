<script setup lang="ts">
import type { UpdateProfilePayload } from '../../types/profile'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { t, locale } = useI18n()

useHead(() => ({ title: t('accounts.profile.pageTitle') }))

const { data: user, isPending, isError, refetch } = useProfileQuery()
const updateProfileMutation = useUpdateProfileMutation()

const toast = useToast()
const saving = computed(() => updateProfileMutation.isPending.value)
const avatarFile = ref<File | null>(null)
const avatarPreview = ref<string | null>(null)

const documentTypeItems = computed(() => [
  { label: t('accounts.profile.documentTypes.cc'), value: 'CC' },
  { label: t('accounts.profile.documentTypes.ce'), value: 'CE' },
  { label: t('accounts.profile.documentTypes.passport'), value: 'PASSPORT' },
])

const genderItems = computed(() => [
  { label: t('accounts.profile.genders.male'), value: 'M' },
  { label: t('accounts.profile.genders.female'), value: 'F' },
])

const form = reactive({
  first_name: '',
  last_name: '',
  document_type: undefined as string | undefined,
  document_number: '',
  gender: undefined as string | undefined,
  phone_number: '',
  city: '',
  department: '',
  address: '',
})

const initials = computed(() => {
  const f = form.first_name?.trim()?.[0] ?? ''
  const l = form.last_name?.trim()?.[0] ?? ''
  return (f + l).toUpperCase() || '?'
})

const avatarSrc = computed(() => {
  if (avatarPreview.value) return avatarPreview.value
  if (user.value?.farmer?.avatar) return getImageUrl(user.value.farmer.avatar)
  return null
})

const memberSince = computed(() => {
  if (!user.value?.farmer?.created_at) return null
  return formatMonthYear(user.value.farmer.created_at, locale.value)
})

const organizationRegistered = computed(() => {
  if (!user.value?.farmer?.organization?.created_at) return null
  return formatMonthYear(
    user.value.farmer.organization.created_at,
    locale.value,
  )
})

watchEffect(() => {
  if (!user.value) return
  const f = user.value.farmer
  form.first_name = f.first_name ?? ''
  form.last_name = f.last_name ?? ''
  form.document_type = f.document_type ?? undefined
  form.document_number = f.document_number ?? ''
  form.gender = f.gender ?? undefined
  form.phone_number = f.phone_number ?? ''
  form.city = f.city ?? ''
  form.department = f.department ?? ''
  form.address = f.address ?? ''
})

function retryLoad() {
  void refetch()
}

function onAvatarSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  avatarFile.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    avatarPreview.value = e.target?.result as string
  }
  reader.readAsDataURL(file)
}

async function handleSubmit() {
  try {
    const payload: UpdateProfilePayload = {
      first_name: form.first_name || undefined,
      last_name: form.last_name || undefined,
      document_type: form.document_type,
      document_number: form.document_number || undefined,
      gender: form.gender,
      phone_number: form.phone_number || undefined,
      city: form.city || undefined,
      department: form.department || undefined,
      address: form.address || undefined,
    }
    if (avatarFile.value) {
      payload.avatar = avatarFile.value
    }
    // mutateAsync resolves after the profile query refetch (mutation
    // onSuccess awaits the invalidation), so the toast fires on fresh data.
    await updateProfileMutation.mutateAsync(payload)
    toast.add({
      title: t('accounts.profile.updateSuccessTitle'),
      description: t('accounts.profile.updateSuccessDescription'),
      color: 'success',
    })
  } catch {
    toast.add({
      title: t('accounts.profile.updateErrorTitle'),
      description: t('accounts.profile.updateErrorDescription'),
      color: 'error',
    })
  }
}
</script>

<template>
  <DashboardProfileSkeleton v-if="isPending" />
  <UDashboardPanel v-else-if="isError || !user" id="profile-dashboard">
    <template #header>
      <UDashboardNavbar
        :title="t('accounts.profile.pageTitle')"
        icon="i-lucide-user"
      />
    </template>

    <template #body>
      <UContainer class="py-10 px-4">
        <div class="flex flex-col items-center gap-3 text-center">
          <UIcon
            name="i-lucide-circle-alert"
            class="size-8 text-muted"
            aria-hidden="true"
          />
          <p class="text-default">
            {{ t('accounts.profile.loadError') }}
          </p>
          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide-refresh-cw"
            @click="retryLoad"
          >
            {{ t('accounts.profile.retry') }}
          </UButton>
        </div>
      </UContainer>
    </template>
  </UDashboardPanel>
  <UDashboardPanel v-else id="profile-dashboard">
    <template #header>
      <UDashboardNavbar
        :title="t('accounts.profile.pageTitle')"
        icon="i-lucide-user"
      />
    </template>

    <template #body>
      <UContainer class="py-6 px-4">
        <UForm
          :state="form"
          class="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6 items-start"
          @submit="handleSubmit"
        >
          <div class="flex flex-col gap-4">
            <!-- User Information -->
            <UCard>
              <div
                class="flex flex-col items-center text-center gap-3 pb-4 border-b border-default"
              >
                <div class="relative group">
                  <UAvatar
                    v-if="avatarSrc"
                    :src="avatarSrc"
                    :alt="`${form.first_name} ${form.last_name}`"
                    size="3xl"
                  />
                  <div
                    v-else
                    class="w-18 h-18 rounded-full flex items-center justify-center text-2xl font-medium text-white select-none"
                    style="
                      background: linear-gradient(
                        135deg,
                        #3b6d11 0%,
                        #639922 100%
                      );
                      width: 72px;
                      height: 72px;
                    "
                  >
                    {{ initials }}
                  </div>

                  <UButton
                    as="label"
                    color="neutral"
                    variant="ghost"
                    size="xs"
                    class="absolute -bottom-1 -right-1 rounded-full cursor-pointer shadow-sm focus-within:ring-2 focus-within:ring-primary"
                    :disabled="saving"
                  >
                    <template #leading>
                      <UIcon name="i-lucide-camera" class="size-3.5" />
                    </template>
                    <!-- sr-only (not hidden): keeps the input focusable and its
                         aria-label exposed; Enter/Space opens the picker natively. -->
                    <input
                      type="file"
                      accept="image/*"
                      class="sr-only"
                      :aria-label="t('accounts.profile.changeAvatar')"
                      :disabled="saving"
                      @change="onAvatarSelected"
                    />
                  </UButton>
                </div>

                <div>
                  <p class="font-medium text-base text-highlighted">
                    {{
                      form.first_name || form.last_name
                        ? `${form.first_name} ${form.last_name}`.trim()
                        : user.email
                    }}
                  </p>
                  <p class="text-sm text-muted">{{ user.email }}</p>
                </div>

                <UBadge color="success" variant="subtle" size="sm">
                  <UIcon name="i-lucide-leaf" class="size-3 mr-1" />
                  {{ t('accounts.profile.farmerBadge') }}
                </UBadge>
              </div>

              <div class="mt-4 flex flex-col gap-2.5">
                <p
                  class="text-xs font-medium uppercase tracking-widest text-muted mb-1"
                >
                  {{ t('accounts.profile.accountInformation') }}
                </p>

                <div
                  v-if="memberSince"
                  class="flex items-center gap-2 text-sm text-muted"
                >
                  <UIcon name="i-lucide-calendar" class="size-4 shrink-0" />
                  <span
                    >{{ t('accounts.profile.memberSince') }}
                    <span class="text-default font-medium">{{
                      memberSince
                    }}</span></span
                  >
                </div>

                <div
                  v-if="form.city || form.department"
                  class="flex items-center gap-2 text-sm text-muted"
                >
                  <UIcon name="i-lucide-map-pin" class="size-4 shrink-0" />
                  <span class="text-default">
                    {{
                      [form.city, form.department].filter(Boolean).join(', ')
                    }}
                  </span>
                </div>

                <div
                  v-if="form.phone_number"
                  class="flex items-center gap-2 text-sm text-muted"
                >
                  <UIcon name="i-lucide-phone" class="size-4 shrink-0" />
                  <span class="text-default">{{ form.phone_number }}</span>
                </div>
              </div>
            </UCard>
            <!-- Organization Information -->
            <UCard v-if="user.farmer.organization">
              <template #header>
                <p
                  class="text-xs font-medium uppercase tracking-widest text-muted"
                >
                  {{ t('accounts.profile.organization') }}
                </p>
              </template>

              <div class="flex flex-col gap-2.5">
                <div
                  v-if="user.farmer.organization.name"
                  class="flex items-center gap-2 text-sm"
                >
                  <UIcon
                    name="i-lucide-building"
                    class="size-4 shrink-0 text-muted"
                  />
                  <span class="text-default font-medium">{{
                    user.farmer.organization.name
                  }}</span>
                </div>

                <div
                  v-if="user.farmer.organization.nit"
                  class="flex items-center gap-2 text-sm text-muted"
                >
                  <UIcon name="i-lucide-hash" class="size-4 shrink-0" />
                  <span class="text-default"
                    >{{ t('accounts.profile.nit') }}
                    {{ user.farmer.organization.nit }}</span
                  >
                </div>

                <div
                  v-if="user.farmer.organization.created_at"
                  class="flex items-center gap-2 text-sm text-muted"
                >
                  <UIcon
                    name="i-lucide-calendar-plus"
                    class="size-4 shrink-0"
                  />
                  <span
                    >{{ t('accounts.profile.registered') }}
                    <span class="text-default font-medium">{{
                      organizationRegistered
                    }}</span></span
                  >
                </div>
              </div>
            </UCard>

            <UCard v-else>
              <div class="flex flex-col items-center text-center gap-2 py-2">
                <UIcon name="i-lucide-building" class="size-8 text-muted" />
                <p class="text-sm text-muted">
                  {{ t('accounts.profile.noOrganization') }}
                </p>
              </div>
            </UCard>
          </div>

          <div class="flex flex-col gap-4">
            <!-- Personal Information form -->
            <UCard>
              <template #header>
                <p
                  class="text-xs font-medium uppercase tracking-widest text-muted"
                >
                  {{ t('accounts.profile.personalInformation') }}
                </p>
              </template>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormField
                  name="email"
                  :label="t('accounts.profile.fields.email')"
                >
                  <UInput
                    :model-value="user.email"
                    disabled
                    class="w-full"
                    icon="i-lucide-mail"
                    :placeholder="t('accounts.profile.fields.emailPlaceholder')"
                  />
                </UFormField>

                <UFormField
                  name="first_name"
                  :label="t('accounts.profile.fields.firstName')"
                >
                  <UInput
                    v-model="form.first_name"
                    :placeholder="
                      t('accounts.profile.fields.firstNamePlaceholder')
                    "
                    class="w-full"
                  />
                </UFormField>

                <UFormField
                  name="last_name"
                  :label="t('accounts.profile.fields.lastName')"
                >
                  <UInput
                    v-model="form.last_name"
                    :placeholder="
                      t('accounts.profile.fields.lastNamePlaceholder')
                    "
                    class="w-full"
                  />
                </UFormField>

                <UFormField
                  name="gender"
                  :label="t('accounts.profile.fields.gender')"
                >
                  <USelect
                    v-model="form.gender"
                    :items="genderItems"
                    :placeholder="
                      t('accounts.profile.fields.selectPlaceholder')
                    "
                    class="w-full"
                  />
                </UFormField>

                <UFormField
                  name="document_type"
                  :label="t('accounts.profile.fields.documentType')"
                >
                  <USelect
                    v-model="form.document_type"
                    :items="documentTypeItems"
                    :placeholder="
                      t('accounts.profile.fields.selectPlaceholder')
                    "
                    class="w-full"
                  />
                </UFormField>

                <UFormField
                  name="document_number"
                  :label="t('accounts.profile.fields.documentNumber')"
                >
                  <UInput
                    v-model="form.document_number"
                    :placeholder="
                      t('accounts.profile.fields.documentNumberPlaceholder')
                    "
                    class="w-full"
                  />
                </UFormField>

                <UFormField
                  name="phone_number"
                  :label="t('accounts.profile.fields.phone')"
                >
                  <UInput
                    v-model="form.phone_number"
                    :placeholder="t('accounts.profile.fields.phonePlaceholder')"
                    icon="i-lucide-phone"
                    class="w-full"
                  />
                </UFormField>
              </div>
            </UCard>
            <!-- Location Information form -->
            <UCard>
              <template #header>
                <p
                  class="text-xs font-medium uppercase tracking-widest text-muted"
                >
                  {{ t('accounts.profile.location') }}
                </p>
              </template>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormField
                  name="city"
                  :label="t('accounts.profile.fields.city')"
                >
                  <UInput
                    v-model="form.city"
                    :placeholder="t('accounts.profile.fields.cityPlaceholder')"
                    class="w-full"
                  />
                </UFormField>

                <UFormField
                  name="department"
                  :label="t('accounts.profile.fields.department')"
                >
                  <UInput
                    v-model="form.department"
                    :placeholder="
                      t('accounts.profile.fields.departmentPlaceholder')
                    "
                    class="w-full"
                  />
                </UFormField>

                <UFormField
                  name="address"
                  :label="t('accounts.profile.fields.address')"
                  class="md:col-span-2"
                >
                  <UInput
                    v-model="form.address"
                    :placeholder="
                      t('accounts.profile.fields.addressPlaceholder')
                    "
                    icon="i-lucide-map-pin"
                    class="w-full"
                  />
                </UFormField>
              </div>
            </UCard>
            <!-- Form action -->
            <div class="flex justify-end">
              <UButton
                type="submit"
                color="success"
                :loading="saving"
                :disabled="saving"
                icon="i-lucide-save"
                class="cursor-pointer"
              >
                {{ t('accounts.profile.saveChanges') }}
              </UButton>
            </div>
          </div>
        </UForm>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
