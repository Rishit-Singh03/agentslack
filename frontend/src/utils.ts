export function utcDate(value: string): Date {
  return new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`)
}
export function clockTime(value: string, seconds = false): string {
  return utcDate(value).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    ...(seconds ? { second: '2-digit' } : {}),
  })
}
export function upsert<T extends { id: number }>(items: T[], item: T): T[] {
  return items.some((existing) => existing.id === item.id)
    ? items.map((existing) => (existing.id === item.id ? item : existing))
    : [...items, item]
}
export function mergeMessages<T extends { id: number }>(first: T[], second: T[]): T[] {
  return [...new Map([...first, ...second].map((item) => [item.id, item])).values()].sort(
    (a, b) => a.id - b.id,
  )
}
