const iconMap: Record<string, string> = {
  agriculture: "i-lucide-tractor",
  farming: "i-lucide-wheat",
  sensor: "i-lucide-radio",
  weather: "i-lucide-cloud-sun",
  dashboard: "i-lucide-layout-dashboard",
  analytics: "i-lucide-bar-chart-3",
  monitoring: "i-lucide-activity",
  components: "i-lucide-cpu",
  system: "i-lucide-server",
  play: "i-lucide-play-circle",
  document: "i-lucide-file-text",
  download: "i-lucide-download",
  search: "i-lucide-search",
  efficiency: "i-lucide-zap",
  optimization: "i-lucide-trending-up",
  automation: "i-lucide-bot",
  innovation: "i-lucide-lightbulb",
  security: "i-lucide-shield",
  team: "i-lucide-users",
  company: "i-lucide-building",
  support: "i-lucide-headset",
  trust: "i-lucide-handshake",
  mission: "i-lucide-flag",
  vision: "i-lucide-eye",
  goal: "i-lucide-target",
  impact: "i-lucide-sparkles",
  sustainability: "i-lucide-leaf",
  check: "i-lucide-check",
}

export function getBlockIcon(icon: string): string {
  return iconMap[icon] || "i-lucide-check-circle"
}
