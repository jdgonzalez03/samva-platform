export class NotFoundError extends Error {
  statusCode = 404
  statusMessage: string

  constructor(statusMessage = 'Not Found') {
    super(statusMessage)
    this.name = 'NotFoundError'
    this.statusMessage = statusMessage
  }
}

export class RefreshTokenError extends Error {
  statusCode = 401
  statusMessage: string

  constructor(statusMessage = 'Refresh Token Error') {
    super(statusMessage)
    this.name = 'RefreshTokenError'
    this.statusMessage = statusMessage
  }
}

// Errors thrown by the fetcher are ofetch `FetchError`s, which carry the HTTP
// status on `status`; anything else (network, refresh) simply has no status.
export const isNotFound = (error: unknown): boolean =>
  (error as { status?: number } | null)?.status === 404

// A 404 is a final answer, not a transient failure: retrying only delays the
// message the user needs. Other errors keep the client's single retry.
export const retryUnlessNotFound = (
  failureCount: number,
  error: unknown,
): boolean => !isNotFound(error) && failureCount < 1

// For a polled query: once the record is gone, every further poll would only
// repeat the same 404, so the interval stops there.
export const pollUnlessNotFound =
  (intervalMs: number) =>
  (query: { state: { error: unknown } }): number | false =>
    isNotFound(query.state.error) ? false : intervalMs
