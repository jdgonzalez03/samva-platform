import { fetcher } from '#api/fetcher'
import type { LoginPayload, AuthResponse } from '../../types/auth'

export const authApi = {
  login: (payload: LoginPayload) =>
    fetcher.post<AuthResponse>('accounts/login/', payload),
}
