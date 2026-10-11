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
