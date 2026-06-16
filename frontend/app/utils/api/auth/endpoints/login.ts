import type { LoginPayload, AuthResponse } from '#shared/types/auth/auth'

export async function loginUser(payload: LoginPayload): Promise<AuthResponse> {
  const config = useRuntimeConfig()
  const response = await fetch(`${config.public.apiBase}/accounts/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || 'Login failed')
  }

  return response.json()
}

