import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { ArrowUp, ArrowUpRight, BookOpen, ChevronRight, CircleHelp, FileText, GitBranch, Landmark, LoaderCircle, MapPin, Menu, Plus, Search, ShieldCheck, Square, X } from 'lucide-react'
import { ask, BASE, BACKEND_CONFIGURED, getJSON, getSession, restoreSession, type Citation, type LegalDocument, type Project, type Readiness, type Result, type Session, type Trace } from './api'
import { DataPanel, DocumentRow, formatDate, SourcePanel, TracePanel } from './ui'
import { ScopeControl } from './ChatScope'

type Page = 'chat' | 'sources' | 'projects' | 'evaluation'
type Message = { id: string; role: 'user' | 'assistant'; content: string; result?: Result }
const suggestions = [
  { title: 'Bồi thường tài sản', description: 'Chi phí di chuyển được tính ra sao?', icon: FileText, question: 'Điều 104 Luật Đất đai 2024 quy định bồi thường chi phí di chuyển tài sản như thế nào?' },
  { title: 'Điều kiện tái định cư', description: 'Cần đối chiếu những hồ sơ nào?', icon: Landmark, question: 'Những thông tin nào cần có để xác định một hộ gia đình đủ điều kiện tái định cư?' },
  { title: 'Dự án Vành đai 4', description: 'Thông tin nào đã được công bố?', icon: MapPin, question: 'Từ thông tin tổng quan dự án Vành đai 4 có thể kết luận thửa đất bị thu hồi không?' },
]
const pageLabels: Record<Page, string> = { chat: 'Hỏi đáp pháp luật', sources: 'Thư viện văn bản', projects: 'Vành đai 4', evaluation: 'Đánh giá hệ thống' }

const labels: Record<string, string> = { answered: 'Có căn cứ', clarification_needed: 'Cần bổ sung thông tin', insufficient_evidence: 'Chưa đủ căn cứ', limited: 'Giới hạn lượt dùng', error: 'Chưa xử lý được' }

function App() {
  const [page, setPage] = useState<Page>('chat')
  const [navOpen, setNavOpen] = useState(false)
  const [project, setProject] = useState(''), [asOf, setAsOf] = useState('')
  const [dataOpen, setDataOpen] = useState(false)
  const [input, setInput] = useState(''), [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [readiness, setReadiness] = useState<Readiness | null>(null), [connecting, setConnecting] = useState(false)
  const [docs, setDocs] = useState<LegalDocument[]>([]), [projects, setProjects] = useState<Project[]>([])
  const [trace, setTrace] = useState<Trace[]>([]), [traceOpen, setTraceOpen] = useState(false)
  const [selectedSource, setSelectedSource] = useState<Citation | LegalDocument | null>(null)
  const [evaluation, setEvaluation] = useState<Record<string, unknown> | null>(null), [search, setSearch] = useState('')
  const inputRef = useRef<HTMLTextAreaElement | null>(null)
  const navTriggerRef = useRef<HTMLButtonElement | null>(null)
  const sessionRef = useRef<Session | null>(null), abortRef = useRef<AbortController | null>(null), bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const textarea = inputRef.current
    if (textarea) { textarea.style.height = 'auto'; textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px` }
  }, [input, page])

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
    if (!traceOpen && !selectedSource && !navOpen && !dataOpen) return
    const previous = document.activeElement as HTMLElement | null
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]')
    const controls = () => Array.from(dialog?.querySelectorAll<HTMLElement>('button,a[href],input,select,textarea,[tabindex="0"]') || [])
    controls()[0]?.focus()
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setTraceOpen(false); setSelectedSource(null); setNavOpen(false); setDataOpen(false) }
      if (e.key === 'Tab') {
        const elements = controls(), first = elements[0], last = elements.at(-1)
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus() }
        if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus() }
      }
    }
    window.addEventListener('keydown', handler)
    return () => { window.removeEventListener('keydown', handler); if (navOpen) navTriggerRef.current?.focus(); else previous?.focus() }
  }, [traceOpen, selectedSource, navOpen, dataOpen])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, busy])
  useEffect(() => () => abortRef.current?.abort(), [])

  async function send(text = input) {
    if (busy || !text.trim()) return
    if (!BACKEND_CONFIGURED) { setError('Backend chưa được triển khai. Bản xem trước hiện chỉ có giao diện.'); return }
    const question = text.trim()
    setPage('chat'); setNavOpen(false); setInput(''); setError(''); setBusy(true); setTrace([])
    setMessages(m => [...m, { id: crypto.randomUUID(), role: 'user', content: question }])
    const controller = new AbortController(); abortRef.current = controller
    const timeout = window.setTimeout(() => controller.abort(), 180000)
    let received = false
    try {
      sessionRef.current ||= await getSession()
      await ask(sessionRef.current, question, project, asOf, controller.signal, (event, data) => {
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
    setMessages([]); setTrace([]); setError(''); setPage('chat'); setNavOpen(false)
  }

  const ready = readiness?.status === 'ready'
  const panelOpen = traceOpen || !!selectedSource || dataOpen
  const activeProject = projects.find(p => p.id === 'ring4')
  const filteredDocs = docs.filter(d => `${d.title} ${d.document_number || ''}`.normalize('NFC').toLocaleLowerCase('vi').includes(search.normalize('NFC').toLocaleLowerCase('vi')))
  const evaluationWarning = evaluation && evaluation.status !== 'not_run' &&
    (!evaluation.matches_active_release || !evaluation.matches_active_configuration || evaluation.status !== 'reviewed')
    ? 'Chưa hoàn tất đánh giá trên cấu hình đang hoạt động. Không diễn giải kết quả của phiên bản khác thành chất lượng bản hiện tại.' : ''
  const openSource = (source: Citation | LegalDocument) => { setDataOpen(false); setTraceOpen(false); setSelectedSource(source) }
  const navigate = (target: Page) => { setDataOpen(false); setPage(target); setNavOpen(false); setTraceOpen(false); setSelectedSource(null) }


  return <div className={`app-shell page-${page} ${panelOpen ? 'panel-open' : ''} ${navOpen ? 'nav-open' : ''}`}>
    <a className="skip-link" href="#main-content">Đến nội dung chính</a>
    {navOpen && <button className="nav-scrim" tabIndex={-1} onClick={() => setNavOpen(false)} aria-label="Đóng menu điều hướng"/>}
    <aside className="sidebar" id="main-navigation" role={navOpen ? 'dialog' : undefined} aria-modal={navOpen || undefined} aria-label={navOpen ? 'Menu điều hướng' : undefined}>
      <button className="icon-button mobile-nav-close" onClick={() => setNavOpen(false)} aria-label="Đóng menu"><X size={20}/></button>
      <a className="brand" href="#" onClick={e => { e.preventDefault(); navigate('chat') }}><Landmark size={28}/><span>Hà Nội<span className="brand-sub">PHÁP LUẬT ĐẤT ĐAI</span></span></a>
      <button className="button button-primary new-chat" onClick={newConversation} disabled={busy}><Plus size={18}/>Cuộc trò chuyện mới</button>
      <div className="nav-label">KHÔNG GIAN TRA CỨU</div>
      <nav aria-label="Điều hướng chính">{(Object.entries(pageLabels) as [Page, string][]).map(([id, label]) => <button key={id} aria-current={page === id ? 'page' : undefined} className={page === id ? 'active' : ''} onClick={() => navigate(id)}>{label}</button>)}</nav>
      <div className="sidebar-note"><ShieldCheck size={20}/><strong>Bản thử nghiệm</strong><p>Chỉ hỗ trợ dự án Vành đai 4.<br/>Luôn đối chiếu hồ sơ thực tế.</p></div>
    </aside>
    <main className="main" id="main-content" inert={navOpen}>
      <header className="topbar"><div className="topbar-title"><button className="icon-button mobile-menu" ref={navTriggerRef} onClick={() => setNavOpen(true)} aria-label="Mở menu điều hướng" aria-expanded={navOpen} aria-controls="main-navigation"><Menu size={20}/></button><span>{page === 'chat' ? 'Hanoi Land Law' : pageLabels[page]}</span></div><div className="topbar-actions"><button className="icon-button data-trigger" onClick={() => { setSelectedSource(null); setTraceOpen(false); setDataOpen(true) }} aria-label="Thông tin dữ liệu và kết nối" title="Thông tin dữ liệu và kết nối"><CircleHelp size={20}/><span className={ready ? 'status-dot ready' : 'status-dot'}/></button><button className="icon-button mobile-new-chat" onClick={newConversation} disabled={busy} aria-label="Cuộc trò chuyện mới"><Plus size={20}/></button></div></header>
      {page === 'chat' && <>
        <div className={`chat-workspace ${panelOpen ? 'has-panel' : ''} ${messages.length ? 'has-messages' : 'is-empty'}`}>
          <div className="chat-scroll">
            {!messages.length ? <div className="welcome"><h1>Tìm đúng căn cứ.</h1><p className="intro">Tra cứu pháp luật đất đai Hà Nội, kèm nguồn để đối chiếu.</p></div>
            : <div className="messages">{messages.map(message => <article key={message.id} className={`message ${message.role}`}>
              <div className="message-label">{message.role === 'user' ? 'Bạn' : <><Landmark size={20}/>Hanoi Land Law</>}</div>
              {message.result && <span className={`answer-status ${message.result.status}`}>{labels[message.result.status] || message.result.status}</span>}
              <div className="message-body"><ReactMarkdown components={{ a: ({ children }) => <span>{children}</span> }}>{message.content}</ReactMarkdown></div>
              {!!message.result?.citations?.length && <div className="citations">{message.result.citations.map((c, index) => <button key={c.id} onClick={() => openSource(c)}><span className="citation-heading"><FileText size={18}/><strong>[{index + 1}] {c.document_number || c.title}</strong></span><span className="citation-location">{c.locator}</span><span className="citation-action">Mở đoạn căn cứ<ArrowUpRight size={14}/></span></button>)}</div>}
              {message.result && <button className="trace-link" onClick={() => { setSelectedSource(null); setTrace(message.result!.trace || []); setTraceOpen(true) }}><GitBranch size={16}/>Xem quá trình kiểm chứng<ChevronRight size={14}/><span>{message.result.tool_calls} công cụ · {(message.result.elapsed_ms / 1000).toFixed(1)} giây</span></button>}
            </article>)}{busy && <div className="working" role="status"><LoaderCircle size={18} className="spin"/><span>{trace.at(-1)?.summary || 'Đang kết nối và chuẩn bị tra cứu…'}</span><button onClick={() => { setSelectedSource(null); setTraceOpen(true) }}>Xem quá trình</button></div>}<div ref={bottom}/></div>}
          </div>
          <div className="composer-area">{error && <div className="error-banner" role="alert"><div><strong>Chưa thể hoàn tất lượt hỏi</strong><p>{error}</p></div><button className="icon-button" onClick={() => setError('')} aria-label="Đóng thông báo"><X size={18}/></button></div>}
            {!ready && <div className="connection-note" role="status">{connecting ? 'Đang kết nối backend. Lần khởi động đầu có thể mất khoảng một phút…' : readiness?.status === 'not_deployed' ? 'Bản xem trước giao diện. Backend chưa được triển khai.' : readiness?.database && !readiness.llm_configured ? 'Chưa cấu hình API AI; hệ thống sẽ báo rõ giới hạn khi gửi câu hỏi.' : readiness?.database && !readiness.corpus_release ? 'Bộ dữ liệu đang chờ công bố.' : 'Backend có thể đang khởi động. Bạn có thể thử kết nối lại.'}</div>}
            <div className="composer"><form id="chat-form" className="composer-input" onSubmit={e => { e.preventDefault(); void send() }}><textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)} placeholder={messages.length ? "Hỏi tiếp…" : "Nhập câu hỏi của bạn…"} maxLength={4000} rows={1} aria-label="Câu hỏi pháp luật" onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send() } }}/></form><div className="composer-bottom"><ScopeControl compact={messages.length > 0} project={project} asOf={asOf} onProjectChange={setProject} onDateChange={setAsOf}/>{busy ? <button type="button" className="send-button" onClick={() => abortRef.current?.abort()} aria-label="Dừng lượt hỏi"><Square size={18}/></button> : <button className="send-button" type="submit" form="chat-form" disabled={!input.trim()} aria-label="Gửi câu hỏi"><ArrowUp size={20}/></button>}</div></div>{!messages.length && <div className="topic-grid">{suggestions.map(({title, description, question, icon: Icon}) => <button key={title} onClick={() => void send(question)} disabled={busy}><Icon size={20} className="topic-icon"/><strong>{title}</strong><p>{description}</p><ArrowUpRight size={16}/></button>)}</div>}{!messages.length && <p className="disclaimer">Bản thử nghiệm · Chỉ nhập tình huống đã ẩn danh.</p>}
          </div>
        </div>
      </>}
      {page === 'sources' && <section className="content-page"><h1>Thư viện văn bản</h1><p className="page-intro">Tìm văn bản và mở nguồn gốc để kiểm tra căn cứ.</p><label className="searchbox"><Search size={20}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Tìm theo số hiệu hoặc tên văn bản…" aria-label="Tìm văn bản"/></label><div className="library-count"><strong>{docs.length} tài liệu đã công bố</strong>{readiness?.checked_at && <span>Nguồn kiểm tra: {formatDate(readiness.checked_at)}</span>}</div>{!docs.length ? <div className="empty-state"><BookOpen size={28}/><h2>Corpus chưa được công bố</h2><p>Tài liệu chỉ xuất hiện sau bước thu thập, kiểm tra chất lượng và công bố phiên bản.</p><button className="button button-secondary" onClick={() => void refresh()}>Kiểm tra lại</button></div> : <><div className="document-list">{filteredDocs.map(d => <DocumentRow key={d.id} document={d} onOpen={openSource}/>)}</div>{!filteredDocs.length && <div className="empty-state"><Search size={24}/><h2>Không tìm thấy văn bản</h2><p>Thử số hiệu hoặc từ khóa ngắn hơn.</p><button className="button button-secondary" onClick={() => setSearch('')}>Xóa từ khóa</button></div>}</>}</section>}
      {page === 'projects' && <section className="content-page"><h1>Vành đai 4</h1><p className="page-intro">Phạm vi dự án của bản MVP hiện chỉ hỗ trợ Vành đai 4. Thư viện vẫn lưu tài liệu của các dự án khác để tham khảo.</p>{activeProject ? <div className="project-dossier"><article className="project-overview"><div className="eyebrow"><MapPin size={20}/>HỒ SƠ DỰ ÁN · HÀ NỘI</div><h2>{activeProject.name}</h2><p>{activeProject.description}</p><small>{docs.filter(d => d.project === activeProject.id).length} nguồn đã công bố / {activeProject.source_ids.length} nguồn trong danh mục</small></article><aside className="warning-note"><ShieldCheck size={20}/><p>Thông tin tổng quan không xác định thửa đất bị thu hồi hoặc quyền lợi của từng hộ.</p></aside><div className="project-actions"><button className="button button-primary" onClick={() => { setProject(activeProject.id); setPage('chat'); setInput(activeProject.questions[0] || `Tôi cần kiểm tra hồ sơ pháp lý nào của ${activeProject.name}?`) }}>Hỏi về {activeProject.id === 'ring4' ? 'Vành đai 4' : activeProject.id === 'songhong' ? 'Sông Hồng' : 'Olympic'}</button><span>Câu hỏi sẽ sử dụng phạm vi dự án này.</span></div><h2 className="section-title">Nguồn để đối chiếu</h2><div className="document-list">{docs.filter(d => d.project === activeProject.id).map(d => <DocumentRow key={d.id} document={d} onOpen={openSource}/>)}</div>{!docs.some(d => d.project === activeProject.id) && <p className="secondary-copy">Chưa có nguồn đã công bố cho dự án này.</p>}</div> : <div className="empty-state"><MapPin size={28}/><h2>Chưa tải được hồ sơ dự án</h2><button className="button button-secondary" onClick={() => void refresh()}>Thử lại</button></div>}</section>}
      {page === 'evaluation' && <section className="content-page"><h1>Đánh giá hệ thống</h1><p className="page-intro">Báo cáo kỹ thuật cần gắn với đúng corpus, model và cấu hình đã chạy.</p>{evaluationWarning && <aside className="warning-note" role="status"><ShieldCheck size={20}/><p>{evaluationWarning}</p></aside>}<div className="evaluation-summary"><div><small>Corpus đang hoạt động</small><strong>{readiness?.corpus_release || 'Chưa công bố'}</strong></div><div><small>Phạm vi công bố</small><strong>Bản thử nghiệm</strong></div><div><small>Báo cáo khớp cấu hình</small><strong>{evaluation?.matches_active_configuration && evaluation?.matches_active_release ? 'Khớp phiên bản đang chạy' : 'Chưa có báo cáo khớp'}</strong></div></div>
        {!evaluation || evaluation.status === 'not_run' ? <div className="empty-state"><h2>Chưa có kết quả kiểm tra trên bản này</h2><p>Kết quả sẽ được công bố sau khi chạy và rà soát.</p></div> : <EvaluationTable evaluation={evaluation}/>}
      </section>}
    </main>
    {dataOpen && <DataPanel readiness={readiness} connecting={connecting} onRefresh={() => void refresh()} onClose={() => setDataOpen(false)}/>}
    {selectedSource && <SourcePanel source={selectedSource} onClose={() => setSelectedSource(null)}/>}
    {traceOpen && <TracePanel trace={trace} onClose={() => setTraceOpen(false)}/>}
  </div>
}
function EvaluationTable({ evaluation }: { evaluation: Record<string, unknown> }) {
  const rows = (evaluation.case_results || []) as {id:string;status:string;review:string;seconds:number;note:string;citations_valid?:boolean|null;answer_origin?:string}[]
  const counts = (evaluation.results || []) as {pass?:number;partial?:number;fail?:number}[]
  const metrics = evaluation.metrics as {groups?:Record<string,{cases:number;pass:number;partial:number;fail:number}>;answer_origin?:Record<string,number>;usage?:Record<string,{samples:number;median:number|null;p95:number|null}>} | undefined
  const supplemental = evaluation.supplemental as {cases:number;completed:number;pass:number;partial:number;fail:number;execution_failures:number;note:string} | undefined
  const limitations = Array.isArray(evaluation.limitations) ? evaluation.limitations.filter((item): item is string => typeof item === 'string') : []
  const groupLabels: Record<string,string> = {answered:'Trả lời nội dung',clarification:'Hỏi làm rõ',insufficient:'Thiếu chứng cứ / ngoài phạm vi',execution_failure:'Lỗi thực thi'}
  return <><p>Model: <strong>{String(evaluation.model || 'Chưa xác định')}</strong> · {String(evaluation.status)}</p>
    <p>{counts[0]?.pass ?? 0} đạt · {counts[0]?.partial ?? 0} một phần · {counts[0]?.fail ?? 0} chưa đạt. Đây là đánh giá kỹ thuật, chưa được thẩm định pháp lý độc lập. Tổng số đạt gồm cả hỏi lại và từ chối, không phải độ chính xác trả lời pháp luật.</p>
    {metrics?.groups && <div className="evaluation-table"><table><thead><tr><th>Nhóm hành vi</th><th>Số ca</th><th>Đạt</th><th>Một phần</th><th>Chưa đạt</th></tr></thead><tbody>{Object.entries(metrics.groups).map(([name,g])=><tr key={name}><td>{groupLabels[name] || name}</td><td>{g.cases}</td><td>{g.pass}</td><td>{g.partial}</td><td>{g.fail}</td></tr>)}</tbody></table></div>}
    {metrics?.answer_origin && <p>Luồng xử lý: {metrics.answer_origin.llm ?? 0} có bước sinh bằng LLM · {metrics.answer_origin.deterministic ?? 0} theo quy tắc · {metrics.answer_origin.unknown ?? 0} chưa xác định từ artifact.</p>}
    {metrics?.usage && <div className="evaluation-table"><table><thead><tr><th>Chỉ số</th><th>Số mẫu</th><th>Median</th><th>p95</th></tr></thead><tbody>{Object.entries(metrics.usage).map(([name,v])=><tr key={name}><td>{({elapsed_ms:'Thời gian (ms)',token_usage:'Token',llm_calls:'Lần gọi LLM',tool_calls:'Lần gọi công cụ'} as Record<string,string>)[name] || name}</td><td>{v.samples}</td><td>{v.median ?? '—'}</td><td>{v.p95 ?? '—'}</td></tr>)}</tbody></table><p>Thống kê một lượt chạy CLI; không phải cam kết tốc độ của dịch vụ.</p></div>}
    {supplemental && <aside className="warning-note"><ShieldCheck size={20}/><div><strong>Kiểm tra bổ sung</strong><p>{supplemental.completed}/{supplemental.cases} ca đã thực hiện · {supplemental.pass} đạt · {supplemental.partial} một phần · {supplemental.fail} chưa đạt · {supplemental.execution_failures} lỗi thực thi.</p><p>{supplemental.note}</p></div></aside>}
    {!!limitations.length && <ul className="secondary-copy">{limitations.map((text,index)=><li key={index}>{text}</li>)}</ul>}
    <div className="evaluation-table"><table><thead><tr><th>Ca</th><th>Kết quả</th><th>Giây</th><th>Nguồn trích dẫn</th><th>Nhận xét</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{r.id}</td><td>{({pass:'Đạt',partial:'Một phần',fail:'Chưa đạt'} as Record<string,string>)[r.review] || 'Chưa rà soát'}</td><td>{r.seconds.toFixed(1)}</td><td>{r.citations_valid == null ? 'Không áp dụng' : r.citations_valid ? 'Khớp corpus' : 'Không khớp'}</td><td>{r.note}</td></tr>)}</tbody></table></div>
  </>
}
export default App
