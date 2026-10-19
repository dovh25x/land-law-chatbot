import { listConversations, saveConversation, deleteConversation, clearConversations, type Conversation, newConversation as makeConversation } from './history'
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { ArrowDown, ArrowUp, BookOpen, CircleHelp, Copy, GitBranch, LoaderCircle, Menu, MessageSquare, Moon, PanelLeftClose, PanelLeftOpen, Plus, Search, ShieldCheck, Square, Sun, Trash2, X } from 'lucide-react'
import { ask, APIError, BASE, BACKEND_CONFIGURED, cachedSession, clearSession, getJSON, getSession, type Citation, type GenerationStatus, type LegalDocument, type Readiness, type Result, type Session, type Trace } from './api'
import { ConfirmDialog, DataPanel, DocumentRow, formatDate, generationLabel, SourcePanel, sourceKinds, TracePanel, useDialog, useMedia } from './ui'
import { Turnstile } from './Turnstile'

type Page = 'chat' | 'sources' | 'evaluation'
type Message = { id: string; role: 'user' | 'assistant'; content: string; result?: Result }
type SourceSelection = { source: Citation | LegalDocument | null; citations: Citation[] }
const suggestions = ['Chi phí di chuyển tài sản được quy định thế nào?', 'Khi nào được hỗ trợ ổn định đời sống?', 'Cần hồ sơ gì để đối chiếu điều kiện tái định cư?']
const searchText = (value: string) => value.toLocaleLowerCase('vi').normalize('NFD').replace(/\p{Diacritic}/gu, '').replace(/đ/g, 'd')
const pageLabels: Record<Page, string> = { chat: 'Hỏi đáp pháp luật', sources: 'Thư viện văn bản', evaluation: 'Đánh giá hệ thống' }
const pageIcons = { chat: MessageSquare, sources: BookOpen, evaluation: ShieldCheck }
const labels: Record<string, string> = { answered: 'Có căn cứ', clarification_needed: 'Cần bổ sung thông tin', insufficient_evidence: 'Chưa đủ căn cứ', limited: 'Giới hạn lượt dùng', error: 'Chưa xử lý được' }
function initialTheme() {
  try { const saved = localStorage.getItem('landlaw-theme'); if (saved === 'light' || saved === 'dark') return saved } catch { /* Theme works in memory when storage is unavailable. */ }
  return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function App() {
  const [page, setPage] = useState<Page>('chat'), [navOpen, setNavOpen] = useState(false), [collapsed, setCollapsed] = useState(false)
  const [copiedId, setCopiedId] = useState<string>(), [copyError, setCopyError] = useState('')
  const conversationRef = useRef(makeConversation())
  const [conversations, setConversations] = useState<Conversation[]>([]), [storageError, setStorageError] = useState('')
  const [deletion, setDeletion] = useState<{ id?: string; title: string } | null>(null), [deleting, setDeleting] = useState(false)
  const [theme, setTheme] = useState(initialTheme), [challenge, setChallenge] = useState<string>()
  const [hasSession, setHasSession] = useState(() => !!cachedSession()), [challengeVersion, setChallengeVersion] = useState(0)
  const [dataOpen, setDataOpen] = useState(false), [input, setInput] = useState(''), [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [readiness, setReadiness] = useState<Readiness | null>(null), [generation, setGeneration] = useState<GenerationStatus | null>(null), [connecting, setConnecting] = useState(false)
  const [docs, setDocs] = useState<LegalDocument[]>([]), [docsState, setDocsState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [evaluationState, setEvaluationState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [trace, setTrace] = useState<Trace[]>([]), [traceOpen, setTraceOpen] = useState(false)
  const [sourcePanel, setSourcePanel] = useState<SourceSelection | null>(null)
  const [evaluation, setEvaluation] = useState<Record<string, unknown> | null>(null), [search, setSearch] = useState(''), [sourceKind, setSourceKind] = useState('all')
  const inputRef = useRef<HTMLTextAreaElement>(null), navRef = useRef<HTMLElement>(null)
  const sessionRef = useRef<Session | null>(null), abortRef = useRef<AbortController | null>(null), stopReason = useRef('')
  const chatScroll = useRef<HTMLDivElement>(null), nearBottom = useRef(true), [showBottom, setShowBottom] = useState(false)
  const mobile = useMedia('(max-width: 767px)'), desktop = useMedia('(min-width: 1280px)'), touch = useMedia('(pointer: coarse)')
  const modalOpen = !!deletion || dataOpen || traceOpen || (!!sourcePanel && !desktop)
  useDialog(navRef, navOpen && !deletion, true, () => setNavOpen(false))
  useEffect(() => { if (!mobile) setNavOpen(false) }, [mobile])
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('landlaw-theme', theme) } catch { /* Keep the selected theme for this tab. */ }
  }, [theme])
  useEffect(() => {
    const textarea = inputRef.current
    if (textarea) { textarea.style.height = 'auto'; textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px` }
  }, [input, page])

  async function copyAnswer(id: string, content: string) {
    try { await navigator.clipboard.writeText(content); setCopiedId(id); setCopyError('') }
    catch { setCopyError('Không sao chép được. Bạn có thể chọn nội dung để sao chép thủ công.') }
  }
  async function refresh(signal?: AbortSignal) {
    if (!BACKEND_CONFIGURED) { setReadiness({ status: 'not_deployed' }); setDocsState('error'); setEvaluationState('error'); return }
    setConnecting(true); setDocsState('loading'); setEvaluationState('loading')
    const results = await Promise.allSettled([
      fetch(BASE + '/readyz', { signal }).then(response => response.json() as Promise<Readiness>),
      getJSON<GenerationStatus>('/api/v1/status', signal),
      getJSON<{ documents: LegalDocument[]; references?: LegalDocument[] }>('/api/v1/documents', signal),
      getJSON<Record<string, unknown>>('/api/v1/evaluations/latest', signal),
    ])
    if (signal?.aborted) return
    const [ready, status, sources, report] = results
    setReadiness(ready.status === 'fulfilled' ? ready.value : { status: 'starting' })
    setGeneration(status.status === 'fulfilled' ? status.value : null)
    if (sources.status === 'fulfilled') { setDocs([...sources.value.documents, ...(sources.value.references || [])]); setDocsState('ready') } else setDocsState('error')
    if (report.status === 'fulfilled') { setEvaluation(report.value); setEvaluationState('ready') } else setEvaluationState('error')
    setConnecting(false)
  }
  useEffect(() => { const controller = new AbortController(); void refresh(controller.signal); return () => controller.abort() }, [])
  useEffect(() => {
    if (!BACKEND_CONFIGURED) return
    const controller = new AbortController()
    const update = () => { if (!document.hidden) void getJSON<GenerationStatus>('/api/v1/status', controller.signal).then(setGeneration).catch(() => {}) }
    const timer = generation?.reason === 'provider_limited'
      ? window.setTimeout(update, Math.min(300000, Math.max(1000, (generation.retry_after || 30) * 1000))) : undefined
    document.addEventListener('visibilitychange', update)
    window.addEventListener('focus', update)
    return () => { controller.abort(); window.clearTimeout(timer); document.removeEventListener('visibilitychange', update); window.removeEventListener('focus', update) }
  }, [generation])
  useEffect(() => {
    let alive = true
    void listConversations().then(saved => {
      if (!alive) return
      setConversations(saved)
      if (saved.length) { conversationRef.current = saved[0]; setMessages(saved[0].messages) }
    }).catch(() => { if (alive) setStorageError('Không đọc được lịch sử tại máy; hội thoại chỉ tồn tại trong tab này.') })
    const timer = window.setInterval(() => {
      void listConversations().then(saved => {
        if (!alive) return
        setConversations(saved)
        if (conversationRef.current.expires_at <= Date.now()) { conversationRef.current = makeConversation(); setMessages([]); setTrace([]) }
      }).catch(() => { if (alive) setStorageError('Không dọn được lịch sử hết hạn tại máy.') })
    }, 60000)
    return () => { alive = false; clearInterval(timer) }
  }, [])
  useEffect(() => {
    if (!messages.length) return
    const current = conversationRef.current
    void saveConversation({ ...current, messages, title: messages[0].content.slice(0, 80), updated_at: Date.now() })
      .then(() => listConversations()).then(setConversations)
      .catch(() => setStorageError('Không lưu được lịch sử tại máy. Server không giữ bản sao; bạn có thể tiếp tục trong tab.'))
  }, [messages])
  useEffect(() => {
    if (nearBottom.current) chatScroll.current?.scrollTo({ top: chatScroll.current.scrollHeight, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
    else setShowBottom(true)
  }, [messages, busy])
  useEffect(() => () => abortRef.current?.abort(), [])

  async function send() {
    if (busy || !input.trim()) return
    if (!BACKEND_CONFIGURED) { setError('Backend chưa được triển khai. Bản xem trước hiện chỉ có giao diện.'); return }
    if (generation && !generation.generation_available) { setError(`${generationLabel(generation)}. Bạn vẫn có thể tra cứu thư viện nguồn.`); return }
    if (import.meta.env.VITE_TURNSTILE_SITE_KEY && !hasSession && !challenge) { setError('Vui lòng hoàn tất xác minh trình duyệt trước khi gửi.'); return }
    const question = input.trim()
    setPage('chat'); setNavOpen(false); setInput(''); setError(''); setBusy(true); setTrace([]); stopReason.current = ''; nearBottom.current = true
    const messageId = crypto.randomUUID()
    setMessages(current => [...current, { id: messageId, role: 'user', content: question }])
    const controller = new AbortController(); abortRef.current = controller
    const timeout = window.setTimeout(() => { stopReason.current = 'Quá thời gian chờ kết nối. Server không lưu đáp án để khôi phục.'; controller.abort() }, 180000)
    let received = false
    try {
      sessionRef.current ||= await getSession(challenge)
      setHasSession(true)
      if (controller.signal.aborted) throw new DOMException('Aborted', 'AbortError')
      await ask(sessionRef.current, question, 'ring4', '', controller.signal, (event, data) => {
        if (event === 'progress') setTrace(current => [...current, data as Trace])
        if (event === 'result') {
          received = true
          const result = data as Result
          setMessages(current => [...current, { id: result.trace_id, role: 'assistant', content: result.content, result }]); setTrace(result.trace)
        }
        if (event === 'failure') { received = true; setError((data as { content: string }).content) }
      }, messages)
      if (!received) throw new Error('Mất kết nối trước khi nhận kết quả. Server không lưu đáp án để khôi phục. Bạn có thể chủ động gửi câu hỏi mới.')
    } catch (failure) {
      if (failure instanceof APIError && ['session_expired', 'challenge_failed', 'challenge_required'].includes(failure.code)) {
        sessionRef.current = null; clearSession(); setHasSession(false); setChallenge(undefined); setChallengeVersion(value => value + 1)
        setInput(current => current || question)
        setMessages(current => current.filter(message => message.id !== messageId))
      }
      setError(failure instanceof Error && failure.name !== 'AbortError' ? failure.message : stopReason.current || 'Lượt hỏi đã dừng. Server không lưu đáp án để khôi phục.')
    } finally { window.clearTimeout(timeout); setBusy(false); abortRef.current = null }
  }
  function newConversation() {
    if (busy) return
    conversationRef.current = makeConversation(); setMessages([]); setTrace([]); setError(''); setInput(''); setPage('chat'); setNavOpen(false); setSourcePanel(null); nearBottom.current = true
  }
  async function confirmDeletion() {
    if (!deletion || busy) return
    setDeleting(true)
    try {
      if (deletion.id) await deleteConversation(deletion.id); else await clearConversations()
      setConversations(await listConversations())
      if (!deletion.id || conversationRef.current.id === deletion.id) newConversation()
      setDeletion(null)
    } catch { setStorageError('Không xóa được lịch sử tại máy.') }
    finally { setDeleting(false) }
  }
  function openSource(source: Citation | LegalDocument | null, citations: Citation[] = []) {
    const scroll = chatScroll.current
    if (scroll) scroll.scrollTo({ top: scroll.scrollTop, behavior: 'instant' })
    setDataOpen(false); setTraceOpen(false)
    const enriched = source ? { ...source, checksum: source.checksum || docs.find(doc => doc.id === ('document_id' in source ? source.document_id : source.id))?.checksum } : null
    setSourcePanel({ source: enriched, citations })
  }
  function navigate(target: Page) { setDataOpen(false); setPage(target); setNavOpen(false); setTraceOpen(false); setSourcePanel(null) }
  const filteredDocs = docs.filter(doc => (sourceKind === 'all' || doc.source_kind === sourceKind) && searchText(`${doc.title} ${doc.document_number || ''}`).includes(searchText(search)))
  const evaluationWarning = evaluation && evaluation.status !== 'not_run' && (!evaluation.matches_active_release || !evaluation.matches_active_configuration || evaluation.status !== 'reviewed')
    ? 'Chưa hoàn tất đánh giá trên cấu hình đang hoạt động. Không diễn giải kết quả của phiên bản khác thành chất lượng bản hiện tại.' : ''
  const ready = readiness?.status === 'ready'
  const connectionMessage = connecting ? 'Đang kết nối dịch vụ. Lần khởi động đầu có thể mất khoảng một phút…'
    : generation && !generation.generation_available ? `${generationLabel(generation)}.${generation.retry_after ? ` Thử lại sau ${generation.retry_after} giây.` : ''} Thư viện nguồn vẫn truy cập được.`
    : generation?.warning === 'source_stale' ? 'Nguồn chưa được rà soát cập nhật. AI trả lời theo snapshot; chưa xác nhận quy định hiện hành. Vui lòng đối chiếu nguồn chính thức.'
    : !ready ? readiness?.status === 'not_deployed' ? 'Bản xem trước giao diện. Backend chưa được triển khai.' : 'Dịch vụ chưa sẵn sàng. Bạn có thể kiểm tra lại kết nối.' : ''

  return <div onClickCapture={event => { const button = (event.target as HTMLElement).closest('button'); button?.focus() }} className={`app-shell page-${page} ${sourcePanel ? 'panel-open' : ''} ${navOpen ? 'nav-open' : ''} ${collapsed ? 'sidebar-collapsed' : ''}`}>
    <a className="skip-link" href="#main-content">Đến nội dung chính</a>
    {navOpen && <button className="nav-scrim" tabIndex={-1} onClick={() => setNavOpen(false)} aria-label="Đóng menu điều hướng"/>}
    <aside ref={navRef} className="sidebar" id="main-navigation" role={navOpen ? 'dialog' : undefined} aria-modal={navOpen || undefined} aria-label={navOpen ? 'Menu điều hướng' : 'Thanh điều hướng'} inert={modalOpen || (mobile && !navOpen)}>
      <div className="sidebar-heading"><a className="brand" href="#" onClick={event => { event.preventDefault(); navigate('chat') }}>Vành đai 4</a><button className="icon-button desktop-collapse" onClick={() => setCollapsed(true)} aria-label="Thu gọn thanh điều hướng"><PanelLeftClose size={20}/></button><button className="icon-button mobile-nav-close" onClick={() => setNavOpen(false)} aria-label="Đóng menu"><X size={20}/></button></div>
      <button className="button button-primary new-chat" onClick={newConversation} disabled={busy}><Plus size={18}/>Cuộc trò chuyện mới</button>
      <nav aria-label="Điều hướng chính">{(Object.entries(pageLabels) as [Page, string][]).map(([id, label]) => { const Icon = pageIcons[id]; return <button key={id} aria-current={page === id ? 'page' : undefined} className={page === id ? 'active' : ''} onClick={() => navigate(id)}><Icon size={18}/>{label}</button> })}</nav>
      <div className="nav-label">Lịch sử trên thiết bị</div>
      <div className="history-list">{conversations.map(conversation => <div className={`history-row ${conversationRef.current.id === conversation.id ? 'active' : ''}`} key={conversation.id}>
        <button disabled={busy} title={conversation.title} onClick={() => { conversationRef.current = conversation; setMessages(conversation.messages); setPage('chat'); setNavOpen(false); setSourcePanel(null); setError(''); nearBottom.current = true }}>{conversation.title}</button>
        <button disabled={busy} aria-label={`Xóa cuộc trò chuyện ${conversation.title}`} onClick={() => setDeletion({ id: conversation.id, title: 'Xóa cuộc trò chuyện?' })}><Trash2 size={16}/></button>
      </div>)}{!conversations.length && <p className="secondary-copy">Chưa có cuộc trò chuyện.</p>}</div>
      <div className="sidebar-note"><button className="mobile-data-link" onClick={() => { setNavOpen(false); setSourcePanel(null); setTraceOpen(false); setDataOpen(true) }} aria-label="Thông tin dữ liệu và kết nối"><CircleHelp size={18}/>Dữ liệu và kết nối</button><button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label="Đổi giao diện sáng tối">{theme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>}Giao diện {theme === 'dark' ? 'sáng' : 'tối'}</button><button disabled={busy} onClick={() => setDeletion({ title: 'Xóa toàn bộ lịch sử?' })}><Trash2 size={18}/>Xóa toàn bộ lịch sử</button><p>Lưu tại máy trong 7 ngày.<br/>Không đồng bộ giữa thiết bị.</p></div>
    </aside>
    <main className="main" id="main-content" inert={navOpen || modalOpen}>
      <header className="topbar"><div className="topbar-title"><button className="icon-button mobile-menu" onClick={() => setNavOpen(true)} aria-label="Mở menu điều hướng" aria-expanded={navOpen} aria-controls="main-navigation"><Menu size={20}/></button>{collapsed && <button className="icon-button desktop-expand" onClick={() => setCollapsed(false)} aria-label="Mở rộng thanh điều hướng"><PanelLeftOpen size={20}/></button>}<div><span>{page === 'chat' ? 'Vành đai 4' : pageLabels[page]}</span>{page === 'chat' && <span className="topbar-subtitle">Trợ lý pháp luật</span>}</div></div><div className="topbar-actions"><span className="preview-label">Bản thử nghiệm</span><button className="icon-button data-trigger" onClick={() => { setSourcePanel(null); setTraceOpen(false); setDataOpen(true) }} aria-label="Thông tin dữ liệu và kết nối" title="Thông tin dữ liệu và kết nối"><CircleHelp size={20}/></button><button className="icon-button mobile-new-chat" onClick={newConversation} disabled={busy} aria-label="Cuộc trò chuyện mới"><Plus size={20}/></button></div></header>
      {storageError && <div className="global-notice" role="alert"><span>{storageError}</span><button className="icon-button" onClick={() => setStorageError('')} aria-label="Đóng thông báo lịch sử"><X size={18}/></button></div>}
      {copyError && <div className="global-notice" role="status"><span>{copyError}</span><button className="icon-button" onClick={() => setCopyError('')} aria-label="Đóng thông báo sao chép"><X size={18}/></button></div>}
      {page === 'chat' && <div className={`chat-workspace ${messages.length ? 'has-messages' : 'is-empty'}`}>
        <div ref={chatScroll} className="chat-scroll" onScroll={event => { const el = event.currentTarget; nearBottom.current = el.scrollHeight - el.clientHeight - el.scrollTop < 96; setShowBottom(!nearBottom.current) }}>
          {!messages.length ? <div className="welcome"><div className="welcome-mark"><MessageSquare size={28}/></div><h1>Bạn muốn tìm hiểu điều gì?</h1><p className="intro">Bồi thường, hỗ trợ và tái định cư<br className="mobile-break"/> cho Vành đai 4 tại Hà Nội.</p></div> : <div className="messages">{messages.map(message => <article key={message.id} className={`message ${message.role}`}>
            <div className="message-label">{message.role === 'user' ? 'Bạn' : 'Vành đai 4'}</div>
            {message.result && message.result.status !== 'answered' && <span className={`answer-status ${message.result.status}`}>{labels[message.result.status] || 'Trạng thái chưa xác định'}</span>}
            <div className="message-body"><ReactMarkdown components={{ a: ({ children }) => <span>{children}</span> }}>{message.content}</ReactMarkdown></div>
            {!!message.result?.retry_after && <p className="secondary-copy">Thử lại sau {message.result.retry_after} giây.</p>}
            {!!message.result?.citations?.length && <div className="citations" aria-label="Căn cứ của đáp án">{message.result.citations.map((citation, index) => <button key={citation.id} onClick={() => openSource(citation, message.result!.citations)} aria-label={`[${index + 1}] ${citation.title} ${citation.document_number || ''} · ${citation.locator}`}><span className="citation-index">{index + 1}</span><span><strong>{citation.document_number || citation.title}</strong><small>{citation.document_number ? `${citation.title} · ` : ''}{citation.locator}</small></span></button>)}</div>}
            {message.result && <div className="answer-actions">{!!message.result.citations?.length && <button onClick={() => openSource(null, message.result!.citations)}><BookOpen size={16}/>Xem nguồn</button>}<button className="trace-link" aria-label="Xem quá trình kiểm chứng" onClick={() => { setSourcePanel(null); setDataOpen(false); setTrace(message.result!.trace || []); setTraceOpen(true) }}><GitBranch size={16}/>Chi tiết thực thi</button><button onClick={() => void copyAnswer(message.id, message.content)}><Copy size={16}/>{copiedId === message.id ? 'Đã sao chép' : 'Sao chép'}</button></div>}
          </article>)}{busy && <div className="working" role="status"><LoaderCircle className="spin" size={18}/><span>{trace.at(-1)?.summary || 'Đang kết nối và chuẩn bị tra cứu…'}</span><button onClick={() => { setSourcePanel(null); setDataOpen(false); setTraceOpen(true) }}>Xem quá trình</button></div>}</div>}
        </div>
        <div className="composer-area">
        {showBottom && !!messages.length && <button className="scroll-bottom icon-button" onClick={() => { nearBottom.current = true; chatScroll.current?.scrollTo({ top: chatScroll.current.scrollHeight, behavior: 'instant' }); setShowBottom(false) }} aria-label="Về cuối hội thoại"><ArrowDown size={20}/></button>}
          {error && <div className="error-banner" role="alert"><div><strong>Chưa thể hoàn tất lượt hỏi</strong><p>{error}</p></div><button className="icon-button" onClick={() => setError('')} aria-label="Đóng thông báo"><X size={18}/></button></div>}
          {connectionMessage && <div className="connection-note" role="status"><p>{connectionMessage}</p><button className="button button-secondary" disabled={connecting} onClick={() => void refresh()}>Kiểm tra kết nối</button></div>}
          <Turnstile key={challengeVersion} onToken={setChallenge} hasSession={hasSession}/><div className="composer"><form id="chat-form" onSubmit={event => { event.preventDefault(); void send() }}><textarea ref={inputRef} value={input} onChange={event => setInput(event.target.value)} placeholder={mobile ? 'Nhập câu hỏi pháp luật…' : 'Hỏi về bồi thường, hỗ trợ, tái định cư…'} maxLength={4000} rows={1} aria-label="Câu hỏi pháp luật" onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && !touch) { event.preventDefault(); void send() } }}/></form><div className="composer-bottom"><span className="composer-hint">{touch ? 'Chỉ nhập tình huống đã ẩn danh' : 'Enter để gửi · Shift + Enter xuống dòng'}</span>{busy ? <button type="button" className="send-button" onClick={() => { stopReason.current = 'Bạn đã dừng lượt hỏi. Server không lưu đáp án để khôi phục.'; abortRef.current?.abort() }} aria-label="Dừng lượt hỏi"><Square size={18}/></button> : <button className="send-button" type="submit" form="chat-form" disabled={!input.trim()} aria-label="Gửi câu hỏi"><ArrowUp size={20}/></button>}</div></div>
          {!messages.length && <div className="topic-grid" aria-label="Gợi ý câu hỏi">{suggestions.map(question => <button key={question} onClick={() => { setInput(question); inputRef.current?.focus() }}><span>{question}</span></button>)}</div>}
          <span className="sr-only" aria-live="polite">{copiedId ? 'Đã sao chép đáp án' : ''}</span><p className="disclaimer">{messages.length ? 'Có thể có sai sót. Hãy kiểm tra nguồn trước khi áp dụng.' : 'Bản thử nghiệm · Chỉ nhập tình huống đã ẩn danh.'}</p>
        </div>
      </div>}
      {page === 'sources' && <section className="content-page"><h1>Thư viện văn bản</h1><p className="page-intro">Tìm văn bản và mở nguồn gốc để kiểm tra căn cứ.</p><div className="library-toolbar"><label className="searchbox"><Search size={20}/><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Tìm theo số hiệu hoặc tên văn bản…" aria-label="Tìm văn bản"/></label><label className="source-filter"><span>Loại nguồn</span><select aria-label="Loại nguồn" value={sourceKind} onChange={event => setSourceKind(event.target.value)}><option value="all">Tất cả nguồn</option>{Object.entries(sourceKinds).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label></div>
        {docsState === 'loading' ? <div className="empty-state" role="status"><LoaderCircle className="spin" size={24}/><p>Đang tải thư viện…</p></div> : docsState === 'error' ? <div className="empty-state" role="alert"><h2>Chưa tải được thư viện</h2><p>Không thể xác định danh sách tài liệu lúc này.</p><button className="button button-secondary" onClick={() => void refresh()}>Thử tải lại thư viện</button></div> : <><div className="library-count"><strong>{filteredDocs.length}/{docs.length} tài liệu trong thư viện</strong>{readiness?.checked_at && <span>Nguồn kiểm tra: {formatDate(readiness.checked_at)}</span>}</div>{!docs.length ? <div className="empty-state"><BookOpen size={28}/><h2>Corpus chưa được công bố</h2><p>Tài liệu xuất hiện khi nguồn được thu thập và đưa vào thư viện.</p><button className="button button-secondary" onClick={() => void refresh()}>Kiểm tra lại</button></div> : <><div className="document-list">{filteredDocs.map(document => <DocumentRow key={document.id} document={document} onOpen={doc => openSource(doc)}/>)}</div>{!filteredDocs.length && <div className="empty-state"><Search size={24}/><h2>Không tìm thấy văn bản</h2><p>Thử số hiệu, từ khóa ngắn hơn hoặc loại nguồn khác.</p><button className="button button-secondary" onClick={() => { setSearch(''); setSourceKind('all') }}>Xóa từ khóa</button></div>}</>}</>}
      </section>}
      {page === 'evaluation' && <section className="content-page"><h1>Đánh giá hệ thống</h1><p className="page-intro">Báo cáo kỹ thuật gắn với corpus và cấu hình đã chạy.</p>{evaluationWarning && <aside className="warning-note" role="status"><ShieldCheck size={20}/><p>{evaluationWarning}</p></aside>}<div className="evaluation-summary"><div><small>Corpus đang hoạt động</small><strong>{readiness?.corpus_release || 'Chưa công bố'}</strong></div><div><small>Phạm vi công bố</small><strong>Bản thử nghiệm</strong></div><div><small>Báo cáo khớp cấu hình</small><strong>{evaluation?.matches_active_configuration && evaluation?.matches_active_release ? 'Khớp phiên bản đang chạy' : 'Chưa có báo cáo khớp'}</strong></div></div>
        {evaluationState === 'loading' ? <p role="status">Đang tải báo cáo…</p> : evaluationState === 'error' ? <div className="empty-state" role="alert"><h2>Chưa tải được báo cáo</h2><button className="button button-secondary" onClick={() => void refresh()}>Thử tải lại báo cáo</button></div> : !evaluation || evaluation.status === 'not_run' ? <div className="empty-state"><h2>Chưa có kết quả kiểm tra trên bản này</h2><p>Kết quả sẽ được công bố sau khi chạy và rà soát.</p></div> : evaluationWarning ? <details><summary>Xem báo cáo của phiên bản trước</summary><EvaluationTable evaluation={evaluation}/></details> : <EvaluationTable evaluation={evaluation}/> }
      </section>}
    </main>
    {dataOpen && <DataPanel readiness={readiness} generation={generation} connecting={connecting} onRefresh={() => void refresh()} onClose={() => setDataOpen(false)}/>}
    {sourcePanel && <SourcePanel source={sourcePanel.source} citations={sourcePanel.citations} onSelect={citation => openSource(citation, sourcePanel.citations)} onClose={() => setSourcePanel(null)}/>}
    {traceOpen && <TracePanel trace={trace} onClose={() => setTraceOpen(false)}/>}
    {deletion && <ConfirmDialog title={deletion.title} busy={deleting} onCancel={() => setDeletion(null)} onConfirm={() => void confirmDeletion()}/>}
  </div>
}
function EvaluationTable({ evaluation }: { evaluation: Record<string, unknown> }) {
  const rows = (evaluation.case_results || []) as {id:string;status:string;review:string;seconds:number;note:string;citations_valid?:boolean|null;answer_origin?:string}[]
  const counts = (evaluation.results || []) as {pass?:number;partial?:number;fail?:number}[]
  const metrics = evaluation.metrics as {groups?:Record<string,{cases:number;pass:number;partial:number;fail:number}>;answer_origin?:Record<string,number>;usage?:Record<string,{samples:number;median:number|null;p95:number|null}>} | undefined
  const supplemental = evaluation.supplemental as {cases:number;completed:number;pass:number;partial:number;fail:number;execution_failures:number;note:string} | undefined
  const retrieval=evaluation.retrieval as {gold_recall_at_8?:number;storage_backend?:string;backend?:string;eligible_cases?:number}|undefined
  const faithfulness=evaluation.faithfulness as {sampled_faithfulness?:number|null;scored_cases:number;expected_cases:number;total_judged_claims:number;judge_model:string}|undefined
  const limitations = Array.isArray(evaluation.limitations) ? evaluation.limitations.filter((item): item is string => typeof item === 'string') : []
  const groupLabels: Record<string,string> = {answered:'Trả lời nội dung',clarification:'Hỏi làm rõ',insufficient:'Thiếu chứng cứ / ngoài phạm vi',execution_failure:'Lỗi thực thi'}
  return <><p>Model: <strong>{String(evaluation.model || 'Chưa xác định')}</strong> · {String(evaluation.status)}</p>
    <p>{counts[0]?.pass ?? 0} đạt · {counts[0]?.partial ?? 0} một phần · {counts[0]?.fail ?? 0} chưa đạt. Đây là đánh giá kỹ thuật, chưa được thẩm định pháp lý độc lập. Tổng số đạt gồm cả hỏi lại và từ chối, không phải độ chính xác trả lời pháp luật.</p>
    {retrieval&&<section className="metric-card"><h2>Gold Recall@8</h2><p> {retrieval.gold_recall_at_8==null?'Chưa đo':(retrieval.gold_recall_at_8*100).toFixed(1)+'%'} · Backend: {retrieval.storage_backend||retrieval.backend||'Xem artifact'}. Truy vấn gốc, không phải evidence sau agent routing.</p></section>}
    {faithfulness&&<section className="metric-card"><h2>Faithfulness mẫu</h2><p> {faithfulness.sampled_faithfulness==null?'Chưa chấm':(faithfulness.sampled_faithfulness*100).toFixed(1)+'%'} · {faithfulness.scored_cases}/{faithfulness.expected_cases} ca có điểm · {faithfulness.total_judged_claims} mệnh đề · Judge: {faithfulness.judge_model}. Cùng model, không phải thẩm định độc lập.</p></section>}
    {metrics?.groups && <div className="evaluation-table"><table><thead><tr><th>Nhóm hành vi</th><th>Số ca</th><th>Đạt</th><th>Một phần</th><th>Chưa đạt</th></tr></thead><tbody>{Object.entries(metrics.groups).map(([name,g])=><tr key={name}><td>{groupLabels[name] || name}</td><td>{g.cases}</td><td>{g.pass}</td><td>{g.partial}</td><td>{g.fail}</td></tr>)}</tbody></table></div>}
    {metrics?.answer_origin && <p>Luồng xử lý: {metrics.answer_origin.llm ?? 0} có bước sinh bằng LLM · {metrics.answer_origin.deterministic ?? 0} theo quy tắc · {metrics.answer_origin.unknown ?? 0} chưa xác định từ artifact.</p>}
    {metrics?.usage && <details className="evaluation-details"><summary>Thống kê vận hành</summary><div className="evaluation-table"><table><thead><tr><th>Chỉ số</th><th>Số mẫu</th><th>Median</th><th>p95</th></tr></thead><tbody>{Object.entries(metrics.usage).map(([name,v])=><tr key={name}><td>{({elapsed_ms:'Thời gian (ms)',token_usage:'Token',llm_calls:'Lần gọi LLM',tool_calls:'Lần gọi công cụ'} as Record<string,string>)[name] || name}</td><td>{v.samples}</td><td>{v.median ?? '—'}</td><td>{v.p95 ?? '—'}</td></tr>)}</tbody></table><p>Thống kê một lượt chạy CLI; không phải cam kết tốc độ của dịch vụ.</p></div></details>}
    {supplemental && <aside className="warning-note"><ShieldCheck size={20}/><div><strong>Kiểm tra bổ sung</strong><p>{supplemental.completed}/{supplemental.cases} ca đã thực hiện · {supplemental.pass} đạt · {supplemental.partial} một phần · {supplemental.fail} chưa đạt · {supplemental.execution_failures} lỗi thực thi.</p><p>{supplemental.note}</p></div></aside>}
    {!!limitations.length && <ul className="secondary-copy">{limitations.map((text,index)=><li key={index}>{text}</li>)}</ul>}
    <details className="evaluation-details" open><summary>Kết quả từng ca</summary><div className="evaluation-table"><table><thead><tr><th>Ca</th><th>Kết quả</th><th>Giây</th><th>Nguồn trích dẫn</th><th>Nhận xét</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{r.id}</td><td>{({pass:'Đạt',partial:'Một phần',fail:'Chưa đạt'} as Record<string,string>)[r.review] || 'Chưa rà soát'}</td><td>{r.seconds.toFixed(1)}</td><td>{r.citations_valid == null ? 'Không áp dụng' : r.citations_valid ? 'Khớp corpus' : 'Không khớp'}</td><td>{r.note}</td></tr>)}</tbody></table></div></details>
  </>
}
export default App
