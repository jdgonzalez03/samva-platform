// Up to two initials from name parts, so an avatar without a photo still
// identifies its owner instead of rendering an empty circle.
export function getInitials(...parts: (string | null | undefined)[]): string {
  const initials = parts
    .map((part) => part?.trim().charAt(0) ?? '')
    .join('')
    .slice(0, 2)
  return initials.toUpperCase() || '?'
}
