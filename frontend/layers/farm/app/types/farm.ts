export interface Farm {
  id: number
  name: string
  address: string
  created_at: string
}

export interface Plot {
  id: number
  name: string
  description: string
  // DRF serializes DecimalField as a string.
  area_hectares: string | null
}
