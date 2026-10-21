import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { DocumentRow, generationLabel } from './ui'

describe('verified source lookup labels', () => {
  it('does not describe source lookup as generated legal answers', () => {
    expect(generationLabel({ generation_available: false, reason: 'disabled', source_lookup_only: true })).toContain('không sinh đáp án AI')
  })
  it('labels passage count, date and whole-document limits on source rows', () => {
    const html = renderToStaticMarkup(DocumentRow({ document: {
      id: 'law', title: 'Văn bản công khai', url: 'https://example.test/law', source_kind: 'legal',
      checked_at: '2026-10-21', applicability_verified: false, source_lookup_only: true,
      review_as_of: '2026-10-21', verified_passage_count: 2,
    }, onOpen: () => {} }))
    expect(html).toContain('2 đoạn được review')
    expect(html).toContain('Không xác minh toàn văn')
    expect(html).not.toContain('Có thể sinh đáp án')
  })
})
