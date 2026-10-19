import type { Artifact, EvaluationData } from './evaluation'

export interface EvaluationHighlight {
  kind: 'smoke' | 'recall' | 'faithfulness'
  value: number
  title: string
  sample: string
  description: string
  checked_at?: string
  release?: string
  configuration_sha256?: string
  backend?: string
  source?: Artifact
}

const validScore = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1
const timestamp = (date?: string) => date && Number.isFinite(Date.parse(date)) ? Date.parse(date) : 0

/** Archive records for presentation, never a replacement for the selected run. */
export function evaluationHighlights(data: EvaluationData): EvaluationHighlight[] {
  const runs = data.runs || []
  const main = runs.flatMap(run => run.suites.filter(suite => suite.split === 'smoke' && suite.status === 'reviewed'
    && suite.expected > 0 && validScore(suite.counts.pass / suite.expected) && suite.executed === suite.expected && !suite.counts.not_run && !suite.counts.awaiting_review
    && suite.counts.pass + suite.counts.partial + suite.counts.fail === suite.expected)
    .map(suite => ({run, suite})))
    .sort((a, b) => b.suite.counts.pass / b.suite.expected - a.suite.counts.pass / a.suite.expected
      || b.suite.expected - a.suite.expected || timestamp(b.suite.checked_at) - timestamp(a.suite.checked_at))[0]
  const retrieval = [...(data.retrieval_runs || [])].filter(report => report.k === 8 && validScore(report.gold_recall_at_8) && (report.eligible_cases || 0) > 0)
    .sort((a, b) => b.gold_recall_at_8! - a.gold_recall_at_8! || b.eligible_cases! - a.eligible_cases!
      || Number(b.release === data.active_release) - Number(a.release === data.active_release)
      || timestamp(b.checked_at) - timestamp(a.checked_at))[0]
  const faith = [...(data.faithfulness_runs || [])].filter(report => validScore(report.sampled_faithfulness)
    && report.scored_cases > 0 && report.total_judged_claims > 0 && report.scored_cases <= report.expected_cases)
    .sort((a, b) => b.sampled_faithfulness! - a.sampled_faithfulness!
      || b.scored_cases - a.scored_cases || timestamp(b.checked_at) - timestamp(a.checked_at))[0]
  const highlights: EvaluationHighlight[] = []
  if (main) highlights.push({kind: 'smoke', value: main.suite.counts.pass / main.suite.expected,
    title: 'Tỷ lệ đạt bộ chính', sample: `${main.suite.counts.pass}/${main.suite.expected} ca đạt đủ tiêu chí`,
    description: 'Gồm trả lời, hỏi lại và từ chối đúng theo bộ tiêu chí.',
    checked_at: main.suite.checked_at, release: main.run.release, configuration_sha256: main.run.configuration_sha256,
    backend: main.run.backend, source: main.suite.source})
  if (retrieval) highlights.push({kind: 'recall', value: retrieval.gold_recall_at_8!, title: 'Tìm nguồn · Recall@8',
    sample: `${retrieval.eligible_cases} ca có gold · ${retrieval.split === 'supplemental' ? 'Bộ bổ sung' : retrieval.split === 'natural' ? 'Câu hỏi tự nhiên' : 'Bộ chính'}`,
    description: 'Đo tìm đoạn nguồn; không đo chất lượng diễn giải đáp án.',
    checked_at: retrieval.checked_at, release: retrieval.release, configuration_sha256: retrieval.configuration_sha256,
    backend: retrieval.backend, source: retrieval.source})
  if (faith) {
    const run = runs.find(item => item.configuration_sha256 === faith.configuration_sha256)
    highlights.push({kind: 'faithfulness', value: faith.sampled_faithfulness!, title: 'Hỗ trợ từ nguồn · Faithfulness',
      sample: `${faith.scored_cases}/${faith.expected_cases} ca có điểm · ${faith.total_judged_claims} mệnh đề`,
      description: 'Chấm mẫu bằng cùng model; không phải thẩm định độc lập.',
      checked_at: faith.checked_at, release: run?.release, configuration_sha256: faith.configuration_sha256,
      backend: run?.backend, source: faith.source})
  }
  return highlights
}
