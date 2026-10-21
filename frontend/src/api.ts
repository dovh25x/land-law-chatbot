import { requestHistory, type LocalMessage } from './history'
export const BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
export const BACKEND_CONFIGURED = !!BASE || import.meta.env.DEV || import.meta.env.VITE_SAME_ORIGIN_API === 'true'
export type ProjectID = 'ring4'
export interface Trace { step: string; tool?: string; summary: string; document_ids: string[]; elapsed_ms: number }
export interface Citation { checksum?: string; id: string; document_id: string; title: string; document_number?: string; url: string; locator: string; excerpt: string; checked_at: string; applicability: string; source_review_notes?: string; source_kind?: string; page?: number; source_url?: string }
export interface VerifiedClaim { text: string; citation_ids: string[]; kind?: string; section?: 'direct'|'explanation'|'actions' }
export interface AnswerSection { kind: 'direct'|'explanation'|'actions'; claim_indexes: number[] }
export interface Clarification { fact: string; question: string; options: string[]; allow_unknown: boolean }
export interface Result { status: string; content: string; citations: Citation[]; trace: Trace[]; trace_id: string; corpus_release?: string; model: string; embedding_model: string; mode: string; llm_calls: number; tool_calls: number; token_usage: number; elapsed_ms: number; as_of: string; support_level: string; retry_after?: number | null; missing_facts?: string[]; answer_schema_version?: number; verified_claims?: VerifiedClaim[]; answer_sections?: AnswerSection[]; answer_notices?:string[]; clarification?: Clarification|null; source_context?: {source_checked_at?:string|null;source_fresh?:boolean}; need_more_context?:string|null }
export interface Session { session_id: string; token: string }
export interface LegalDocument { checksum?: string; id: string; title: string; url: string; document_number?: string; source_kind: string; project?: ProjectID; checked_at: string; applicability_verified: boolean; effective_from?: string; effective_to?: string; source_review_notes?: string; availability?: 'reference_only'; attachment_urls?: string[]; source_files?: {url: string}[]; source_lookup_only?: boolean; review_as_of?: string; verified_passage_count?: number; whole_document_verified?: boolean; chunks?: { id: string; locator: string; text: string }[] }
export interface Project { id: ProjectID; name: string; description: string; source_ids: string[]; questions: string[] }
export interface Readiness { status: string; database?: boolean; llm_configured?: boolean; corpus_release?: string; checked_at?: string; publication_profile?: string; quality_status?: string; retrieval_mode?: string; coverage_gaps?: {document_id: string; title: string; reason: string}[] }

export interface GenerationStatus {
  source_lookup_only?: boolean
  source_lookup_as_of?: string
  api_version?: number
  capabilities?: {citizen_answers?: boolean; answer_schema_version?: number}
  generation_available: boolean
  reason: 'disabled' | 'source_stale' | 'provider_limited' | null
  retry_after?: number | null
  corpus_release?: string | null
  source_fresh?: boolean
  warning?: 'source_stale' | null
  source_checked_at?: string | null
}

export class APIError extends Error {
  constructor(message: string, public code: string, public retryAfter?: number) { super(message) }
}

let memorySession: Session | null = null
export function cachedSession(): Session | null {
  if (memorySession) return memorySession
  try {
    const value = JSON.parse(sessionStorage.getItem('landlaw-session') || 'null')
    if (typeof value?.session_id === 'string' && value.session_id && typeof value.token === 'string' && value.token) return memorySession = value
  } catch { /* A tab can work without browser session storage. */ }
  return null
}
export function clearSession() {
  memorySession = null
  try { sessionStorage.removeItem('landlaw-session') } catch { /* Memory is already cleared. */ }
}

export async function responseError(response: Response): Promise<APIError> {
  const body = await response.json().catch(() => null)
  const code = typeof body?.detail?.code === 'string' ? body.detail.code : `http_${response.status}`
  const raw = response.headers.get('Retry-After')
  const seconds = raw && /^\d+$/.test(raw) ? Number(raw) : undefined
  const wait = seconds === undefined ? '' : ` Thử lại sau ${seconds} giây.`
  const messages: Record<string, string> = {
    session_expired: 'Phiên đã hết hạn. Vui lòng xác minh trình duyệt và gửi lại câu hỏi.',
    generation_disabled: 'Trả lời bằng AI đang tạm dừng. Bạn vẫn có thể tra cứu thư viện nguồn.',
    system_busy: 'Hệ thống đang bận.',
    challenge_required: 'Vui lòng hoàn tất xác minh trình duyệt trước khi gửi.',
    challenge_failed: 'Xác minh trình duyệt chưa hợp lệ. Hãy tải lại trang để xác minh.',
    challenge_unavailable: 'Dịch vụ xác minh trình duyệt đang gián đoạn.',
    client_upgrade_required: 'Hãy tải lại ứng dụng để dùng phiên bản mới.',
  }
  const message = messages[code] || (response.status === 429 ? 'Đã đạt giới hạn lượt hỏi.'
    : response.status === 409 ? 'Lượt hỏi đã được gửi hoặc phiên đang xử lý. Server không lưu đáp án để phát lại.'
    : 'Dịch vụ chưa sẵn sàng. Vui lòng thử lại sau.')
  return new APIError(message + wait, code, seconds)
}

export async function getJSON<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(BASE + path, { signal })
  if (!res.ok) throw new Error('Dịch vụ chưa sẵn sàng. Backend có thể đang khởi động; hãy thử lại sau khoảng một phút.')
  return res.json()
}

export async function getSession(turnstileToken?:string): Promise<Session> {
  if (!BACKEND_CONFIGURED) throw new Error('Backend chưa được triển khai. Bản xem trước hiện chỉ có giao diện.')
  const cached = cachedSession()
  if (cached) {
      const response = await fetch(BASE + `/api/v1/sessions/${cached.session_id}`, { headers: { Authorization: `Bearer ${cached.token}` } })
      if (response.ok) return cached
      if (response.status !== 404 && response.status !== 410) throw new Error('Chưa tải được phiên đã lưu. Vui lòng thử lại sau khi backend khởi động.')
      clearSession()
  }
  const response = await fetch(BASE + '/api/v1/sessions', { method: 'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({turnstile_token:turnstileToken}) })
  if (!response.ok) throw await responseError(response)
  const session: Session = await response.json()
  if (!session.session_id || !session.token) throw new Error('Máy chủ chưa tạo được phiên hợp lệ. Vui lòng thử lại.')
  memorySession = session
  try { sessionStorage.setItem('landlaw-session', JSON.stringify(session)) } catch { /* Keep the session in this tab's memory. */ }
  return session
}

export class SSEParser {
  private buffer = ''
  constructor(private callback: (event: string, data: unknown) => void) {}
  feed(chunk: string) {
    this.buffer += chunk
    this.buffer = this.buffer.replace(/\r\n/g, '\n')
    let index: number
    while ((index = this.buffer.indexOf('\n\n')) !== -1) {
      const frame = this.buffer.slice(0, index)
      this.buffer = this.buffer.slice(index + 2)
      let event = 'message'
      const data: string[] = []
      for (const line of frame.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
      }
      if (data.length) this.callback(event, JSON.parse(data.join('\n')))
    }
  }
}

export async function ask(session: Session, message: string, project: string, asOf: string, signal: AbortSignal, onEvent: (event: string, data: unknown) => void, history:LocalMessage[]=[], requestId=crypto.randomUUID()) {
  const response = await fetch(BASE + '/api/v1/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.token}` }, signal,
    body: JSON.stringify({ session_id: session.session_id, message, project: project || null, as_of: asOf || null, request_id:requestId, history:requestHistory(history) }),
  })
  if (response.status === 404 || response.status === 410) {
    clearSession()
    throw new APIError('Phiên đã hết hạn. Vui lòng xác minh trình duyệt và gửi lại câu hỏi.', 'session_expired')
  }
  if (!response.ok) throw await responseError(response)
  if (!response.body) throw new Error('Trình duyệt không hỗ trợ luồng trả lời.')
  const parser = new SSEParser(onEvent)
  const reader = response.body.getReader(), decoder = new TextDecoder()
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      parser.feed(decoder.decode(value, { stream: true }))
    }
    parser.feed(decoder.decode())
  } finally { reader.releaseLock() }
}
