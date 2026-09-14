export function formatHistoryTime(
  iso: string,
  options: { now?: Date, timeZone?: string } = {},
): string {
  if (!iso) {
    return ''
  }
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const now = options.now ?? new Date()
  const timeZone = options.timeZone
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  const get = (type: Intl.DateTimeFormatPartTypes) => parts.find(part => part.type === type)?.value ?? ''
  const year = get('year')
  const nowYear = new Intl.DateTimeFormat('en-US', { timeZone, year: 'numeric' }).format(now)
  const time = `${get('hour')}:${get('minute')}`
  if (year === nowYear) {
    return `${get('month')} ${get('day')}, ${time}`
  }
  return `${get('month')} ${get('day')}, ${year}, ${time}`
}
