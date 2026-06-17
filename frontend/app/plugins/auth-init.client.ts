import { useAuth } from '#imports'
import { hasTokens } from '#api/tokens'

export default defineNuxtPlugin(async () => {
  if (!hasTokens()) return

  const { fetchMe } = useAuth()
  await fetchMe()
})
