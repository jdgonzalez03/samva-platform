import {
  DEFAULT_VIEW_MODE,
  getStoredViewMode,
  parseViewMode,
  setStoredViewMode,
  type ViewMode,
} from '../utils/view-mode'

// The `?view=` query parameter decides which dashboard view is shown.
// `localStorage` is used only when the URL has no `view`, and only after mount:
// the server cannot read `localStorage`, so reading it during setup would make
// the client show a different tab than the server rendered (hydration error).
export const useDashboardViewMode = () => {
  const route = useRoute()
  const router = useRouter()

  const fallback = shallowRef<ViewMode>(DEFAULT_VIEW_MODE)

  onMounted(() => {
    if (parseViewMode(route.query.view)) return

    fallback.value = getStoredViewMode() ?? DEFAULT_VIEW_MODE
    // `replace`, not `push`: this writes the mode into the URL without adding a
    // new history entry. So the browser's Back button goes to the previous mode
    // instead of reading storage again, which by then already has the new mode.
    void router.replace({ query: { ...route.query, view: fallback.value } })
  })

  const mode = computed<ViewMode>(
    () => parseViewMode(route.query.view) ?? fallback.value,
  )

  const setMode = (next: string | number | undefined): void => {
    const parsed = parseViewMode(next)
    if (!parsed || parsed === mode.value) return

    setStoredViewMode(parsed)
    void router.push({ query: { ...route.query, view: parsed } })
  }

  return { mode, setMode }
}
