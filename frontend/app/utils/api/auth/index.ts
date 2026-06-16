import type { LoginPayload, AuthResponse } from '#shared/types/auth/auth'
import { loginUser } from './endpoints/login'

export const authApi = {
  login: (payload: LoginPayload) => loginUser(payload),
}