import type { IrrigationInput } from '../types/predictions'

// Mirrors the backend's `DEFAULT_AVERAGE_HOURS` and the window choices it
// accepts (1–`MAX_AVERAGE_HOURS`).
export const DEFAULT_AVERAGE_HOURS = 6
export const AVERAGE_HOURS_OPTIONS = [6, 12, 24] as const

export const HISTORY_PAGE_SIZE = 10

export const IRRIGATION_INPUTS: IrrigationInput[] = [
  'moisture',
  'temperature',
  'radiation',
]

export const INPUT_ICONS: Record<IrrigationInput, string> = {
  moisture: 'i-lucide-sprout',
  temperature: 'i-lucide-thermometer',
  radiation: 'i-lucide-sun',
}

// Presentation of each model the backend catalogue can list; a key missing
// here is a model this frontend cannot render yet, so its card is skipped.
export const MODEL_CARDS: Record<
  string,
  { icon: string; path: string; i18nKey: string }
> = {
  'fuzzy-irrigation': {
    icon: 'i-lucide-droplets',
    path: '/dashboard/predictions/fuzzy',
    i18nKey: 'fuzzyIrrigation',
  },
}

// Shared by the chart and its `<ClientOnly>` fallback so hydration never
// jumps. Keep the class and the pixel value in step (`h-64` = 256px).
export const CHART_HEIGHT_CLASS = 'h-64'
export const CHART_HEIGHT = 256
export const CHART_MARGIN = { top: 8, right: 16, bottom: 8, left: 8 }
