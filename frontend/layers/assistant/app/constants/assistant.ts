// Tools that change data: after one runs, every cached view may be stale
// (the plot's latest irrigation shows on the dashboard, plots and predictions).
export const WRITE_TOOLS = new Set(['calculate_irrigation'])

// Labels for the tool rows; an unknown tool falls back to a generic label.
export const TOOL_ICONS: Record<string, string> = {
  list_farms: 'i-lucide-tractor',
  list_plots: 'i-lucide-land-plot',
  get_plot_conditions: 'i-lucide-thermometer',
  list_sensors: 'i-lucide-radio-tower',
  get_latest_irrigation: 'i-lucide-droplets',
  calculate_irrigation: 'i-lucide-calculator',
}

export const DEFAULT_TOOL_ICON = 'i-lucide-wrench'

// One quick action per tool. Those that need a plot only fill the prompt, so
// the user completes the plot name before sending.
export const QUICK_ACTIONS = [
  { key: 'farms', tool: 'list_farms', needsPlot: false },
  { key: 'plots', tool: 'list_plots', needsPlot: false },
  { key: 'sensors', tool: 'list_sensors', needsPlot: false },
  { key: 'conditions', tool: 'get_plot_conditions', needsPlot: true },
  { key: 'latestIrrigation', tool: 'get_latest_irrigation', needsPlot: true },
  { key: 'calculateIrrigation', tool: 'calculate_irrigation', needsPlot: true },
] as const

export const TIPS_DISMISSED_KEY = 'samva:assistant-tips-dismissed'
