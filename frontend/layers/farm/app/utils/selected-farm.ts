const SELECTED_FARM_KEY = 'selectedFarmId'

export const getStoredFarmId = (): number | null => {
  if (!import.meta.client) return null

  const stored = localStorage.getItem(SELECTED_FARM_KEY)
  if (stored === null) return null

  const farmId = Number.parseInt(stored, 10)
  return Number.isNaN(farmId) ? null : farmId
}

export const setStoredFarmId = (farmId: number): void => {
  if (!import.meta.client) return
  localStorage.setItem(SELECTED_FARM_KEY, String(farmId))
}
