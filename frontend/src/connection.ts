/**
 * Connection status controller for the citizen chat.
 *
 * Keeps the last verified server capabilities separate from current network
 * reachability: a transient failed GET /api/v1/status must never erase the
 * verified configuration or disable a composer that the server previously
 * allowed. The backend remains authoritative for every chat submission.
 *
 * Framework-free and dependency-injected so it can be tested deterministically.
 */
import type { GenerationStatus } from './api'

export type ConnectionPhase = 'connecting' | 'healthy' | 'degraded' | 'unavailable' | 'disabled'

export interface ConnectionState {
  phase: ConnectionPhase
  /** Last successfully verified server status. Never cleared by a network failure. */
  status: GenerationStatus | null
  /** When that status was verified (epoch ms). */
  verifiedAt: number | null
  /** Latest transient error, cleared on a successful verification. */
  error: { code: string; message: string } | null
  /** Consecutive failed attempts; drives bounded backoff. */
  attempts: number
}

export interface ConnectionOptions {
  fetchStatus: (signal: AbortSignal) => Promise<GenerationStatus>
  setTimer?: (callback: () => void, delayMs: number) => number
  clearTimer?: (id: number) => void
  now?: () => number
  random?: () => number
  isVisible?: () => boolean
  minGapMs?: number
  baseDelayMs?: number
  maxDelayMs?: number
  maxRetryAfterMs?: number
  jitter?: number
  addListener?: (target: EventTarget, event: string, listener: () => void) => () => void
}

const INITIAL: ConnectionState = {
  phase: 'connecting',
  status: null,
  verifiedAt: null,
  error: null,
  attempts: 0,
}

export class ConnectionController {
  private state: ConnectionState = INITIAL
  private listeners = new Set<() => void>()
  private detach: Array<() => void> = []
  private inFlight: Promise<ConnectionState> | null = null
  private inFlightController: AbortController | null = null
  private retryTimer: number | null = null
  private lastStartedAt = 0
  private sequence = 0
  private started = false
  private readonly options: Required<Pick<ConnectionOptions, 'setTimer' | 'clearTimer' | 'now' | 'random' | 'isVisible' | 'minGapMs' | 'baseDelayMs' | 'maxDelayMs' | 'maxRetryAfterMs' | 'jitter'>> & ConnectionOptions

  constructor(options: ConnectionOptions) {
    this.options = {
      ...options,
      setTimer: options.setTimer ?? ((callback, delay) => window.setTimeout(callback, delay)),
      clearTimer: options.clearTimer ?? (id => window.clearTimeout(id)),
      now: options.now ?? (() => Date.now()),
      random: options.random ?? Math.random,
      isVisible: options.isVisible ?? (() => (typeof document === 'undefined' ? true : !document.hidden)),
      minGapMs: options.minGapMs ?? 2000,
      baseDelayMs: options.baseDelayMs ?? 2000,
      maxDelayMs: options.maxDelayMs ?? 30000,
      maxRetryAfterMs: options.maxRetryAfterMs ?? 300000,
      jitter: options.jitter ?? 0.2,
    }
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => { this.listeners.delete(listener) }
  }

  getSnapshot = () => this.state

  start() {
    if (this.started) return
    this.started = true
    const add = this.options.addListener ?? ((target: EventTarget, event: string, listener: () => void) => {
      target.addEventListener(event, listener)
      return () => target.removeEventListener(event, listener)
    })
    const refresh = () => { void this.check() }
    this.detach.push(add(document, 'visibilitychange', () => { if (this.options.isVisible()) refresh() }))
    this.detach.push(add(window, 'focus', refresh))
    this.detach.push(add(window, 'online', () => { this.resetBackoff(); refresh() }))
    void this.check({ force: true })
  }

  stop() {
    this.started = false
    for (const remove of this.detach.splice(0)) remove()
    this.inFlightController?.abort()
    this.inFlightController = null
    this.inFlight = null
    this.clearRetry()
  }

  /** Single-flight status read. Manual checks may bypass the min-gap, never dedupe. */
  check = ({ force = false }: { force?: boolean } = {}): Promise<ConnectionState> => {
    if (!this.started) return Promise.resolve(this.state)
    if (this.inFlight) return this.inFlight
    const now = this.options.now()
    if (!force && now - this.lastStartedAt < this.options.minGapMs) {
      return Promise.resolve(this.state)
    }
    this.lastStartedAt = now
    const sequence = ++this.sequence
    const controller = new AbortController()
    this.inFlightController = controller
    const request = this.options.fetchStatus(controller.signal)
      .then(status => this.settleSuccess(status, sequence))
      .catch(error => this.settleFailure(error, sequence))
      .finally(() => {
        if (this.sequence === sequence) {
          this.inFlight = null
          this.inFlightController = null
        }
      })
    this.inFlight = request
    return request
  }

  private settleSuccess(status: GenerationStatus, sequence: number): ConnectionState {
    if (sequence !== this.sequence) return this.state // stale response must not overwrite a newer verdict
    const enabled = !!status.generation_available
    this.clearRetry()
    this.state = {
      phase: enabled ? 'healthy' : 'disabled',
      status,
      verifiedAt: this.options.now(),
      error: null,
      attempts: 0,
    }
    this.emit()
    if (!enabled && status.retry_after) this.scheduleRetry(Math.min(
      this.options.maxRetryAfterMs, Math.max(1000, status.retry_after * 1000)))
    return this.state
  }

  private settleFailure(error: unknown, sequence: number): ConnectionState {
    if (sequence !== this.sequence) return this.state
    const attempts = this.state.attempts + 1
    this.state = {
      phase: this.state.status ? 'degraded' : 'unavailable',
      status: this.state.status,
      verifiedAt: this.state.verifiedAt,
      error: classify(error),
      attempts,
    }
    this.emit()
    const retryAfter = error instanceof Error && 'retryAfter' in error
      ? Number((error as { retryAfter?: number }).retryAfter) : NaN
    const base = this.options.baseDelayMs * 2 ** Math.max(0, attempts - 1)
    const capped = Number.isFinite(retryAfter) && retryAfter > 0
      ? Math.min(this.options.maxRetryAfterMs, retryAfter * 1000)
      : Math.min(this.options.maxDelayMs, base)
    this.scheduleRetry(capped * (1 + this.options.jitter * this.options.random()))
    return this.state
  }

  private scheduleRetry(delayMs: number) {
    this.clearRetry()
    if (!this.started || !this.options.isVisible()) return // focus/visibility will resume
    this.retryTimer = this.options.setTimer(() => {
      this.retryTimer = null
      void this.check({ force: true })
    }, Math.max(250, Math.round(delayMs)))
  }

  private clearRetry() {
    if (this.retryTimer !== null) {
      this.options.clearTimer(this.retryTimer)
      this.retryTimer = null
    }
  }

  private resetBackoff() {
    this.state = { ...this.state, attempts: 0 }
  }

  private emit() {
    for (const listener of this.listeners) listener()
  }
}

export function classify(error: unknown): { code: string; message: string } {
  if (error instanceof Error) {
    const code = (error as { code?: unknown }).code
    if (typeof code === 'string' && code) return { code, message: error.message }
    if (error.name === 'AbortError' || error.name === 'TimeoutError') {
      return { code: 'timeout', message: 'Máy chủ phản hồi quá chậm.' }
    }
    return { code: 'network', message: error.message }
  }
  return { code: 'network', message: 'Không kết nối được dịch vụ.' }
}

/** True when a verified status lets the composer submit a question. */
export function canSubmit(status: GenerationStatus | null) {
  return !!status && !!status.generation_available && !status.source_lookup_only
}
