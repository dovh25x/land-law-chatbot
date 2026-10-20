import ReactMarkdown from 'react-markdown'
import type { Result } from './api'
import { clarificationReply, validCitizenAnswer } from './citizen'
import { answerText, formatDate } from './ui'

export function CitizenAnswer({ result, busy, canReply, onChoose, onCitation }: {
  result: Result; busy: boolean; canReply: boolean; onChoose: (text: string) => void; onCitation: (id:string) => void,
}) {
  if (result.answer_schema_version !== 2) return <ReactMarkdown components={{ a: ({children}) => <span>{children}</span> }}>{answerText(result.content)}</ReactMarkdown>
  if (!validCitizenAnswer(result)) return <p role="alert">Chưa hiển thị được đáp án do dữ liệu không đúng định dạng. Bạn có thể chủ động gửi câu hỏi mới.</p>
  const sections = result.answer_sections!, claims = result.verified_claims!, clarification = result.clarification
  const labels = { direct: 'Điều bạn cần biết', explanation: 'Hiểu rõ hơn', actions: 'Việc có thể làm tiếp' }
  const markdown = (text:string) => <ReactMarkdown components={{ a: ({children}) => <span>{children}</span> }}>{text}</ReactMarkdown>
  return <>
    {claims.length ? <>
      {sections.map(section => <section className="citizen-section" key={section.kind} aria-label={labels[section.kind]}>
        {sections.length > 1 && <h3>{labels[section.kind]}</h3>}
        {section.claim_indexes.map(index => <div key={index}>{markdown(claims[index].text)}<span className="claim-citation-numbers">{claims[index].citation_ids.map(id => <button key={id} onClick={()=>onCitation(id)} aria-label={`Mở nguồn ${result.citations.findIndex(c=>c.id===id)+1} của nội dung`}>[{result.citations.findIndex(c=>c.id===id)+1}]</button>)}</span></div>)}
      </section>)}
      {clarification && <p className="clarification-question">{clarification.question}</p>}
      {result.answer_notices?.map((notice,index)=><p className="answer-notice" key={index}>{notice}</p>)}
      <p className="source-date-note">Thời điểm xem xét: {formatDate(result.as_of)}{result.source_context?.source_checked_at ? ` · Nguồn kiểm tra: ${formatDate(result.source_context.source_checked_at)}` : ''}</p>
    </> : markdown(result.content)}
    {clarification && canReply && <div className="clarification-choices" aria-label="Chọn thông tin để trả lời">
      {[...new Set([...clarification.options, ...(clarification.allow_unknown ? [clarification.fact === 'document_type' ? 'Tên khác / Tôi không rõ' : 'Tôi không biết'] : [])])].map(option => <button key={option} className="button button-secondary" disabled={busy}
        onClick={() => onChoose(clarificationReply(clarification.fact, option))}>{option}</button>)}
      <p className="secondary-copy">Chọn để điền vào ô nhập. Bạn có thể sửa trước khi gửi.</p>
    </div>}
  </>
}
