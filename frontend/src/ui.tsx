import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react'
import { ArrowUpRight, Clock, FileText, GitBranch, LoaderCircle, X } from 'lucide-react'
import { getJSON, type Citation, type GenerationStatus, type LegalDocument, type Trace } from './api'

export const sourceKinds: Record<string, string> = {
  legal: 'Văn bản pháp luật', project_decision: 'Hồ sơ dự án', official_news: 'Thông tin chính thức',
  official_procedure: 'Thủ tục chính thức', official_directory: 'Đầu mối công khai',
}
export const formatDate = (value?: string) => value && !Number.isNaN(Date.parse(value))
  ? new Date(value).toLocaleDateString('vi-VN') : 'Chưa xác minh'

export function useMedia(query: string) {
  const [matches, setMatches] = useState(() => matchMedia(query).matches)
  useEffect(() => {
    const media = matchMedia(query), update = () => setMatches(media.matches)
    update(); media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [query])
  return matches
}

/** Modal dialogs trap focus; the desktop comparison region deliberately does not. */
export function useDialog(ref: RefObject<HTMLElement | null>, active: boolean, modal: boolean, onClose: () => void) {
  const closeRef = useRef(onClose)
  const returnFocus = useRef<HTMLElement | null>(null), focusEpoch = useRef(0)
  closeRef.current = onClose
  useEffect(() => {
    if (!active) return
    const epoch = ++focusEpoch.current
    if (!returnFocus.current || !ref.current?.contains(document.activeElement)) returnFocus.current = document.activeElement as HTMLElement | null
    const controls = () => Array.from(ref.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input,select,textarea,[tabindex="0"]') || []).filter(element => element.getClientRects().length > 0);
    (ref.current?.querySelector<HTMLElement>('[aria-label="Đóng menu"], [aria-label="Đóng"]') || controls()[0])?.focus()
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); closeRef.current(); return }
      if (!modal || event.key !== 'Tab') return
      const elements = controls(), first = elements[0], last = elements.at(-1)
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    document.addEventListener('keydown', keydown)
    return () => {
      document.removeEventListener('keydown', keydown)
      queueMicrotask(() => {
        if (focusEpoch.current !== epoch) return
        const previous = returnFocus.current
        returnFocus.current = null
        if (previous?.isConnected && !document.activeElement?.closest('[role="dialog"]')) previous.focus({ preventScroll: true })
      })
    }
  }, [active, modal, ref])
}

export function DocumentRow({ document, onOpen }: { document: LegalDocument; onOpen: (doc: LegalDocument) => void }) {
  return <button className="document-row" onClick={() => onOpen(document)}>
    <FileText size={22} className="document-symbol"/>
    <span className="document-copy"><strong>{document.title}</strong>
      <span>{document.document_number || 'Chưa có số hiệu'} · {sourceKinds[document.source_kind] || 'Nguồn khác'}</span>
      {document.availability === 'reference_only' && <small>Bản gốc tham khảo · Chưa dùng cho câu trả lời AI</small>}
      <small>Kiểm tra {formatDate(document.checked_at)}{document.effective_from ? ` · Hiệu lực từ ${formatDate(document.effective_from)}` : ''}{document.effective_to ? ` · Mốc kết thúc ${formatDate(document.effective_to)}` : ''}</small>
    </span><ArrowUpRight size={18}/>
  </button>
}

export function SidePanel({ title, icon, children, footer, onClose, comparison = false }: {
  title: string; icon: ReactNode; children: ReactNode; footer?: ReactNode; onClose: () => void; comparison?: boolean,
}) {
  const desktop = useMedia('(min-width: 1280px)'), ref = useRef<HTMLElement>(null)
  const modal = !(comparison && desktop)
  useDialog(ref, true, modal, onClose)
  return <div className={`panel-backdrop ${modal ? 'modal-panel' : 'comparison-panel'}`} onClick={modal ? onClose : undefined}>
    <section ref={ref} className="side-panel" role={modal ? 'dialog' : 'complementary'} aria-modal={modal || undefined} aria-label={title} onClick={e => e.stopPropagation()}>
      <header className="panel-header"><div>{icon}<h2>{title}</h2></div><button className="icon-button" onClick={onClose} aria-label="Đóng"><X size={20}/></button></header>
      <div className="panel-body">{children}</div>
      {footer && <footer className="panel-footer">{footer}</footer>}
    </section>
  </div>
}

export function ConfirmDialog({ title, onCancel, onConfirm, busy }: { title: string; onCancel: () => void; onConfirm: () => void; busy: boolean }) {
  const ref = useRef<HTMLElement>(null)
  useDialog(ref, true, true, () => { if (!busy) onCancel() })
  return <div className="confirm-backdrop"><section ref={ref} role="dialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-description" className="confirm-dialog">
    <h2 id="confirm-title">{title}</h2><p id="confirm-description">Dữ liệu sẽ bị xóa khỏi thiết bị này. Xóa lịch sử không đặt lại quota phiên API.</p>
    <div className="confirm-actions"><button className="button button-secondary" onClick={onCancel} disabled={busy}>Hủy</button><button className="button button-danger" onClick={onConfirm} disabled={busy}>{busy ? 'Đang xóa…' : 'Xóa lịch sử'}</button></div>
  </section></div>
}

function ExternalSource({ url, children, primary = false }: { url?: string; children: ReactNode; primary?: boolean }) {
  if (!url || !/^https?:\/\//i.test(url)) return null
  return <a className={`button ${primary ? 'button-primary' : 'button-secondary'}`} href={url} target="_blank" rel="noopener noreferrer">{children}<ArrowUpRight size={18}/></a>
}

const applicability: Record<string, string> = {
  current: 'Đang áp dụng theo kiểm tra của lượt hỏi', historical: 'Căn cứ lịch sử',
  future: 'Căn cứ có hiệu lực trong tương lai', unverified: 'Chưa xác minh trạng thái áp dụng',
  context: 'Nguồn cung cấp bối cảnh', provision_specific: 'Áp dụng theo điều khoản cụ thể',
  expired: 'Đã hết hiệu lực theo kiểm tra của lượt hỏi', unknown: 'Chưa xác định trạng thái áp dụng',
}

export function SourcePanel({ source, citations, onSelect, onClose }: {
  source: Citation | LegalDocument | null; citations: Citation[]; onSelect: (citation: Citation) => void; onClose: () => void,
}) {
  const [document, setDocument] = useState<LegalDocument | null>(null)
  const [loading, setLoading] = useState(false), [error, setError] = useState('')
  const citation = source && 'excerpt' in source ? source : null
  const files = [...new Set([...(document?.attachment_urls || []), ...(document?.source_files || []).map(item => item.url), ...(source && 'attachment_urls' in source ? source.attachment_urls || [] : [])])]
  const scrollRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    setDocument(null); setError(''); scrollRef.current?.closest('.panel-body')?.scrollTo(0, 0)
    if (!source || 'excerpt' in source) { setLoading(false); return }
    const controller = new AbortController(); setLoading(true)
    void getJSON<{ document: LegalDocument }>(`/api/v1/documents/${encodeURIComponent(source.id)}`, controller.signal)
      .then(data => { if (!controller.signal.aborted) setDocument(data.document) })
      .catch(() => { if (!controller.signal.aborted) setError('Chưa tải được nội dung; bạn vẫn có thể mở nguồn chính thức bên dưới.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [source])
  return <SidePanel title="Nguồn căn cứ" comparison icon={<FileText size={20}/>} onClose={onClose} footer={source && <>
    <ExternalSource url={source.url} primary>Mở nguồn chính thức</ExternalSource>
    {citation?.source_url && <ExternalSource url={citation.source_url}>Mở trang nguồn gốc</ExternalSource>}
    {!citation && files.slice(0, 8).map((url, index) => <ExternalSource key={url} url={url}>Mở bản gốc {index + 1}</ExternalSource>)}
  </>}>
    {!!citations.length && <nav className="source-picker" aria-label="Nguồn của đáp án"><h3>{citations.length} nguồn trong đáp án</h3>{citations.map((item, index) => <button key={item.id} aria-current={source?.id === item.id ? 'true' : undefined} onClick={() => onSelect(item)}><span className="citation-index">{index + 1}</span><span>{item.document_number || item.title}<small>{item.locator}</small></span></button>)}</nav>}
    {source ? <div ref={scrollRef} className="source-card">
      <h3 className="source-title">{source.title}</h3><p className="source-meta">{source.document_number || 'Chưa có số hiệu'}</p>
      {source.source_kind && <p className="secondary-copy">{sourceKinds[source.source_kind] || 'Nguồn để đối chiếu'}</p>}
      {(document?.availability === 'reference_only' || ('availability' in source && source.availability === 'reference_only')) && <p className="data-note" role="note">Tài liệu gốc để bạn đối chiếu. Nội dung chưa nằm trong chỉ mục trả lời và không được dùng làm căn cứ cho kết luận AI.</p>}
      {citation ? <>
        <div className="source-excerpt"><h4>{citation.locator}</h4>{citation.page && <p className="secondary-copy">Trang nguồn: {citation.page}</p>}<blockquote>{citation.excerpt}</blockquote></div>
        <p className="source-applicability">{applicability[citation.applicability] || 'Chưa xác định trạng thái áp dụng'}</p>
      </> : <>
        <div className="source-dates"><p>Ngày bắt đầu hiệu lực<br/><strong>{formatDate((source as LegalDocument).effective_from)}</strong></p><p>Mốc kết thúc hiệu lực<br/><strong>{(source as LegalDocument).effective_to ? formatDate((source as LegalDocument).effective_to) : 'Chưa xác định mốc kết thúc'}</strong></p></div>
        {loading && <p role="status"><LoaderCircle className="spin" size={16}/> Đang tải nội dung…</p>}
        {error && <p role="status">{error}</p>}
        {document?.chunks?.slice(0, 3).map(chunk => <div className="source-excerpt" key={chunk.id}><h4>{chunk.locator}</h4><blockquote>{chunk.text}</blockquote></div>)}
        {!!document?.chunks?.length && <p className="secondary-copy">Hiển thị tối đa ba đoạn đầu. Mở nguồn chính thức để đọc đầy đủ.</p>}
      </>}
      <details className="source-technical"><summary>Thông tin phiên bản nguồn</summary><p>Ngày kiểm tra: {formatDate(source.checked_at)}</p><p>Checksum: {source.checksum || 'Chưa có metadata trong lượt hỏi'}</p></details>
      {source.source_review_notes && <p className="secondary-copy">{source.source_review_notes}</p>}
      <p className="secondary-copy">Nguồn dẫn hỗ trợ đối chiếu. Việc áp dụng còn phụ thuộc thời điểm, dữ kiện và hồ sơ cụ thể.</p>
    </div> : <p className="secondary-copy">Chọn một nguồn để đọc đoạn căn cứ và mở văn bản chính thức.</p>}
  </SidePanel>
}

const traceLabels: Record<string, string> = { route: 'Xác định phạm vi', plan: 'Chuẩn bị tra cứu', retrieve: 'Tra cứu nguồn', retrieval: 'Tra cứu nguồn', verify: 'Kiểm tra căn cứ', repair: 'Rà soát lại đáp án', generate: 'Soạn đáp án', answer: 'Hoàn tất đáp án' }
export function TracePanel({ trace, onClose }: { trace: Trace[]; onClose: () => void }) {
  return <SidePanel title="Quá trình kiểm chứng" icon={<GitBranch size={20}/>} onClose={onClose} footer={<p className="panel-footnote">Sự kiện thực thi và nguồn thực tế từ API. Không hiển thị suy nghĩ nội bộ của mô hình.</p>}>
    <p className="secondary-copy">Các sự kiện quan sát được trong lượt hỏi.</p>
    <ol className="trace-timeline">{trace.map((event, index) => <li key={index}>
      <span className="trace-step">{String(index + 1).padStart(2, '0')}</span>
      <div className="trace-copy"><strong>{traceLabels[event.step] || 'Sự kiện thực thi'}</strong><p>{event.summary}</p><small><Clock size={14}/> {(event.elapsed_ms / 1000).toFixed(1)} giây</small>
        <details><summary>Chi tiết công cụ và nguồn</summary><p>{event.tool || event.step}</p>{event.document_ids?.map(id => <p key={id}>{id}</p>)}</details>
      </div>
    </li>)}</ol>
    {!trace.length && <p className="secondary-copy">Chưa có sự kiện. Gửi một câu hỏi để bắt đầu.</p>}
  </SidePanel>
}

/** Hide the former automatic preamble in answers already saved on this device. */
export function answerText(content: string) {
  const legacyNotice = 'Nguồn chưa được rà soát cập nhật; nội dung tham khảo từ snapshot, chưa xác nhận quy định hiện hành. '
  return content.startsWith(legacyNotice) ? content.slice(legacyNotice.length) : content
}

export function generationLabel(status: GenerationStatus | null) {
  if (!status) return 'Chưa xác định khả năng trả lời'
  if (status.generation_available) return 'Có thể sinh đáp án'
  if (!status.reason) return 'Chưa thể sinh đáp án; chưa xác định nguyên nhân'
  return ({ disabled: 'Trả lời bằng AI đang tạm dừng', source_stale: 'Nguồn cần rà soát; tạm dừng sinh đáp án', provider_limited: 'Nhà cung cấp AI đang giới hạn' })[status.reason] || 'Chưa thể sinh đáp án; chưa xác định nguyên nhân'
}
export function DataPanel({ readiness, generation, connecting, onRefresh, onClose }: {
  readiness: import('./api').Readiness | null; generation: GenerationStatus | null; connecting: boolean; onRefresh: () => void; onClose: () => void,
}) {
  return <SidePanel title="Dữ liệu và phạm vi sử dụng" icon={<FileText size={20}/>} onClose={onClose} footer={
    <button className="button button-secondary" onClick={onRefresh} disabled={connecting}>{connecting ? <><LoaderCircle size={16} className="spin"/>Đang kết nối…</> : 'Kiểm tra lại kết nối'}</button>
  }>
    <div className="data-status"><span className={readiness?.status === 'ready' ? 'status-dot ready' : 'status-dot'}/>{connecting ? 'Đang kết nối' : readiness?.database || readiness?.status === 'ready' ? 'Đã kết nối dịch vụ' : 'Dịch vụ chưa sẵn sàng'}</div>
    <p>{generationLabel(generation)}{generation?.retry_after ? ` · Thử lại sau ${generation.retry_after} giây.` : ''}</p>
    <div className="data-note" role="note"><strong>Bản thử nghiệm — chưa được thẩm định pháp lý độc lập.</strong><p>Chỉ trả lời trong phạm vi nguồn đã kiểm tra. Quyền lợi cụ thể cần đối chiếu hồ sơ và cơ quan có thẩm quyền.</p></div>
    <div className="source-dates"><p>Dữ liệu kiểm tra<br/><strong>{formatDate(readiness?.checked_at)}</strong></p><p>Corpus đang hoạt động<br/><strong>{readiness?.corpus_release || 'Chưa công bố'}</strong></p></div>
    {!!readiness?.coverage_gaps?.length && <details><summary>Các nguồn chưa đủ dữ liệu ({readiness.coverage_gaps.length})</summary><ul>{readiness.coverage_gaps.map(g => <li key={g.document_id}><strong>{g.title}:</strong> {g.reason}</li>)}</ul></details>}
    <p className="secondary-copy">Phạm vi dự án hiện chỉ hỗ trợ Vành đai 4. Chỉ nhập tình huống đã ẩn danh.</p>
  </SidePanel>
}
