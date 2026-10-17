type BadgeColor = 'success' | 'warning' | 'neutral'

interface StatusLook {
  color: BadgeColor
  icon: string
}

// Keyed by the backend's `status`; `stationStatusLook` falls back for a key the
// client does not know yet.
export const STATION_STATUS_LOOKS: Record<string, StatusLook> = {
  online: { color: 'success', icon: 'i-lucide-wifi' },
  stale: { color: 'warning', icon: 'i-lucide-clock-alert' },
  never_seen: { color: 'neutral', icon: 'i-lucide-circle-dashed' },
  inactive: { color: 'neutral', icon: 'i-lucide-power-off' },
}

export const FALLBACK_STATUS_LOOK: StatusLook = {
  color: 'neutral',
  icon: 'i-lucide-circle-help',
}

// Shared by the sparkline and its `<ClientOnly>` fallback so hydration never
// jumps. Keep the class and the pixel value in step (`h-12` = 48px).
export const STATION_SPARKLINE_HEIGHT_CLASS = 'h-12'
export const STATION_SPARKLINE_HEIGHT = 48

// Ages are shown in minutes, so a finer tick would only re-render for nothing.
export const STATION_TICK_MS = 30_000
