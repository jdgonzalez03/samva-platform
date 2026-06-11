const backgroundMap: Record<string, string> = {
  white: "bg-white",
  gray: "bg-gray-100",
  green: "bg-green-100",
}

export function getBlockBackground(background: string): string {
  return backgroundMap[background] || "bg-white"
}
