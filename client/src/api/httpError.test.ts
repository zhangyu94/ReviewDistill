import { describe, expect, it } from 'vitest'
import { SERVER_UNREACHABLE, userFacingFetchError, userFacingHttpError } from './httpError.ts'

describe('userFacingHttpError', () => {
  it('says the server cannot be reached instead of Bad Gateway', () => {
    expect(userFacingHttpError(502, 'Bad Gateway')).toBe(SERVER_UNREACHABLE)
  })

  it('says the same for other proxy-down statuses', () => {
    expect(userFacingHttpError(503, 'Service Unavailable')).toBe(SERVER_UNREACHABLE)
    expect(userFacingHttpError(504, 'Gateway Timeout')).toBe(SERVER_UNREACHABLE)
  })

  it('keeps a server-provided explanation for other failures', () => {
    expect(userFacingHttpError(500, 'Internal Server Error', 'store corrupt')).toBe(
      'store corrupt',
    )
    expect(userFacingHttpError(404, 'Not Found', 'Unknown label')).toBe('Unknown label')
  })
})

describe('userFacingFetchError', () => {
  it('says the server cannot be reached when the browser cannot connect', () => {
    expect(userFacingFetchError(new TypeError('Failed to fetch'))).toBe(SERVER_UNREACHABLE)
  })

  it('keeps other error messages', () => {
    expect(userFacingFetchError(new Error('store corrupt'))).toBe('store corrupt')
  })
})
