// Why not just link to the file with `<a href="/api/.../export">`? Because the
// browser would open that URL as a normal navigation, and navigations never
// carry our JWT (it lives in localStorage and only our fetcher adds the
// `Authorization` header). So the caller downloads the file through the
// fetcher first, and this helper turns the in-memory Blob into a temporary
// object URL that a hidden `<a download>` can click.
export const downloadBlob = (blob: Blob, filename: string): void => {
  if (!import.meta.client) return

  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.rel = 'noopener'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  // Revoking synchronously cancels the download in Safari; one tick is enough.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
