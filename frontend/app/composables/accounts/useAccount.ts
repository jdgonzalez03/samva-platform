import type { UpdateProfilePayload } from '#shared/types/accounts/profile'
import { accountsApi } from '#api/accounts/index'

export function useAccount() {

  const updateProfile = async (payload: UpdateProfilePayload) => {
    const updated = await accountsApi.updateProfile(payload)
    return updated
  }

  return { updateProfile }
}
