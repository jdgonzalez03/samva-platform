
## Arrow functions in stores and composables

All functions inside Pinia stores and Vue composables must be arrow functions, not `function` declarations.

**Correct:**
```ts
const fetchMe = async () => { ... }
const clearUser = () => { user.value = null }
const waitForReady = () => readyPromise
```

**Wrong:**
```ts
function fetchMe() { ... }
async function fetchMe() { ... }
function clearUser() { user.value = null }
```

---
## Icons

Always use Lucide icons (`i-lucide-*`). Never use heroicons or any other icon set.

**Correct:**
```vue
<UIcon name="i-lucide-circle-check" />
<UIcon name="i-lucide-circle-x" />
<UIcon name="i-lucide-loader-circle" class="animate-spin" />
```

**Wrong:**
```vue
<UIcon name="i-heroicons-check-circle" />
<UIcon name="i-heroicons-x-circle" />
```

---
## Nuxt UI component prefix

All Nuxt UI components use the `U` prefix, not `Nuxt`. This is the default use of NuxtUI

**Wrong:** `<NuxtIcon>`, `<NuxtButton>`, `<NuxtForm>`, `<NuxtInput>`

**Correct:** `<UIcon>`, `<UButton>`, `<UForm>`, `<UInput>`
