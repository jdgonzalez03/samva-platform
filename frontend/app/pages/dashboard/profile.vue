<script setup lang="ts">
import type { UpdateProfilePayload } from '#shared/types/accounts/profile'
import { getImageUrl } from '../../utils/image'

definePageMeta({
  middleware: ['auth'],
  layout: 'dashboard',
})

const { updateProfile } = useAccount()
const { user, fetchMe } = useAuth()


const toast = useToast()
const saving = ref(false)
const avatarFile = ref<File | null>(null)
const avatarPreview = ref<string | null>(null)

const documentTypeItems = [
  { label: 'Identity Card', value: 'CC' },
  { label: 'Foreign ID Card', value: 'CE' },
  { label: 'Passport', value: 'PASSPORT' },
]

const genderItems = [
  { label: 'Male', value: 'M' },
  { label: 'Female', value: 'F' },
]

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
  return new Date(user.value.farmer.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
  })
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

onMounted(async () => {
  if (!user.value) {
    await fetchMe()
  }
})

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
  saving.value = true
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
    await updateProfile(payload)
    await fetchMe()
    toast.add({ title: 'Profile updated', description: 'Changes saved successfully', color: 'success' })
  } catch {
    toast.add({ title: 'Update error', description: 'Could not save changes. Please try again.', color: 'error' })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <DashboardProfileSkeleton v-if="!user" />

  <UDashboardPanel v-else id="profile-dashboard">
    <template #header>
      <UDashboardNavbar title="My Profile" icon="i-lucide-user" />
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
              <div class="flex flex-col items-center text-center gap-3 pb-4 border-b border-default">
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
                    style="background: linear-gradient(135deg, #3B6D11 0%, #639922 100%); width: 72px; height: 72px;"
                  >
                    {{ initials }}
                  </div>

                  <UButton
                    as="label"
                    color="neutral"
                    variant="ghost"
                    size="xs"
                    class="absolute -bottom-1 -right-1 rounded-full cursor-pointer shadow-sm"
                    :disabled="saving"
                  >
                    <template #leading>
                      <UIcon name="i-lucide-camera" class="size-3.5" />
                    </template>
                    <input
                      type="file"
                      accept="image/*"
                      class="hidden"
                      @change="onAvatarSelected"
                    />
                  </UButton>
                </div>

                <div>
                  <p class="font-medium text-base text-highlighted">
                    {{ form.first_name || form.last_name
                      ? `${form.first_name} ${form.last_name}`.trim()
                      : user.email }}
                  </p>
                  <p class="text-sm text-muted">{{ user.email }}</p>
                </div>

                <UBadge color="success" variant="subtle" size="sm">
                  <UIcon name="i-lucide-leaf" class="size-3 mr-1" />
                  Farmer
                </UBadge>
              </div>

              <div class="mt-4 flex flex-col gap-2.5">
                <p class="text-xs font-medium uppercase tracking-widest text-muted mb-1">
                  Account Information
                </p>

                <div v-if="memberSince" class="flex items-center gap-2 text-sm text-muted">
                  <UIcon name="i-lucide-calendar" class="size-4 shrink-0" />
                  <span>Member since <span class="text-default font-medium">{{ memberSince }}</span></span>
                </div>

                <div v-if="form.city || form.department" class="flex items-center gap-2 text-sm text-muted">
                  <UIcon name="i-lucide-map-pin" class="size-4 shrink-0" />
                  <span class="text-default">
                    {{ [form.city, form.department].filter(Boolean).join(', ') }}
                  </span>
                </div>

                <div v-if="form.phone_number" class="flex items-center gap-2 text-sm text-muted">
                  <UIcon name="i-lucide-phone" class="size-4 shrink-0" />
                  <span class="text-default">{{ form.phone_number }}</span>
                </div>
              </div>
            </UCard>
            <!-- Organization Information -->
            <UCard v-if="user.farmer.organization">
              <template #header>
                <p class="text-xs font-medium uppercase tracking-widest text-muted">
                  Organization
                </p>
              </template>

              <div class="flex flex-col gap-2.5">
                <div v-if="user.farmer.organization.name" class="flex items-center gap-2 text-sm">
                  <UIcon name="i-lucide-building" class="size-4 shrink-0 text-muted" />
                  <span class="text-default font-medium">{{ user.farmer.organization.name }}</span>
                </div>

                <div v-if="user.farmer.organization.nit" class="flex items-center gap-2 text-sm text-muted">
                  <UIcon name="i-lucide-hash" class="size-4 shrink-0" />
                  <span class="text-default">NIT {{ user.farmer.organization.nit }}</span>
                </div>

                <div v-if="user.farmer.organization.created_at" class="flex items-center gap-2 text-sm text-muted">
                  <UIcon name="i-lucide-calendar-plus" class="size-4 shrink-0" />
                  <span>Registered <span class="text-default font-medium">{{ new Date(user.farmer.organization.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' }) }}</span></span>
                </div>
              </div>
            </UCard>

            <UCard v-else>
              <div class="flex flex-col items-center text-center gap-2 py-2">
                <UIcon name="i-lucide-building" class="size-8 text-muted" />
                <p class="text-sm text-muted">No organization</p>
              </div>
            </UCard>
          </div>

          <div class="flex flex-col gap-4">
            <!-- Personal Information form -->
            <UCard>
              <template #header>
                <p class="text-xs font-medium uppercase tracking-widest text-muted">
                  Personal Information
                </p>
              </template>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormField name="email" label="Email">
                  <UInput
                    :model-value="user.email"
                    disabled
                    class="w-full"
                    icon="i-lucide-mail"
                    placeholder="you@example.com"
                  />
                </UFormField>

                <UFormField name="first_name" label="First Name">
                  <UInput
                    v-model="form.first_name"
                    placeholder="Joe"
                    class="w-full"
                  />
                </UFormField>

                <UFormField name="last_name" label="Last Name">
                  <UInput
                    v-model="form.last_name"
                    placeholder="Doe"
                    class="w-full"
                  />
                </UFormField>

                <UFormField name="gender" label="Gender">
                  <USelect
                    v-model="form.gender"
                    :items="genderItems"
                    placeholder="Select"
                    class="w-full"
                  />
                </UFormField>

                <UFormField name="document_type" label="Document Type">
                  <USelect
                    v-model="form.document_type"
                    :items="documentTypeItems"
                    placeholder="Select"
                    class="w-full"
                  />
                </UFormField>

                <UFormField name="document_number" label="Document Number">
                  <UInput
                    v-model="form.document_number"
                    placeholder="Document Number"
                    class="w-full"
                  />
                </UFormField>

                <UFormField name="phone_number" label="Phone">
                  <UInput
                    v-model="form.phone_number"
                    placeholder="+57 300 000 0000"
                    icon="i-lucide-phone"
                    class="w-full"
                  />
                </UFormField>
              </div>
            </UCard>
            <!-- Location Information form -->
            <UCard>
              <template #header>
                <p class="text-xs font-medium uppercase tracking-widest text-muted">
                  Location
                </p>
              </template>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormField name="city" label="City">
                  <UInput
                    v-model="form.city"
                    placeholder="City"
                    class="w-full"
                  />
                </UFormField>

                <UFormField name="department" label="Department">
                  <UInput
                    v-model="form.department"
                    placeholder="Department"
                    class="w-full"
                  />
                </UFormField>

                <UFormField name="address" label="Address" class="md:col-span-2">
                  <UInput
                    v-model="form.address"
                    placeholder="Street, number, neighborhood…"
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
                Save changes
              </UButton>
            </div>
          </div>
        </UForm>
      </UContainer>
    </template>
  </UDashboardPanel>
</template>