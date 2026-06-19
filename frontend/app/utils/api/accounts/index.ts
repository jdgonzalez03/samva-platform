import { fetcher } from '../fetcher'
import type { Profile, UpdateProfilePayload } from '#shared/types/accounts/profile'

export const accountsApi = {
  getMe: () => fetcher.get<Profile>('accounts/me/'),
  updateProfile: (payload: UpdateProfilePayload) => {
    const hasFiles = payload.avatar

    if (hasFiles) {
      const formData = new FormData();
      Object.entries(payload).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          formData.append(key, value);
        }
      });
      return fetcher.patchFormData<Profile>('accounts/me/', formData)
    }
    return fetcher.patch<Profile>('accounts/me/', payload)
  }
}
