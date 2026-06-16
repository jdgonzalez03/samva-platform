import type { LoginPayload } from '#shared/types/auth/auth'
import type { Profile } from '#shared/types/accounts/profile'

import { authApi } from '#api/auth/index'
import { accountsApi } from '#api/accounts/index'
import { setTokens, clearTokens, hasTokens } from '#api/tokens'

export function useAuth() {

  const isAuthenticated = useState('auth', () => false)
  const user = useState<Profile | null>('user', () => null)
  const loading = useState('auth-loading', () => false)

  const router = useRouter();

  const login = async (payload: LoginPayload) => {
    loading.value = true
    try {
      const data = await authApi.login(payload)
      setTokens(data.tokens.access, data.tokens.refresh)
      user.value = await accountsApi.getMe()
      isAuthenticated.value = true
    } finally {
      loading.value = false
    }
  }
  
  const fetchMe = async () => {
    if (!hasTokens()) return
    try {
      user.value = await accountsApi.getMe()
      isAuthenticated.value = true
    } catch {
      logout()
    }
  }
  
  const logout = () => {
    clearTokens()
    user.value = null
    isAuthenticated.value = false
    router.push('/login')
  }
  
  return {
    isAuthenticated: readonly(isAuthenticated),
    user: readonly(user),
    loading: readonly(loading),
    login,
    logout,
    fetchMe,
  }
}
