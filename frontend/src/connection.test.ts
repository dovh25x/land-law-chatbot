import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { APIError } from './api'
import { ConnectionController, canSubmit, classify, type ConnectionOptions, type ConnectionState } from './connection'
import type { GenerationStatus } from './api'

beforeEach(() => {
  vi.stubGlobal('document', { hidden: false, addEventListener() {}, removeEventListener() {} })
  vi.stubGlobal('window', { addEventListener() {}, removeEventListener() {}, setTimeout, clearTimeout })
})
afterEach(() => { vi.unstubAllGlobals() })

const OK: GenerationStatus = {
  generation_available: true, reason: null, api_version: 3, source_lookup_only: false,
  capabilities: { citizen_answers: true, answer_schema_version: 2 },
}

const LIMITED: GenerationStatus = {
  generation_available: false, reason: 'provider_limited', retry_after: 5, api_version: 3,
  source_lookup_only: false,
}

async function flush() { for (let i = 0; i < 5; i++) await Promise.resolve() }

function setup(overrides: Partial<ConnectionOptions> = {}) {
  let now = 1_000_000, nextId = 1
  const timers = new Map<number, { callback: () => void; delay: number }>()
  const deferred: Array<{ resolve: (value: GenerationStatus) => void; reject: (error: unknown) => void }> = []
  const listeners = new Map<string, () => void>()
  const fetchStatus = vi.fn((_signal: AbortSignal) => new Promise<GenerationStatus>((resolve, reject) => { deferred.push({ resolve, reject }) }))
  const controller = new ConnectionController({
    fetchStatus,
    setTimer: (callback, delay) => { const id = nextId++; timers.set(id, { callback, delay }); return id },
    clearTimer: id => { timers.delete(id) },
    now: () => now,
    random: () => 0,
    isVisible: () => true,
    minGapMs: 50,
    baseDelayMs: 2000,
    maxDelayMs: 30000,
    jitter: 0,
    addListener: (_target, event, listener) => { listeners.set(event, listener); return () => listeners.delete(event) },
    ...overrides,
  })
  const snapshot = () => controller.getSnapshot() as ConnectionState
  const runNextTimer = () => {
    const entry = [...timers.entries()].sort((a, b) => a[1].delay - b[1].delay)[0]
    if (!entry) return false
    timers.delete(entry[0]); entry[1].callback()
    return true
  }
  return { controller, fetchStatus, deferred, timers, listeners, snapshot, runNextTimer, advance: (ms: number) => { now += ms } }
}

describe('connection controller', () => {
  it('verifies the initial connection and keeps the capabilities', async () => {
    const h = setup()
    h.controller.start()
    expect(h.fetchStatus).toHaveBeenCalledTimes(1)
    expect(h.snapshot().phase).toBe('connecting')
    h.deferred[0].resolve(OK)
    await flush()
    const state = h.snapshot()
    expect(state.phase).toBe('healthy')
    expect(state.status).toBe(OK)
    expect(state.verifiedAt).not.toBeNull()
    expect(canSubmit(state.status)).toBe(true)
  })

  it('a single failed background status request degrades but never erases the verified capabilities', async () => {
    const h = setup()
    h.controller.start()
    h.deferred[0].resolve(OK)
    await flush()
    const pending = h.controller.check({ force: true })
    h.deferred[1].reject(new APIError('Dịch vụ chưa sẵn sàng.', 'http_503'))
    await pending
    const state = h.snapshot()
    expect(state.phase).toBe('degraded')
    expect(state.status).toBe(OK)
    expect(state.error?.code).toBe('http_503')
    expect(canSubmit(state.status)).toBe(true)
    expect([...h.timers.values()][0].delay).toBe(2000)
  })

  it('recovers automatically after consecutive failures using capped exponential backoff', async () => {
    const h = setup()
    h.controller.start()
    h.deferred[0].resolve(OK)
    await flush()
    const delays: number[] = []
    for (let attempt = 0; attempt < 6; attempt++) {
      const pending = h.controller.check({ force: true })
      h.deferred.at(-1)!.reject(new APIError('offline', 'offline'))
      await pending
      delays.push([...h.timers.values()][0].delay)
    }
    expect(delays).toEqual([2000, 4000, 8000, 16000, 30000, 30000])
    // The scheduled retry itself re-verifies and returns to healthy.
    h.runNextTimer()
    h.deferred.at(-1)!.resolve(OK)
    await flush()
    expect(h.snapshot().phase).toBe('healthy')
    expect(h.snapshot().attempts).toBe(0)
    expect(h.timers.size).toBe(0)
  })

  it('stays unavailable when it has never verified the service and recovers on retry', async () => {
    const h = setup()
    h.controller.start()
    h.deferred[0].reject(new APIError('Thiết bị đang ngoại tuyến.', 'offline'))
    await flush()
    expect(h.snapshot().phase).toBe('unavailable')
    expect(h.snapshot().status).toBeNull()
    h.runNextTimer()
    h.deferred[1].resolve(OK)
    await flush()
    expect(h.snapshot().phase).toBe('healthy')
  })

  it('deduplicates concurrent requests and ignores non-forced checks within the min gap', async () => {
    const h = setup()
    h.controller.start()
    h.deferred[0].resolve(OK)
    await flush()
    const first = h.controller.check({ force: true })
    const second = h.controller.check({ force: true })
    expect(h.fetchStatus).toHaveBeenCalledTimes(2)
    h.deferred[1].resolve(OK)
    await Promise.all([first, second])
    h.advance(10)
    h.advance(10)
    const quiet = h.controller.check()
    await quiet
    expect(h.fetchStatus).toHaveBeenCalledTimes(2)
  })

  it('re-checks on focus, visibility and reconnect events', async () => {
    const h = setup()
    h.controller.start()
    h.deferred[0].resolve(OK)
    await flush()
    h.advance(100)
    h.listeners.get('focus')!()
    expect(h.fetchStatus).toHaveBeenCalledTimes(2)
    h.deferred[1].resolve(OK)
    await flush()
    h.advance(100)
    h.listeners.get('visibilitychange')!()
    expect(h.fetchStatus).toHaveBeenCalledTimes(3)
    h.deferred[2].resolve(OK)
    await flush()
    h.advance(100)
    h.listeners.get('online')!()
    expect(h.fetchStatus).toHaveBeenCalledTimes(4)
  })

  it('stops timers and listeners without leaving requests behind', async () => {
    const h = setup()
    h.controller.start()
    h.deferred[0].resolve(OK)
    await flush()
    h.controller.check({ force: true })
    h.deferred[1].reject(new APIError('offline', 'offline'))
    await flush()
    expect(h.timers.size).toBe(1)
    h.controller.stop()
    expect(h.timers.size).toBe(0)
    h.advance(100)
    h.listeners.get('focus')?.()
    expect(h.fetchStatus).toHaveBeenCalledTimes(2)
  })

  it('respects an explicit generation-disabled server verdict and its retry window', async () => {
    const h = setup()
    h.controller.start()
    h.deferred[0].resolve(LIMITED)
    await flush()
    expect(h.snapshot().phase).toBe('disabled')
    expect(h.snapshot().status).toBe(LIMITED)
    expect(canSubmit(h.snapshot().status)).toBe(false)
    expect([...h.timers.values()][0].delay).toBe(5000)
  })

  it('uses the server rate-limit retry window instead of the backoff', async () => {
    const h = setup()
    h.controller.start()
    h.deferred[0].resolve(OK)
    await flush()
    const pending = h.controller.check({ force: true })
    h.deferred[1].reject(new APIError('Đã đạt giới hạn lượt hỏi.', 'http_429', 7))
    await pending
    expect(h.snapshot().phase).toBe('degraded')
    expect([...h.timers.values()][0].delay).toBe(7000)
  })

  it('keeps a cached verdict out of the health signal and exposes stable phases', async () => {
    const h = setup()
    h.controller.start()
    h.deferred[0].resolve(OK)
    await flush()
    const healthy = h.snapshot()
    const pending = h.controller.check({ force: true })
    h.deferred[1].reject(new APIError('timeout', 'timeout'))
    await pending
    const degraded = h.snapshot()
    expect(degraded.status).toBe(healthy.status)
    expect(degraded.verifiedAt).toBe(healthy.verifiedAt)
    expect(degraded.phase).not.toBe(healthy.phase)
  })
})

describe('error classification', () => {
  it('distinguishes transport failures, timeouts and API status codes', () => {
    expect(classify(new APIError('x', 'offline'))).toEqual({ code: 'offline', message: 'x' })
    expect(classify(new APIError('x', 'http_503'))).toEqual({ code: 'http_503', message: 'x' })
    expect(classify(Object.assign(new Error('slow'), { name: 'TimeoutError' })).code).toBe('timeout')
    expect(classify(new TypeError('Failed to fetch'))).toEqual({ code: 'network', message: 'Failed to fetch' })
  })
  it('never allows submission from a source-only or disabled capability', () => {
    expect(canSubmit(null)).toBe(false)
    expect(canSubmit({ ...OK, source_lookup_only: true })).toBe(false)
    expect(canSubmit({ ...OK, generation_available: false })).toBe(false)
  })
})
