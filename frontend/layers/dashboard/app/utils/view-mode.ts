export type ViewMode = 'map' | 'list'

export const VIEW_MODES: ViewMode[] = ['map', 'list']

export const DEFAULT_VIEW_MODE: ViewMode = 'map'

const VIEW_MODE_KEY = 'dashboardViewMode'

export const parseViewMode = (value: unknown): ViewMode | null =>
  VIEW_MODES.includes(value as ViewMode) ? (value as ViewMode) : null

export const getStoredViewMode = (): ViewMode | null => {
  if (!import.meta.client) return null
  return parseViewMode(localStorage.getItem(VIEW_MODE_KEY))
}

export const setStoredViewMode = (mode: ViewMode): void => {
  if (!import.meta.client) return
  localStorage.setItem(VIEW_MODE_KEY, mode)
}
