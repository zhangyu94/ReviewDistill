export const SERVER_UNREACHABLE
  = 'Cannot reach the ReviewDistill server. Make sure it is running, then reload this page.'

const GATEWAY_STATUSES = new Set([502, 503, 504])

export function isServerUnreachableMessage(text: string): boolean {
  return text === SERVER_UNREACHABLE
}

export function userFacingHttpError(
  status: number,
  statusText: string,
  detail?: string,
): string {
  if (GATEWAY_STATUSES.has(status) || isGatewayStatusText(statusText)) {
    return SERVER_UNREACHABLE
  }
  const fromBody = detail?.trim()
  if (fromBody) {
    return fromBody
  }
  const fromStatus = statusText.trim()
  if (fromStatus) {
    return fromStatus
  }
  return `Request failed (${status})`
}

export function userFacingFetchError(err: unknown): string {
  if (isBrowserDisconnect(err)) {
    return SERVER_UNREACHABLE
  }
  return err instanceof Error ? err.message : String(err)
}

function isGatewayStatusText(statusText: string): boolean {
  return /^(?:bad gateway|service unavailable|gateway timeout)$/i.test(statusText.trim())
}

function isBrowserDisconnect(err: unknown): boolean {
  if (!(err instanceof Error)) {
    return false
  }
  return err instanceof TypeError
    || /failed to fetch|networkerror|load failed/i.test(err.message)
}
