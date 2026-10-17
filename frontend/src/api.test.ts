import { describe, expect, it } from 'vitest'
import { SSEParser } from './api'
describe('SSE protocol', () => {
  it('handles fragmented unicode frames, comments and multiple events', () => {
    const events: unknown[] = []
    const parser = new SSEParser((type, data) => events.push([type, data]))
    parser.feed(': heartbeat\n\nevent: progress\ndata: {"summary":"Đang ')
    parser.feed('tra cứu"}\n\nevent: result\ndata: {"status":"answered"}\n\n')
    expect(events).toEqual([['progress', { summary: 'Đang tra cứu' }], ['result', { status: 'answered' }]])
  })
  it('handles CRLF frames without exposing heartbeats', () => {
    const events: unknown[] = []
    const parser = new SSEParser((type, data) => events.push([type, data]))
    parser.feed(': connected\r\n\r\nevent: failure\r\ndata: {"status":"error"}\r\n\r\n')
    expect(events).toEqual([['failure', { status: 'error' }]])
  })
})

describe('structured HTTP errors', () => {
  it('preserves provider retry hints without inventing a wait time', async () => {
    const { responseError } = await import('./api')
    const busy = await responseError(new Response(JSON.stringify({ detail: { code: 'system_busy' } }), { status: 429, headers: { 'Retry-After': '5' } }))
    expect(busy.code).toBe('system_busy')
    expect(busy.message).toContain('Hệ thống đang bận')
    expect(busy.retryAfter).toBe(5)
    const quota = await responseError(new Response('{}', { status: 429 }))
    expect(quota.retryAfter).toBeUndefined()
    expect(quota.message).not.toContain('giây')
  })
})
