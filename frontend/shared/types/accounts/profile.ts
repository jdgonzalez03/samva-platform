export interface FarmerProfile {
  id: number
  first_name?: string
  last_name?: string
  document_type?: string
  document_number?: string
  gender?: string
  phone_number?: string
  city?: string
  department?: string
  address?: string
  avatar?: string
  is_active: boolean
}

export interface Profile {
  id: number
  email: string
  farmer: FarmerProfile
}
