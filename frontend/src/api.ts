import { requestHistory, type LocalMessage } from './history'
export const BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
export const BACKEND_CONFIGURED = !!BASE || import.meta.env.DEV || import.meta.env.VITE_SAME_ORIGIN_API === 'true'
export type ProjectID = 'ring4'
export interface Trace { step: string; tool?: string; summary: string; document_ids: string[]; elapsed_ms: number }
export interface Citation { id: string; document_id: string; title: string; document_number?: string; url: string; locator: string; excerpt: string; checked_at: string; applicability: string; source_review_notes?: string; page?: number; source_url?: string }
export interface Result { status: string; content: string; citations: Citation[]; trace: Trace[]; trace_id: string; corpus_release?: string; model: string; embedding_model: string; mode: string; llm_calls: number; tool_calls: number; token_usage: number; elapsed_ms: number; as_of: string; support_level: string }
export interface Session { session_id: string; token: string }
export interface LegalDocument { id: string; title: string; url: string; document_number?: string; source_kind: string; project?: ProjectID; checked_at: string; applicability_verified: boolean; effective_from?: string; effective_to?: string; source_review_notes?: string; chunks?: { id: string; locator: string; text: string }[] }
export interface Project { id: ProjectID; name: string; description: string; source_ids: string[]; questions: string[] }
export interface Readiness { status: string; database?: boolean; llm_configured?: boolean; corpus_release?: string; checked_at?: string; publication_profile?: string; quality_status?: string; retrieval_mode?: string; coverage_gaps?: {document_id: string; title: string; reason: string}[] }

export async function getJSON<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(BASE + path, { signal })
  if (!res.ok) throw new Error('Dịch vụ chưa sẵn sàng. Backend có thể đang khởi động; hãy thử lại sau khoảng một phút.')
  return res.json()
}

export async function getSession(turnstileToken?:string): Promise<Session> {
  if (!BACKEND_CONFIGURED) throw new Error('Backend chưa được triển khai. Bản xem trước hiện chỉ có giao diện.')
  const cached = sessionStorage.getItem('landlaw-session')
  if (cached) {
    try {
      const session = JSON.parse(cached) as Session
      const response = await fetch(BASE + `/api/v1/sessions/${session.session_id}`, { headers: { Authorization: `Bearer ${session.token}` } })
      if (response.ok) return session
      if (response.status !== 404 && response.status !== 410) throw new Error('Chưa tải được phiên đã lưu. Vui lòng thử lại sau khi backend khởi động.')
    } catch (error) {
      if (!(error instanceof SyntaxError)) throw error
    }
    sessionStorage.removeItem('landlaw-session')
  }
  const response = await fetch(BASE + '/api/v1/sessions', { method: 'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({turnstile_token:turnstileToken}) })
  if (!response.ok) throw new Error('Chưa tạo được phiên. Backend có thể đang khởi động hoặc đã đạt giới hạn lượt dùng.')
  const session: Session = await response.json()
  sessionStorage.setItem('landlaw-session', JSON.stringify(session))
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
  if (!response.ok) {
    if (response.status === 429) throw new Error(`Đã đạt giới hạn lượt hỏi. Thử lại sau ${response.headers.get('Retry-After') || '60'} giây.`)
    if(response.status===409)throw new Error('Lượt hỏi đã được gửi hoặc phiên đang xử lý. Server không lưu đáp án để phát lại.')
    if(response.status===426)throw new Error('Hãy tải lại ứng dụng để dùng phiên bản mới.')
    throw new Error('Dịch vụ chưa sẵn sàng. Vui lòng thử lại sau.')
  }
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
