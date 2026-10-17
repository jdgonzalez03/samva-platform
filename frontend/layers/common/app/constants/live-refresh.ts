// How often views of the latest readings refetch while the tab is visible.
// Probes report about once a minute, so polling at half that keeps a new
// reading at most ~30 s behind without hammering the API.
export const LIVE_REFRESH_INTERVAL_MS = 30_000
