import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { ArrowUp, ArrowUpRight, BookOpen, Check, ChevronRight, CircleHelp, Clock3, FileText, GitBranch, Landmark, Layers3, LoaderCircle, MapPin, Plus, Search, ShieldCheck, Square, X } from 'lucide-react'
import { ask, BASE, BACKEND_CONFIGURED, getJSON, getSession, restoreSession, type Citation, type LegalDocument, type Project, type Readiness, type Result, type Session, type Trace } from './api'

type Page = 'chat' | 'sources' | 'projects' | 'evaluation'
type Message = { id: string; role: 'user' | 'assistant'; content: string; result?: Result }
const suggestions = [
  ['Bồi thường & hỗ trợ', 'Đất nông nghiệp bị thu hồi ở Hà Nội được bồi thường và hỗ trợ theo những điều kiện nào?'],
  ['Tái định cư', 'Những thông tin nào cần có để xác định một hộ gia đình đủ điều kiện tái định cư?'],
  ['Quy hoạch & dự án', 'Quy hoạch được phê duyệt có đồng nghĩa với việc đất của tôi sẽ bị thu hồi không?'],
  ['Hiệu lực văn bản', 'Quyết định 56/2024/QĐ-UBND còn áp dụng cho hồ sơ thu hồi đất nào?'],
]
const labels: Record<string, string> = { answered: 'Có căn cứ', clarification_needed: 'Cần bổ sung thông tin', insufficient_evidence: 'Chưa đủ căn cứ', limited: 'Giới hạn lượt dùng', error: 'Chưa xử lý được' }
const kinds: Record<string, string> = { legal: 'Văn bản pháp luật', project_decision: 'Hồ sơ dự án', official_news: 'Thông tin chính thức' }

function App() {
  const [page, setPage] = useState<Page>('chat')
  const [project, setProject] = useState(''), [asOf, setAsOf] = useState(''), [mode, setMode] = useState('agentic')
  const [input, setInput] = useState(''), [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [readiness, setReadiness] = useState<Readiness | null>(null), [connecting, setConnecting] = useState(false)
  const [docs, setDocs] = useState<LegalDocument[]>([]), [projects, setProjects] = useState<Project[]>([])
  const [trace, setTrace] = useState<Trace[]>([]), [traceOpen, setTraceOpen] = useState(false)
  const [selectedSource, setSelectedSource] = useState<Citation | LegalDocument | null>(null)
  const [evaluation, setEvaluation] = useState<Record<string, unknown> | null>(null), [search, setSearch] = useState('')
  const sessionRef = useRef<Session | null>(null), abortRef = useRef<AbortController | null>(null), bottom = useRef<HTMLDivElement>(null)

  async function refresh(signal?: AbortSignal) {
    if (!BACKEND_CONFIGURED) { setReadiness({ status: 'not_deployed' }); return }
    setConnecting(true)
    try {
      const response = await fetch(BASE + '/readyz', { signal })
      if (response.headers.get('content-type')?.includes('application/json')) setReadiness(await response.json())
      else setReadiness({ status: 'starting' })
      const [sourceData, projectData, evalData] = await Promise.allSettled([
        getJSON<{ documents: LegalDocument[] }>('/api/v1/documents', signal),
        getJSON<{ projects: Project[] }>('/api/v1/projects', signal),
        getJSON<Record<string, unknown>>('/api/v1/evaluations/latest', signal),
      ])
      if (sourceData.status === 'fulfilled') setDocs(sourceData.value.documents)
      if (projectData.status === 'fulfilled') setProjects(projectData.value.projects)
      if (evalData.status === 'fulfilled') setEvaluation(evalData.value)
    } catch { setReadiness({ status: 'starting' }) }
    finally { setConnecting(false) }
  }
  useEffect(() => { const c = new AbortController(); void refresh(c.signal); return () => c.abort() }, [])
  useEffect(() => {
    if (!BACKEND_CONFIGURED) return
    const c = new AbortController(), cached = sessionStorage.getItem('landlaw-session')
    void restoreSession(c.signal).then(restored => {
      if (!restored || c.signal.aborted || cached !== sessionStorage.getItem('landlaw-session') || sessionRef.current) return
      sessionRef.current = restored.session
      setMessages(existing => existing.length ? existing : restored.messages.map(m => ({ id: m.payload.trace_id || crypto.randomUUID(), role: m.role,
        content: m.payload.content, result: m.role === 'assistant' ? m.payload as Result : undefined })))
    }).catch(() => {})
    return () => c.abort()
  }, [])
  useEffect(() => {
    if (!traceOpen && !selectedSource) return
    const previous = document.activeElement as HTMLElement | null
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]')
    const controls = () => Array.from(dialog?.querySelectorAll<HTMLElement>('button,a[href],input,select,textarea,[tabindex="0"]') || [])
    controls()[0]?.focus()
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setTraceOpen(false); setSelectedSource(null) }
      if (e.key === 'Tab') {
        const elements = controls(), first = elements[0], last = elements.at(-1)
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus() }
        if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus() }
      }
    }
    window.addEventListener('keydown', handler)
    return () => { window.removeEventListener('keydown', handler); previous?.focus() }
  }, [traceOpen, selectedSource])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, busy])
  useEffect(() => () => abortRef.current?.abort(), [])

  async function send(text = input) {
    if (busy || !text.trim()) return
    if (!BACKEND_CONFIGURED) { setError('Backend chưa được triển khai. Bản xem trước hiện chỉ có giao diện.'); return }
    const question = text.trim()
    setPage('chat'); setInput(''); setError(''); setBusy(true); setTrace([])
    setMessages(m => [...m, { id: crypto.randomUUID(), role: 'user', content: question }])
    const controller = new AbortController(); abortRef.current = controller
    const timeout = window.setTimeout(() => controller.abort(), 180000)
    let received = false
    try {
      sessionRef.current ||= await getSession()
      await ask(sessionRef.current, question, project, asOf, mode, controller.signal, (event, data) => {
        if (event === 'progress') setTrace(t => [...t, data as Trace])
        if (event === 'result') {
          received = true
          const result = data as Result
          setMessages(m => [...m, { id: result.trace_id, role: 'assistant', content: result.content, result }])
          setTrace(result.trace)
        }
        if (event === 'failure') { received = true; setError((data as { content: string }).content) }
      })
      if (!received) throw new Error('Kết nối kết thúc trước khi có kết quả. Vui lòng thử lại.')
    } catch (e) { setError(e instanceof Error && e.name !== 'AbortError' ? e.message : 'Lượt hỏi đã dừng hoặc quá thời gian chờ.') }
    finally { window.clearTimeout(timeout); setBusy(false); abortRef.current = null }
  }

  function newConversation() {
    abortRef.current?.abort(); sessionRef.current = null; sessionStorage.removeItem('landlaw-session')
    setMessages([]); setTrace([]); setError(''); setPage('chat')
  }

  const ready = readiness?.status === 'ready'
  const evaluationWarning = evaluation && evaluation.status !== 'not_run' &&
    (!evaluation.matches_active_release || !evaluation.matches_active_configuration || evaluation.status !== 'reviewed')
    ? 'Báo cáo này chưa chứng nhận chất lượng bản đang hoạt động: kết quả có thể thuộc corpus/cấu hình model khác hoặc chưa được rà soát đầy đủ.' : ''
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={e => { e.preventDefault(); setPage('chat') }}><span className="brand-mark"><Landmark size={23}/></span><span>Hà Nội<span className="brand-sub">PHÁP LUẬT ĐẤT ĐAI</span></span></a>
      <button className="new-chat" onClick={newConversation}><Plus size={17}/> Cuộc trò chuyện mới</button>
      <div className="nav-label">KHÔNG GIAN TRA CỨU</div>
      <nav aria-label="Điều hướng chính">
        {([['chat', CircleHelp, 'Hỏi đáp pháp luật'], ['sources', BookOpen, 'Thư viện văn bản'], ['projects', Layers3, 'Dự án trọng điểm'], ['evaluation', GitBranch, 'Đánh giá hệ thống']] as const).map(([id, Icon, label]) => <button key={id} className={page === id ? 'active' : ''} onClick={() => setPage(id)}><Icon size={18}/>{label}{page === id && <span className="nav-dot"/>}</button>)}
      </nav>
      <div className="sidebar-note"><ShieldCheck size={21}/><strong>Bắt đầu từ căn cứ</strong><p>Mỗi kết luận cần có nguồn. Khi thiếu dữ kiện, hệ thống sẽ hỏi thêm.</p></div>
      <div className="sidebar-footer"><span className="region-icon"><MapPin size={17}/></span><div>Thành phố Hà Nội<small>Nguồn chính thức · Tiếng Việt</small></div></div>
    </aside>
    <main className="main">
      {page === 'evaluation' && evaluationWarning && <aside className="connection-note" role="status">{evaluationWarning}</aside>}
      <header className="topbar"><div><span className="breadcrumb">Không gian tra cứu</span><ChevronRight size={13}/><span>{page === 'chat' ? 'Hỏi đáp pháp luật' : page === 'sources' ? 'Thư viện văn bản' : page === 'projects' ? 'Dự án trọng điểm' : 'Đánh giá hệ thống'}</span></div><button className="status-chip" onClick={() => void refresh()} disabled={connecting}><span className={ready ? 'status-dot ready' : 'status-dot'}/>{connecting ? 'Đang kết nối' : ready ? 'Sẵn sàng tra cứu' : 'Kiểm tra kết nối'}{connecting && <LoaderCircle size={12} className="spin"/>}</button></header>
      {['demo','technical_demo','accepted'].includes(readiness?.publication_profile || '') && <aside className="connection-note" role="note"><strong>{readiness?.quality_status === 'accepted' ? 'Đã đạt bộ kiểm thử nghiệm thu đối chiếu nguồn.' : readiness?.publication_profile === 'technical_demo' ? 'Demo kỹ thuật — chưa nghiệm thu pháp lý.' : 'Demo — chưa hoàn tất nghiệm thu.'}</strong> Chỉ trả lời trong phạm vi nguồn đã kiểm tra. {readiness?.checked_at && <>Dữ liệu kiểm tra: {new Date(readiness.checked_at).toLocaleDateString('vi-VN')}. </>}{!!readiness?.coverage_gaps?.length && <details><summary>Các nguồn chưa đủ dữ liệu ({readiness.coverage_gaps.length})</summary><ul>{readiness.coverage_gaps.map(g => <li key={g.document_id}>{g.title}: {g.reason}</li>)}</ul></details>}</aside>}
      {page === 'chat' && <>
        <div className="filterbar"><span className="filter-label"><MapPin size={14}/> Phạm vi</span><label className="sr-only" htmlFor="project">Dự án</label><select id="project" value={project} onChange={e => setProject(e.target.value)}><option value="">Toàn Hà Nội</option><option value="ring4">Vành đai 4</option><option value="songhong">Trục cảnh quan sông Hồng</option><option value="olympic">Khu đô thị thể thao Olympic</option></select><span className="filter-divider"/><Clock3 size={14}/><label className="sr-only" htmlFor="asof">Thời điểm áp dụng</label><input id="asof" type="date" value={asOf} onChange={e => setAsOf(e.target.value)} aria-label="Thời điểm áp dụng, để trống là hôm nay"/><span className="filter-spacer"/><label className="sr-only" htmlFor="mode">Chế độ truy xuất</label><select id="mode" value={mode} onChange={e => setMode(e.target.value)}><option value="agentic">Agentic RAG</option><option value="baseline">RAG thông thường</option></select></div>
        <div className="chat-scroll">
          {!messages.length ? <div className="welcome"><div className="eyebrow"><span/> TRA CỨU TỪ NGUỒN CHÍNH THỨC</div><h1>Hiểu rõ pháp luật.<br/><em>Chủ động với quyền lợi của bạn.</em></h1><p className="intro">Hỏi về đất đai, bồi thường, tái định cư và quy hoạch tại Hà Nội.<br className="desktop-break"/> Tìm căn cứ phù hợp với địa bàn, thời điểm và tình huống của bạn.</p><div className="topic-grid">{suggestions.map(([title, question], i) => <button key={title} onClick={() => void send(question)} disabled={busy}><span className="topic-number">0{i+1}</span><strong>{title}</strong><p>{question}</p><ArrowUpRight size={17}/></button>)}</div><div className="welcome-foot"><FileText size={15}/><span>Văn bản pháp luật</span><span className="tiny-dot"/><span>Hồ sơ dự án</span><span className="tiny-dot"/><span>Kiểm tra thời điểm áp dụng</span></div></div> : <div className="messages">{messages.map(message => <article key={message.id} className={`message ${message.role}`}>
            <div className="message-label">{message.role === 'user' ? 'Bạn' : <><span className="mini-brand"><Landmark size={15}/></span>Hà Nội · Pháp luật đất đai</>}</div>
            {message.result && <div className={`answer-status ${message.result.status}`}><ShieldCheck size={14}/>{labels[message.result.status] || message.result.status}</div>}
            <div className="message-body"><ReactMarkdown components={{ a: ({ children }) => <span>{children}</span> }}>{message.content}</ReactMarkdown></div>
            {!!message.result?.citations.length && <div className="citations">{message.result.citations.map((c, index) => <button key={c.id} onClick={() => setSelectedSource(c)}><FileText size={14}/><span>{index+1}. {c.document_number || c.title}<small>{c.locator}</small></span><ArrowUpRight size={14}/></button>)}</div>}
            {message.result && <button className="trace-link" onClick={() => { setTrace(message.result!.trace); setTraceOpen(true) }}><GitBranch size={14}/>Xem quá trình kiểm chứng<span>{message.result.tool_calls} công cụ · {(message.result.elapsed_ms/1000).toFixed(1)} giây</span></button>}
          </article>)}{busy && <div className="working" role="status"><LoaderCircle size={18} className="spin"/><span>{trace.at(-1)?.summary || 'Đang kết nối và chuẩn bị tra cứu…'}</span><button onClick={() => setTraceOpen(true)}>Xem quá trình</button></div>}<div ref={bottom}/></div>}
        </div>
        <div className="composer-area">{error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')} aria-label="Đóng thông báo"><X size={15}/></button></div>}{!ready && !connecting && <div className="connection-note">{readiness?.status === 'not_deployed' ? 'Bản xem trước giao diện. Backend chưa được triển khai và chưa có corpus công bố.' : readiness?.database && !readiness.llm_configured ? 'Chưa cấu hình API AI. Hệ thống sẽ báo rõ giới hạn khi bạn gửi câu hỏi.' : readiness?.database && !readiness.corpus_release ? 'Bộ dữ liệu đang chờ công bố. Bạn có thể xem trạng thái trong thư viện.' : 'Backend có thể đang khởi động. Kết nối đầu tiên có thể mất khoảng một phút.'}</div>}<form className="composer" onSubmit={e => { e.preventDefault(); void send() }}><textarea value={input} onChange={e => setInput(e.target.value)} placeholder="Mô tả câu hỏi của bạn, kèm địa bàn và thời điểm nếu có…" maxLength={4000} rows={2} aria-label="Câu hỏi pháp luật" onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send() } }}/><div className="composer-bottom"><span><ShieldCheck size={13}/> Chỉ nhập tình huống đã ẩn danh</span>{busy ? <button type="button" className="send-button" onClick={() => abortRef.current?.abort()} aria-label="Dừng lượt hỏi"><Square size={16}/></button> : <button className="send-button" type="submit" disabled={!input.trim()} aria-label="Gửi câu hỏi"><ArrowUp size={21}/></button>}</div></form><p className="disclaimer">Thông tin để tham khảo và đối chiếu hồ sơ. Quyền lợi cụ thể cần được xác định từ tài liệu và cơ quan có thẩm quyền.</p></div>
      </>}
      {page === 'sources' && <section className="content-page"><div className="eyebrow">THƯ VIỆN NGUỒN</div><h1>Căn cứ có thể kiểm tra.</h1><p className="page-intro">Văn bản được công bố trong corpus, kèm thời điểm kiểm tra và trạng thái xác minh. Văn bản lịch sử được giữ để đối chiếu hồ sơ cũ.</p><label className="searchbox"><Search size={18}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Tìm số hiệu hoặc tên văn bản…"/></label><div className="library-count">{docs.length} tài liệu đã công bố</div>{!docs.length && <div className="empty-state"><BookOpen size={30}/><h2>Corpus chưa được công bố</h2><p>Tài liệu chỉ xuất hiện sau bước thu thập, kiểm tra chất lượng và công bố phiên bản. Danh mục nguồn không được xem là toàn văn đã xử lý.</p><button onClick={() => void refresh()}>Kiểm tra lại</button></div>}<div className="document-list">{docs.filter(d => `${d.title} ${d.document_number}`.toLocaleLowerCase('vi').includes(search.toLocaleLowerCase('vi'))).map(d => <button key={d.id} onClick={() => setSelectedSource(d)}><span className="doc-icon"><FileText size={21}/></span><span><small>{kinds[d.source_kind]}</small><strong>{d.title}</strong><p>{d.document_number} · Kiểm tra {new Date(d.checked_at).toLocaleDateString('vi-VN')}</p></span><span className={`doc-state ${d.applicability_verified ? 'verified' : ''}`}>{d.effective_to ? 'Có mốc kết thúc hiệu lực' : d.applicability_verified ? 'Đã xác minh' : 'Cần kiểm tra tính áp dụng'}</span><ArrowUpRight size={17}/></button>)}</div></section>}
      {page === 'projects' && <section className="content-page"><div className="eyebrow">HÀ NỘI ĐANG CHUYỂN MÌNH</div><h1>Ba dự án. Từng căn cứ.</h1><p className="page-intro">Tra cứu bối cảnh và hồ sơ công khai. Phạm vi tổng thể của dự án không xác định việc thu hồi một thửa đất cụ thể.</p><div className="project-grid">{projects.map((p, i) => <article key={p.id}><div className={`project-map map-${i}`}><span className="map-line"/><span className="map-line second"/><span className="map-node"/><span className="map-node second"/><span className="map-caption">HỒ SƠ DỰ ÁN · 0{i+1}</span></div><div className="project-copy"><small>HÀ NỘI</small><h2>{p.name}</h2><p>{p.description}</p><div className="project-source-count"><FileText size={14}/>{docs.filter(d => d.project === p.id).length} nguồn đã công bố / {p.source_ids.length} nguồn trong danh mục</div><button onClick={() => { setProject(p.id); setPage('chat'); setInput(p.questions[0] || `Tôi cần kiểm tra hồ sơ pháp lý nào của ${p.name}?`) }}>Tra cứu dự án<ArrowUpRight size={16}/></button></div></article>)}</div>{!projects.length && <div className="empty-state">Chưa tải được hồ sơ dự án. <button onClick={() => void refresh()}>Thử lại</button></div>}</section>}
      {page === 'evaluation' && <section className="content-page"><div className="eyebrow">ĐÁNH GIÁ CÓ THỂ TÁI LẬP</div><h1>Chất lượng được đo.</h1><p className="page-intro">So sánh agentic RAG và RAG thông thường trên cùng corpus, model và bộ câu hỏi. Các chỉ số chỉ được hiển thị khi đã chạy đánh giá thật.</p>{!evaluation || evaluation.status === 'not_run' ? <div className="empty-state"><GitBranch size={30}/><h2>Chưa có kết quả benchmark</h2><p>Bộ câu hỏi cần căn cứ tham chiếu được kiểm tra và một lượt chạy API thật. Hệ thống không tạo số liệu đánh giá mẫu.</p><button onClick={() => void refresh()}>Kiểm tra báo cáo mới</button></div> : <div className="evaluation-panel"><strong>Trạng thái: {String(evaluation.status)}</strong><pre>{JSON.stringify(evaluation, null, 2)}</pre></div>}<div className="method-grid"><div><strong>01 · Chứng cứ</strong><p>Đo retrieval và độ hỗ trợ của nguồn dẫn, không chỉ độ trôi chảy của câu trả lời.</p></div><div><strong>02 · Tính áp dụng</strong><p>Kiểm tra thời điểm, chuyển tiếp, địa bàn và giới hạn hồ sơ dự án.</p></div><div><strong>03 · Chi phí thực thi</strong><p>Báo cáo độ trễ và số lần gọi API, kể cả trường hợp agent không cải thiện.</p></div></div></section>}
    </main>
    {traceOpen && <div className="modal-backdrop" onClick={() => setTraceOpen(false)}><section className="drawer" role="dialog" aria-modal="true" aria-label="Quá trình kiểm chứng" onClick={e => e.stopPropagation()}><header><div><GitBranch size={20}/><h2>Quá trình kiểm chứng</h2></div><button onClick={() => setTraceOpen(false)} aria-label="Đóng"><X size={20}/></button></header><p className="drawer-intro">Sự kiện thực thi và nguồn đã truy xuất. Chỉ hiển thị kết quả quan sát được của từng bước.</p><ol className="trace-timeline">{trace.map((t, i) => <li key={i}><span className="trace-check"><Check size={13}/></span><div><small>{t.tool || t.step} · {(t.elapsed_ms/1000).toFixed(1)}s</small><p>{t.summary}</p>{t.document_ids.map(id => <span className="trace-doc" key={id}>{id}</span>)}</div></li>)}</ol>{!trace.length && <p>Chưa có sự kiện. Gửi một câu hỏi để bắt đầu.</p>}</section></div>}
    {selectedSource && <div className="modal-backdrop" onClick={() => setSelectedSource(null)}><section className="source-modal" role="dialog" aria-modal="true" aria-label="Chi tiết nguồn" onClick={e => e.stopPropagation()}><header><span><FileText size={19}/>NGUỒN DẪN</span><button onClick={() => setSelectedSource(null)} aria-label="Đóng"><X size={20}/></button></header><h2>{selectedSource.title}</h2><div className="source-meta">{selectedSource.document_number}<span>Kiểm tra {new Date(selectedSource.checked_at).toLocaleDateString('vi-VN')}</span></div>{'excerpt' in selectedSource ? <><strong>{selectedSource.locator}</strong><blockquote>{selectedSource.excerpt}</blockquote><p className="source-applicability">Trạng thái căn cứ trong lượt hỏi: {selectedSource.applicability}</p>{selectedSource.page && <p>Trang nguồn: {selectedSource.page}</p>}{selectedSource.source_url && <a className="source-external" href={selectedSource.source_url} target="_blank" rel="noopener noreferrer">Mở trang PDF gốc<ArrowUpRight size={16}/></a>}</> : <p>Ngày bắt đầu hiệu lực: {selectedSource.effective_from || 'Chưa xác minh'}<br/>Ngày kết thúc hiệu lực: {selectedSource.effective_to || 'Chưa xác định mốc kết thúc'}</p>}{selectedSource.source_review_notes && <p className="source-applicability">{selectedSource.source_review_notes}</p>}<a className="source-external" href={selectedSource.url} target="_blank" rel="noopener noreferrer">Mở nguồn chính thức<ArrowUpRight size={16}/></a></section></div>}
  </div>
}
export default App
