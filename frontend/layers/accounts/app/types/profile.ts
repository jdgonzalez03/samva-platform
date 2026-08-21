export interface OrganizationProfile {
  id: number
  name: string | null
  nit: string | null
  created_at: string
}

export interface FarmerProfile {
  id: number
  first_name: string | null
  last_name: string | null
  document_type: 'CC' | 'CE' | 'PASSPORT' | null
  document_number: string | null
  gender: 'M' | 'F' | null
  phone_number: string | null
  city: string | null
  department: string | null
  address: string | null
  avatar: string | null
  is_active: boolean
  organization: OrganizationProfile | null
  created_at: string
}

export interface Profile {
  id: number
  email: string
  farmer: FarmerProfile
}

export interface UpdateProfilePayload {
  first_name?: string
  last_name?: string
  document_type?: string
  document_number?: string
  gender?: string
  phone_number?: string
  city?: string
  department?: string
  address?: string
  avatar?: File
}
