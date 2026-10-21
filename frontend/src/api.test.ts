import { afterEach, describe, expect, it, vi } from 'vitest'
import { SSEParser } from './api'
import { ask, cachedSession, clearSession, getSession } from './api'

afterEach(() => { clearSession(); vi.unstubAllGlobals() })
it('keeps a usable session in memory when sessionStorage is blocked', async () => {
  vi.stubGlobal('sessionStorage', { getItem() { throw Error('blocked') }, setItem() { throw Error('blocked') }, removeItem() { throw Error('blocked') } })
  const session = { session_id: 'fixture', token: 'test-token' }
  const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(session), { status: 201 })).mockResolvedValueOnce(new Response('{}'))
  vi.stubGlobal('fetch', fetcher)
  expect(await getSession()).toEqual(session)
  expect(cachedSession()).toEqual(session)
  expect(await getSession()).toEqual(session)
  expect(fetcher.mock.calls.filter(([url]) => url.endsWith('/sessions'))).toHaveLength(1)
})
it('expires a rejected chat session without resending the question', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 404 }))
  vi.stubGlobal('fetch', fetcher)
  await expect(ask({session_id:'fixture',token:'test-token'},'fixture','ring4','',new AbortController().signal,()=>{})).rejects.toMatchObject({code:'session_expired'})
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(cachedSession()).toBeNull()
})
it('sends the simple RAG execution mode for chat turns', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response('event: result\ndata: {"status":"answered"}\n\n', {
    status: 200, headers: { 'Content-Type': 'text/event-stream' },
  }))
  vi.stubGlobal('fetch', fetcher)
  await ask({session_id:'fixture',token:'test-token'},'Điều kiện bồi thường?','ring4','',new AbortController().signal,()=>{})
  const body = JSON.parse(fetcher.mock.calls[0][1].body)
  expect(body.mode).toBe('simple_rag')
})
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
