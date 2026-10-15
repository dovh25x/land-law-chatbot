import { useEffect, useState, type ReactNode } from 'react'
import { ArrowUpRight, Check, FileText, GitBranch, LoaderCircle, X } from 'lucide-react'
import { getJSON, type Citation, type LegalDocument, type Trace } from './api'

export const sourceKinds: Record<string, string> = {
  legal: 'Văn bản pháp luật', project_decision: 'Hồ sơ dự án', official_news: 'Thông tin chính thức',
}
export const formatDate = (value?: string) => value && !Number.isNaN(Date.parse(value))
  ? new Date(value).toLocaleDateString('vi-VN') : 'Chưa xác minh'

export function DocumentRow({ document, onOpen }: { document: LegalDocument; onOpen: (doc: LegalDocument) => void }) {
  return <button className="document-row" onClick={() => onOpen(document)}>
    <FileText size={24} className="document-symbol"/>
    <span className="document-copy"><small>{document.document_number || sourceKinds[document.source_kind]}</small>
      <strong>{document.title}</strong><span>{sourceKinds[document.source_kind]} · Kiểm tra {formatDate(document.checked_at)}</span>
    </span>
    {document.effective_to && <span className="document-history">Văn bản lịch sử</span>}
    <ArrowUpRight size={18}/>
  </button>
}

export function SidePanel({ title, icon, children, footer, onClose }: {
  title: string; icon: ReactNode; children: ReactNode; footer?: ReactNode; onClose: () => void,
}) {
  return <div className="panel-backdrop" onClick={onClose}>
    <section className="side-panel" role="dialog" aria-modal="true" aria-label={title} onClick={e => e.stopPropagation()}>
      <header className="panel-header"><div>{icon}<h2>{title}</h2></div><button className="icon-button" onClick={onClose} aria-label="Đóng"><X size={20}/></button></header>
      <div className="panel-body">{children}</div>
      {footer && <footer className="panel-footer">{footer}</footer>}
    </section>
  </div>
}

function ExternalSource({ url, children, primary = false }: { url?: string; children: ReactNode; primary?: boolean }) {
  if (!url || !/^https?:\/\//i.test(url)) return null
  return <a className={`button ${primary ? 'button-primary' : 'button-secondary'}`} href={url} target="_blank" rel="noopener noreferrer">{children}<ArrowUpRight size={18}/></a>
}

export function SourcePanel({ source, onClose }: { source: Citation | LegalDocument; onClose: () => void }) {
  const [document, setDocument] = useState<LegalDocument | null>(null)
  const [loading, setLoading] = useState(false), [error, setError] = useState('')
  const citation = 'excerpt' in source ? source : null
  useEffect(() => {
    setDocument(null); setError('')
    if ('excerpt' in source) { setLoading(false); return }
    const c = new AbortController(); setLoading(true)
    void getJSON<{ document: LegalDocument }>(`/api/v1/documents/${encodeURIComponent(source.id)}`, c.signal)
      .then(data => { if (!c.signal.aborted) setDocument(data.document) })
      .catch(() => { if (!c.signal.aborted) setError('Chưa tải được nội dung; bạn vẫn có thể mở nguồn chính thức bên dưới.') })
      .finally(() => { if (!c.signal.aborted) setLoading(false) })
    return () => c.abort()
  }, [source])
  return <SidePanel title="Chi tiết nguồn" icon={<FileText size={20}/>} onClose={onClose} footer={<>
    <ExternalSource url={source.url} primary>Mở nguồn chính thức</ExternalSource>
    {citation?.source_url && <ExternalSource url={citation.source_url}>Mở trang PDF gốc</ExternalSource>}
  </>}>
    <span className="badge">{citation ? 'CĂN CỨ TRONG LƯỢT HỎI' : sourceKinds[(source as LegalDocument).source_kind]}</span>
    <h3 className="source-title">{source.title}</h3>
    <p className="source-meta">{source.document_number}<br/>Snapshot nguồn: {formatDate(source.checked_at)}</p>
    {citation ? <>
      <div className="source-excerpt"><h4>{citation.locator}</h4><blockquote>{citation.excerpt}</blockquote></div>
      <p className="secondary-copy">Trạng thái căn cứ trong lượt hỏi: {citation.applicability}</p>
      {citation.page && <p className="secondary-copy">Trang nguồn: {citation.page}</p>}
    </> : <>
      <div className="source-dates"><p>Ngày bắt đầu hiệu lực<br/><strong>{formatDate((source as LegalDocument).effective_from)}</strong></p><p>Mốc kết thúc hiệu lực<br/><strong>{(source as LegalDocument).effective_to ? formatDate((source as LegalDocument).effective_to) : 'Chưa xác định mốc kết thúc'}</strong></p></div>
      {loading && <p className="secondary-copy" role="status"><LoaderCircle className="spin" size={16}/> Đang tải nội dung…</p>}
      {error && <p className="secondary-copy" role="status">{error}</p>}
      {document?.chunks?.slice(0, 3).map(chunk => <div className="source-excerpt" key={chunk.id}><h4>{chunk.locator}</h4><blockquote>{chunk.text}</blockquote></div>)}
      {!!document?.chunks?.length && <p className="secondary-copy">Hiển thị tối đa ba đoạn đầu. Mở nguồn chính thức để đọc đầy đủ.</p>}
    </>}
    {source.source_review_notes && <p className="secondary-copy">{source.source_review_notes}</p>}
    <p className="secondary-copy">Nguồn dẫn hỗ trợ đối chiếu. Việc áp dụng còn phụ thuộc thời điểm, dữ kiện và hồ sơ cụ thể.</p>
  </SidePanel>
}

export function TracePanel({ trace, onClose }: { trace: Trace[]; onClose: () => void }) {
  return <SidePanel title="Quá trình kiểm chứng" icon={<GitBranch size={20}/>} onClose={onClose} footer={<p className="panel-footnote">Sự kiện thực thi và nguồn thực tế từ API. Không hiển thị suy nghĩ nội bộ của mô hình.</p>}>
    <p className="secondary-copy">Các bước đã thực hiện và tài liệu được dùng trong lượt hỏi.</p>
    <ol className="trace-timeline">{trace.map((event, index) => <li key={index}>
      <span className="trace-step">{String(index + 1).padStart(2, '0')}</span>
      <div className="trace-copy"><strong>{event.tool || event.step}</strong><p>{event.summary}</p><small><Check size={12}/> {(event.elapsed_ms / 1000).toFixed(1)} giây</small>
        {!!event.document_ids?.length && <div className="trace-documents">{event.document_ids.map(id => <span key={id}>{id}</span>)}</div>}
      </div>
    </li>)}</ol>
    {!trace.length && <p className="secondary-copy">Chưa có sự kiện. Gửi một câu hỏi để bắt đầu.</p>}
  </SidePanel>
}

export function DataPanel({ readiness, connecting, onRefresh, onClose }: {
  readiness: import('./api').Readiness | null; connecting: boolean; onRefresh: () => void; onClose: () => void,
}) {
  const publicationLabel = 'Nguyên mẫu học thuật — chưa được thẩm định pháp lý độc lập.'
  return <SidePanel title="Dữ liệu và phạm vi sử dụng" icon={<FileText size={20}/>} onClose={onClose} footer={
    <button className="button button-secondary" onClick={onRefresh} disabled={connecting}>{connecting ? <><LoaderCircle size={16} className="spin"/>Đang kết nối…</> : 'Kiểm tra lại kết nối'}</button>
  }>
    <div className="data-status"><span className={readiness?.status === 'ready' ? 'status-dot ready' : 'status-dot'}/>{connecting ? 'Đang kết nối' : readiness?.status === 'ready' ? 'Sẵn sàng tra cứu' : 'Dịch vụ chưa sẵn sàng'}</div>
    <div className="data-note" role="note"><strong>{publicationLabel}</strong><p>Chỉ trả lời trong phạm vi nguồn đã kiểm tra. Quyền lợi cụ thể cần đối chiếu hồ sơ và cơ quan có thẩm quyền.</p></div>
    <div className="source-dates"><p>Dữ liệu kiểm tra<br/><strong>{formatDate(readiness?.checked_at)}</strong></p><p>Corpus đang hoạt động<br/><strong>{readiness?.corpus_release || 'Chưa công bố'}</strong></p></div>
    {!!readiness?.coverage_gaps?.length && <details className="data-gaps"><summary>Các nguồn chưa đủ dữ liệu ({readiness.coverage_gaps.length})</summary><ul>{readiness.coverage_gaps.map(g => <li key={g.document_id}><strong>{g.title}:</strong> {g.reason}</li>)}</ul></details>}
    <p className="secondary-copy">Phạm vi dự án hiện chỉ hỗ trợ Vành đai 4. Nguồn dự án khác trong thư viện chỉ để tham khảo. Chỉ nhập tình huống đã ẩn danh.</p>
  </SidePanel>
}
