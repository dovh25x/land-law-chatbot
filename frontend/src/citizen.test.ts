import { describe, expect, it } from 'vitest'
import { citizenAnswerText, citizenSuggestions, clarificationReply, validCitizenAnswer } from './citizen'
import type { Result } from './api'

const valid = { status:'answered', answer_schema_version:2, content:'Không dùng phần này để thay claim.',
  citations:[{id:'c1'}],verified_claims:[{text:'Đoạn đã kiểm chứng.',citation_ids:['c1']}],
  answer_sections:[{kind:'direct',claim_indexes:[0]}] } as Result
describe('citizen suggestions', () => {
  it('keeps four distinct, short prompts across the supported topics', () => {
    expect(citizenSuggestions).toHaveLength(4)
    expect(new Set(citizenSuggestions).size).toBe(4)
    expect(citizenSuggestions[0]).toMatch(/giúp gì/i)
    expect(citizenSuggestions[1]).toContain('sổ đỏ')
    expect(citizenSuggestions[2]).toContain('nông nghiệp')
    expect(citizenSuggestions[3]).toContain('tái định cư')
    expect(citizenSuggestions.every(question => question.length <= 90)).toBe(true)
  })
})

describe('verified citizen projection', () => {
  it('accepts a complete projection and refuses missing, repeated or orphan references', () => {
    expect(validCitizenAnswer(valid)).toBe(true)
    expect(validCitizenAnswer({...valid,answer_sections:[]})).toBe(false)
    expect(validCitizenAnswer({...valid,answer_sections:[{kind:'direct',claim_indexes:[1]}]})).toBe(false)
    expect(validCitizenAnswer({...valid,answer_sections:[{kind:'direct',claim_indexes:[0,0]}]})).toBe(false)
    expect(validCitizenAnswer({...valid,citations:[]})).toBe(false)
    expect(validCitizenAnswer({...valid,clarification:{fact:'date',question:'Ngày nào?',options:['Có'],allow_unknown:true}})).toBe(true)
  })
  it('keeps old answers outside the structured renderer', () => {
    expect(validCitizenAnswer({...valid,answer_schema_version:1})).toBe(false)
  })
  it('copies only the verified projection and never an alternative summary', () => {
    expect(citizenAnswerText(valid)).toBe('Đoạn đã kiểm chứng. [1]')
    expect(citizenAnswerText(valid)).not.toContain('Không dùng phần này')
    expect(citizenAnswerText({...valid,answer_notices:['Giới hạn snapshot.']})).toContain('Giới hạn snapshot.')
  })
  it('turns the unknown choice into a clear user statement without assuming paper type', () => {
    expect(clarificationReply('document_type','Tên khác / Tôi không rõ')).toBe('Tôi không rõ tên giấy.')
    expect(clarificationReply('document_type','Thông báo thu hồi đất')).toBe('Trên giấy ghi: Thông báo thu hồi đất.')
  })
})
