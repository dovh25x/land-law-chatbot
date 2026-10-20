import type { Result } from './api'

export const citizenSuggestions = [
  'Tôi vừa nhận giấy về Vành đai 4, cần bắt đầu từ đâu?',
  'Tôi cần chuẩn bị giấy tờ gì để tìm hiểu phương án?',
  'Tôi muốn tìm nơi hỏi về hồ sơ Vành đai 4.',
  'Tôi chưa đồng ý phương án, nên tìm hiểu bước nào?',
  'Tôi muốn hiểu điều kiện hỗ trợ và chỗ ở mới.',
  'Tôi chưa rõ mình đang ở bước nào.',
]

/** A malformed v2 projection must never cause unchecked content to be shown. */
export function validCitizenAnswer(result: Result): boolean {
  if (result.answer_schema_version !== 2) return false
  const claims = result.verified_claims, sections = result.answer_sections
  if (!Array.isArray(claims) || !Array.isArray(sections) || claims.length > 10 || sections.length > 3) return false
  if (result.status === 'answered' && !claims.length) return false
  if (!Array.isArray(result.citations)) return false
  if (result.citations.some(c => !c || typeof c.id !== 'string' || !c.id)) return false
  const citations = new Set(result.citations.map(c => c.id))
  if (citations.size !== result.citations.length) return false
  if (result.answer_notices !== undefined && (!Array.isArray(result.answer_notices)
    || result.answer_notices.length > 5 || result.answer_notices.some(n => typeof n !== 'string'))) return false
  if (claims.some(c => !c || typeof c.text !== 'string' || !c.text.trim() || !Array.isArray(c.citation_ids)
    || !c.citation_ids.length || c.citation_ids.some(id => !citations.has(id)))) return false
  if (sections.some(s => !s || !['direct','explanation','actions'].includes(s.kind) || !Array.isArray(s.claim_indexes)
    || !s.claim_indexes.length || s.claim_indexes.some(i => !Number.isInteger(i) || i < 0 || i >= claims.length))) return false
  const indexes = sections.flatMap(s => s.claim_indexes)
  if (new Set(sections.map(s => s.kind)).size !== sections.length || new Set(indexes).size !== indexes.length || indexes.length !== claims.length) return false
  const clarification = result.clarification
  if (clarification && (typeof clarification.question !== 'string' || !clarification.question.trim()
    || !Array.isArray(clarification.options) || clarification.options.length > 3
    || clarification.options.some(option => typeof option !== 'string' || !option.trim())
    || typeof clarification.allow_unknown !== 'boolean')) return false
  return true
}

export function clarificationReply(fact: string, option: string): string {
  if (option === 'Tên khác / Tôi không rõ' || option === 'Tôi không biết') return fact === 'document_type'
    ? 'Tôi không rõ tên giấy.' : 'Tôi không biết thông tin này.'
  return fact === 'document_type' ? `Trên giấy ghi: ${option}.` : option
}

/** Copy the same verified projection the reader sees, not a separate prose field. */
export function citizenAnswerText(result: Result): string {
  if (!validCitizenAnswer(result)) return 'Chưa hiển thị được đáp án do dữ liệu không đúng định dạng.'
  if (!result.verified_claims!.length) return result.content
  const parts=result.answer_sections!.flatMap(section=>section.claim_indexes.map(index=>{
    const claim=result.verified_claims![index]
    return claim.text+' '+claim.citation_ids.map(id=>`[${result.citations.findIndex(c=>c.id===id)+1}]`).join(' ')
  }))
  if(result.clarification)parts.push(result.clarification.question)
  parts.push(...(result.answer_notices || []))
  return parts.join('\n\n')
}
