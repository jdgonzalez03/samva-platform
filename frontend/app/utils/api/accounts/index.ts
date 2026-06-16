import { fetcher } from '../fetcher'
import type { Profile } from '#shared/types/accounts/profile'

export const accountsApi = {
  getMe: () => fetcher.get<Profile>('accounts/me/'),
}
