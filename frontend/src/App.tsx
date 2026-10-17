import { listConversations, saveConversation, deleteConversation, clearConversations, type Conversation, newConversation as makeConversation } from './history'
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { BookOpen, ChevronRight, CircleHelp, LoaderCircle, Menu, Plus, Search, ShieldCheck, Square, X } from 'lucide-react'
import { ask, BASE, BACKEND_CONFIGURED, getJSON, getSession, type Citation, type LegalDocument, type Readiness, type Result, type Session, type Trace } from './api'
import { DataPanel, DocumentRow, formatDate, SourcePanel, TracePanel } from './ui'
import { Turnstile } from './Turnstile'

type Page = 'chat' | 'sources' | 'evaluation'
type Message = { id: string; role: 'user' | 'assistant'; content: string; result?: Result }
const suggestions = [
  'Chi phí di chuyển tài sản được quy định thế nào?',
  'Khi nào được hỗ trợ ổn định đời sống?',
  'Cần hồ sơ gì để đối chiếu điều kiện tái định cư?',
]

const pageLabels: Record<Page, string> = { chat: 'Hỏi đáp pháp luật', sources: 'Thư viện văn bản', evaluation: 'Đánh giá hệ thống' }

const labels: Record<string, string> = { answered: 'Có căn cứ', clarification_needed: 'Cần bổ sung thông tin', insufficient_evidence: 'Chưa đủ căn cứ', limited: 'Giới hạn lượt dùng', error: 'Chưa xử lý được' }

function App() {
  const [page, setPage] = useState<Page>('chat')
  const [navOpen, setNavOpen] = useState(false)
  const [copiedId, setCopiedId] = useState<string>()
  async function copyAnswer(id: string, content: string) {
    try { await navigator.clipboard.writeText(content); setCopiedId(id) }
    catch { setError('Không sao chép được. Bạn có thể chọn nội dung để sao chép thủ công.') }
  }
  const conversationRef=useRef(makeConversation())
  const [conversations,setConversations]=useState<Conversation[]>([])
  const [theme,setTheme]=useState(()=>localStorage.getItem('landlaw-theme') || (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'))
  const [challenge,setChallenge]=useState<string>()
  useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('landlaw-theme',theme)},[theme])
  const [dataOpen, setDataOpen] = useState(false)
  const [input, setInput] = useState(''), [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [readiness, setReadiness] = useState<Readiness | null>(null), [connecting, setConnecting] = useState(false)
  const [docs, setDocs] = useState<LegalDocument[]>([])
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
      const [sourceData, evalData] = await Promise.allSettled([
        getJSON<{ documents: LegalDocument[] }>('/api/v1/documents', signal),
        getJSON<Record<string, unknown>>('/api/v1/evaluations/latest', signal),
      ])
      if (sourceData.status === 'fulfilled') setDocs(sourceData.value.documents)
      if (evalData.status === 'fulfilled') setEvaluation(evalData.value)
    } catch { setReadiness({ status: 'starting' }) }
    finally { setConnecting(false) }
  }
  useEffect(() => { const c = new AbortController(); void refresh(c.signal); return () => c.abort() }, [])
  useEffect(() => {
    let alive=true
    const restore=async()=>{try{
      const saved=await listConversations()
      if(alive)setConversations(saved)
      if(alive&&saved.length){conversationRef.current=saved[0];setMessages(saved[0].messages)}
    }catch{if(alive)setError('Không đọc được lịch sử tại máy; hội thoại chỉ tồn tại trong tab này.')}}
    void restore()
    const timer=window.setInterval(()=>{void listConversations().then(saved=>{if(!alive)return;setConversations(saved);if(conversationRef.current.expires_at<=Date.now()){conversationRef.current=makeConversation();setMessages([]);setTrace([])}}).catch(()=>setError('Không dọn được lịch sử hết hạn tại máy.'))},60000)
    return()=>{alive=false;clearInterval(timer)}
  }, [])
  useEffect(()=>{
    if(!messages.length)return
    const current=conversationRef.current
    void saveConversation({...current,messages,title:messages[0].content.slice(0,80),updated_at:Date.now()}).then(()=>listConversations()).then(setConversations)
      .catch(()=>setError('Không lưu được lịch sử tại máy. Server không giữ bản sao; bạn có thể tiếp tục trong tab.'))
  },[messages])
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
    if(import.meta.env.VITE_TURNSTILE_SITE_KEY&&!sessionStorage.getItem('landlaw-session')&&!challenge){setError('Vui lòng hoàn tất xác minh trình duyệt trước khi gửi.');return}
    const question = text.trim()
    setPage('chat'); setNavOpen(false); setInput(''); setError(''); setBusy(true); setTrace([])
    setMessages(m => [...m, { id: crypto.randomUUID(), role: 'user', content: question }])
    const controller = new AbortController(); abortRef.current = controller
    const timeout = window.setTimeout(() => controller.abort(), 180000)
    let received = false
    try {
      sessionRef.current ||= await getSession(challenge)
      await ask(sessionRef.current, question, 'ring4', '', controller.signal, (event, data) => {
        if (event === 'progress') setTrace(t => [...t, data as Trace])
        if (event === 'result') {
          received = true
          const result = data as Result
          setMessages(m => [...m, { id: result.trace_id, role: 'assistant', content: result.content, result }])
          setTrace(result.trace)
        }
        if (event === 'failure') { received = true; setError((data as { content: string }).content) }
      },messages)
      if (!received) throw new Error('Mất kết nối trước khi nhận kết quả. Server không lưu đáp án để khôi phục. Bạn có thể chủ động gửi câu hỏi mới.')
    } catch (e) { setError(e instanceof Error && e.name !== 'AbortError' ? e.message : 'Lượt hỏi đã dừng hoặc quá thời gian chờ.') }
    finally { window.clearTimeout(timeout); setBusy(false); abortRef.current = null }
  }

  function newConversation() {
    abortRef.current?.abort(); conversationRef.current=makeConversation()
    setMessages([]); setTrace([]); setError(''); setPage('chat'); setNavOpen(false)
  }

  const ready = readiness?.status === 'ready'
  const panelOpen = traceOpen || !!selectedSource || dataOpen
  const filteredDocs = docs.filter(d => `${d.title} ${d.document_number || ''}`.normalize('NFC').toLocaleLowerCase('vi').includes(search.normalize('NFC').toLocaleLowerCase('vi')))
  const evaluationWarning = evaluation && evaluation.status !== 'not_run' &&
    (!evaluation.matches_active_release || !evaluation.matches_active_configuration || evaluation.status !== 'reviewed')
    ? 'Chưa hoàn tất đánh giá trên cấu hình đang hoạt động. Không diễn giải kết quả của phiên bản khác thành chất lượng bản hiện tại.' : ''
  const openSource = (source: Citation | LegalDocument) => { setDataOpen(false); setTraceOpen(false); setSelectedSource({...source,checksum:source.checksum || docs.find(d=>d.id===('document_id' in source?source.document_id:source.id))?.checksum}) }
  const navigate = (target: Page) => { setDataOpen(false); setPage(target); setNavOpen(false); setTraceOpen(false); setSelectedSource(null) }


  return <div className={`app-shell page-${page} ${panelOpen ? 'panel-open' : ''} ${navOpen ? 'nav-open' : ''}`}>
    <a className="skip-link" href="#main-content">Đến nội dung chính</a>
    {navOpen && <button className="nav-scrim" tabIndex={-1} onClick={() => setNavOpen(false)} aria-label="Đóng menu điều hướng"/>}
    <aside className="sidebar" id="main-navigation" role={navOpen ? 'dialog' : undefined} aria-modal={navOpen || undefined} aria-label={navOpen ? 'Menu điều hướng' : undefined}>
      <button className="icon-button mobile-nav-close" onClick={() => setNavOpen(false)} aria-label="Đóng menu"><X size={20}/></button>
      <a className="brand" href="#" onClick={e => { e.preventDefault(); navigate('chat') }}><span>Vành đai 4</span></a>
      <button className="button button-primary new-chat" onClick={newConversation} disabled={busy}>Cuộc trò chuyện mới</button>
      <div className="nav-label">LỊCH SỬ TRÊN THIẾT BỊ</div>
      <div className="history-list">{conversations.map(c=><div className={`history-row ${conversationRef.current.id===c.id?'active':''}`} key={c.id}>
        <button disabled={busy} onClick={()=>{conversationRef.current=c;setMessages(c.messages);setPage('chat');setNavOpen(false);setError('')}}>{c.title}</button>
        <button disabled={busy} aria-label={`Xóa cuộc trò chuyện ${c.title}`} onClick={()=>{if(!confirm('Xóa cuộc trò chuyện khỏi thiết bị này?'))return;void deleteConversation(c.id).then(()=>listConversations()).then(setConversations).then(()=>{if(conversationRef.current.id===c.id)newConversation()}).catch(()=>setError('Không xóa được lịch sử tại máy.'))}}><X size={14}/></button>
      </div>)}{!conversations.length&&<p className="secondary-copy">Chưa có cuộc trò chuyện.</p>}</div>
      <nav aria-label="Điều hướng chính">{(Object.entries(pageLabels) as [Page, string][]).map(([id, label]) => <button key={id} aria-current={page === id ? 'page' : undefined} className={page === id ? 'active' : ''} onClick={() => navigate(id)}>{label}</button>)}</nav>
      <div className="sidebar-note"><p>Lưu tại máy trong 7 ngày.<br/>Không đồng bộ giữa thiết bị.</p>
      <button className="mobile-data-link" onClick={()=>{setNavOpen(false);setDataOpen(true)}} aria-label="Thông tin dữ liệu và kết nối">Dữ liệu và kết nối</button>
      <button onClick={()=>setTheme(theme==='dark'?'light':'dark')} aria-label="Đổi giao diện sáng tối">{theme==='dark'?'Giao diện sáng':'Giao diện tối'}</button>
      <button disabled={busy} onClick={()=>{if(!confirm('Xóa toàn bộ lịch sử trên thiết bị này?'))return;void clearConversations().then(()=>{setConversations([]);newConversation()}).catch(()=>setError('Không xóa được lịch sử tại máy.'))}}>Xóa toàn bộ lịch sử</button></div>
    </aside>
    <main className="main" id="main-content" inert={navOpen}>
      <header className="topbar"><div className="topbar-title"><button className="icon-button mobile-menu" ref={navTriggerRef} onClick={() => setNavOpen(true)} aria-label="Mở menu điều hướng" aria-expanded={navOpen} aria-controls="main-navigation"><Menu size={20}/></button><div><span className="desktop-chat-title">{page === 'chat' ? 'Vành đai 4 / Trợ lý pháp lý' : pageLabels[page]}</span><span className="mobile-chat-title">{page === 'chat' ? 'Vành đai 4' : pageLabels[page]}</span>{page === 'chat' && <p className="topbar-subtitle">Bản thử nghiệm · Nguồn pháp luật có dẫn chứng</p>}</div></div><div className="topbar-actions"><button className="icon-button data-trigger" onClick={() => { setSelectedSource(null); setTraceOpen(false); setDataOpen(true) }} aria-label="Thông tin dữ liệu và kết nối" title="Thông tin dữ liệu và kết nối"><CircleHelp size={20}/><span className={ready ? 'status-dot ready' : 'status-dot'}/></button><button className="icon-button mobile-new-chat" onClick={newConversation} disabled={busy} aria-label="Cuộc trò chuyện mới"><Plus size={20}/></button></div></header>
      {page === 'chat' && <>
        <div className={`chat-workspace ${panelOpen ? 'has-panel' : ''} ${messages.length ? 'has-messages' : 'is-empty'}`}>
          <div className="chat-scroll">
            {!messages.length ? <div className="welcome"><h1>Bạn muốn tìm hiểu điều gì?</h1><p className="intro">Tra cứu bồi thường, hỗ trợ và tái định cư cho Vành đai 4 tại Hà Nội.</p><div className="topic-grid"><h2>Gợi ý cho bạn</h2>{suggestions.map((question,index) => <button key={question} onClick={() => void send(question)} disabled={busy}><span className="suggestion-number">{index+1}</span><span>{question}</span></button>)}</div></div>
            : <div className="messages">{messages.map(message => <article key={message.id} className={`message ${message.role}`}>
              <div className="message-label">{message.role === 'user' ? 'Bạn' : <>Vành đai 4</>}</div>
              {message.result && message.result.status !== 'answered' && <span className={`answer-status ${message.result.status}`}>{labels[message.result.status] || message.result.status}</span>}
              <div className="message-body"><ReactMarkdown components={{ a: ({ children }) => <span>{children}</span> }}>{message.content}</ReactMarkdown></div>
              {!!message.result?.citations?.length && <div className="citations">{message.result.citations.map((c, index) => <button key={c.id} onClick={() => openSource(c)} aria-label={`[${index+1}] ${c.title} ${c.document_number || ''} · ${c.locator}`}><span className="citation-heading"><strong>[{index + 1}] {c.title} · {c.locator}</strong></span></button>)}</div>}
              {message.result && <div className="answer-actions">
                {!!message.result.citations?.length && <button onClick={() => openSource(message.result!.citations[0])}>Xem nguồn</button>}
                <button className="trace-link" aria-label="Xem quá trình kiểm chứng" onClick={() => { setSelectedSource(null); setTrace(message.result!.trace || []); setTraceOpen(true) }}>Chi tiết thực thi</button>
                <button onClick={() => void copyAnswer(message.id,message.content)}>{copiedId===message.id?'Đã sao chép':'Sao chép'}</button>
              </div>}

            </article>)}{busy && <div className="working" role="status"><span className="notice-icon"><img src="/figma/search.svg" alt=""/></span><span>{trace.at(-1)?.summary || 'Đang kết nối và chuẩn bị tra cứu…'}</span><button onClick={() => { setSelectedSource(null); setTraceOpen(true) }}>Xem quá trình</button></div>}<div ref={bottom}/></div>}
          </div>
          <div className="composer-area">{error && <div className="error-banner" role="alert"><span className="notice-icon"><img src="/figma/alert-circle.svg" alt=""/></span><div><strong>Chưa thể hoàn tất lượt hỏi</strong><p>{error}</p></div><button className="icon-button" onClick={() => setError('')} aria-label="Đóng thông báo"><X size={18}/></button></div>}
            {!ready && <div className="connection-note" role="status"><span className="notice-icon"><img src="/figma/clock.svg" alt=""/></span><p>{connecting ? 'Đang kết nối backend. Lần khởi động đầu có thể mất khoảng một phút…' : readiness?.status === 'not_deployed' ? 'Bản xem trước giao diện. Backend chưa được triển khai.' : readiness?.database && !readiness.llm_configured ? 'Chưa cấu hình API AI; hệ thống sẽ báo rõ giới hạn khi gửi câu hỏi.' : readiness?.database && !readiness.corpus_release ? 'Bộ dữ liệu đang chờ công bố.' : 'Backend có thể đang khởi động. Bạn có thể thử kết nối lại.'}</p></div>}
            <Turnstile onToken={setChallenge}/><div className="composer"><form id="chat-form" className="composer-input" onSubmit={e => { e.preventDefault(); void send() }}><textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)} placeholder="Hỏi về bồi thường, hỗ trợ, tái định cư…" maxLength={4000} rows={1} aria-label="Câu hỏi pháp luật" onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send() } }}/></form><div className="composer-bottom"><span className="composer-hint">Enter để gửi · Shift + Enter xuống dòng</span>{busy ? <button type="button" className="send-button" onClick={() => abortRef.current?.abort()} aria-label="Dừng lượt hỏi"><Square size={18}/></button> : <button className="send-button" type="submit" form="chat-form" disabled={!input.trim()} aria-label="Gửi câu hỏi"><span className="desktop-send-arrow" aria-hidden="true">↑</span><img className="mobile-send-arrow" src="/figma/arrow-up.svg" alt=""/></button>}</div></div><p className="disclaimer">{messages.length ? 'Có thể có sai sót. Hãy kiểm tra nguồn trước khi áp dụng.' : 'Bản thử nghiệm · Chỉ nhập tình huống đã ẩn danh.'}</p>
          </div>
        </div>
      </>}
      {page === 'sources' && <section className="content-page"><h1>Thư viện văn bản</h1><p className="page-intro">Tìm văn bản và mở nguồn gốc để kiểm tra căn cứ.</p><label className="searchbox"><Search size={20}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Tìm theo số hiệu hoặc tên văn bản…" aria-label="Tìm văn bản"/></label><div className="library-count"><strong>{docs.length} tài liệu đã công bố</strong>{readiness?.checked_at && <span>Nguồn kiểm tra: {formatDate(readiness.checked_at)}</span>}</div>{!docs.length ? <div className="empty-state"><BookOpen size={28}/><h2>Corpus chưa được công bố</h2><p>Tài liệu chỉ xuất hiện sau bước thu thập, kiểm tra chất lượng và công bố phiên bản.</p><button className="button button-secondary" onClick={() => void refresh()}>Kiểm tra lại</button></div> : <><div className="document-list">{filteredDocs.map(d => <DocumentRow key={d.id} document={d} onOpen={openSource}/>)}</div>{!filteredDocs.length && <div className="empty-state"><Search size={24}/><h2>Không tìm thấy văn bản</h2><p>Thử số hiệu hoặc từ khóa ngắn hơn.</p><button className="button button-secondary" onClick={() => setSearch('')}>Xóa từ khóa</button></div>}</>}</section>}
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
    {metrics?.usage && <div className="evaluation-table"><table><thead><tr><th>Chỉ số</th><th>Số mẫu</th><th>Median</th><th>p95</th></tr></thead><tbody>{Object.entries(metrics.usage).map(([name,v])=><tr key={name}><td>{({elapsed_ms:'Thời gian (ms)',token_usage:'Token',llm_calls:'Lần gọi LLM',tool_calls:'Lần gọi công cụ'} as Record<string,string>)[name] || name}</td><td>{v.samples}</td><td>{v.median ?? '—'}</td><td>{v.p95 ?? '—'}</td></tr>)}</tbody></table><p>Thống kê một lượt chạy CLI; không phải cam kết tốc độ của dịch vụ.</p></div>}
    {supplemental && <aside className="warning-note"><ShieldCheck size={20}/><div><strong>Kiểm tra bổ sung</strong><p>{supplemental.completed}/{supplemental.cases} ca đã thực hiện · {supplemental.pass} đạt · {supplemental.partial} một phần · {supplemental.fail} chưa đạt · {supplemental.execution_failures} lỗi thực thi.</p><p>{supplemental.note}</p></div></aside>}
    {!!limitations.length && <ul className="secondary-copy">{limitations.map((text,index)=><li key={index}>{text}</li>)}</ul>}
    <div className="evaluation-table"><table><thead><tr><th>Ca</th><th>Kết quả</th><th>Giây</th><th>Nguồn trích dẫn</th><th>Nhận xét</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{r.id}</td><td>{({pass:'Đạt',partial:'Một phần',fail:'Chưa đạt'} as Record<string,string>)[r.review] || 'Chưa rà soát'}</td><td>{r.seconds.toFixed(1)}</td><td>{r.citations_valid == null ? 'Không áp dụng' : r.citations_valid ? 'Khớp corpus' : 'Không khớp'}</td><td>{r.note}</td></tr>)}</tbody></table></div>
  </>
}
export default App
