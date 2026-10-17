// A clock value that updates every `intervalMs`. Without it, a text like
// "3 minutes ago" would stay the same forever while the page is open.
// Use this one value to compute both the age text and any time limit
// (e.g. "older than 15 minutes"), so the two can never disagree.
// `shallowRef` is enough: the value is a number and is always replaced whole.
export const useNow = (intervalMs: number) => {
  const now = shallowRef(Date.now())

  if (import.meta.client) {
    const timer = setInterval(() => {
      now.value = Date.now()
    }, intervalMs)
    onScopeDispose(() => {
      clearInterval(timer)
    })
  }

  return now
}
