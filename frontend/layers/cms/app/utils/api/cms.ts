import { fetcher } from '#api/fetcher'
import type { LandingData } from '../../types/landing'

export const cmsApi = {
  getLanding: () => fetcher.get<LandingData>('cms/landing/'),
}
