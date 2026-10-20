export type Verdict = 'pass' | 'partial' | 'fail' | 'awaiting_review' | 'not_run'
export type Counts = Record<Verdict, number>
export interface Artifact { path: string; sha256: string; url: string }
export interface CaseResult { id: string; question?: string; status: string; review: Verdict; note: string; seconds: number | null; citations_valid?: boolean | null; answer_origin?: string; answer_sha256?: string; llm_calls?: number; tool_calls?: number; token_usage?: number }
export interface Metrics { evidence_hit_at_8?:{eligible_cases:number;measured_cases:number;hits:number;rate:number|null}; llm_used_cases?:number; groups?: Record<string, {cases:number;pass:number;partial:number;fail:number;awaiting_review?:number}>; answer_origin?: Record<string,number>; usage?:Record<string,{samples:number;total?:number;median:number|null;p95:number|null}> }
export interface CitizenMetrics { groups:Record<string,{expected:number;counts:Counts;false_abstention:number}>; citation_evidence_coverage?:{eligible_cases:number;executed_cases:number;complete_cases:number} }
export interface Suite { split: string; label: string; checked_at?: string; status?: string; expected: number; executed: number; counts: Counts; metrics: Metrics; cases: CaseResult[]; source?: Artifact; citizen_metrics?:CitizenMetrics|null; attempt_history?: {available_attempts?:number;limited_or_error_attempts?:number} }
export interface EvaluationRun { id:string; checked_at?:string; release?:string; configuration_sha256?:string; backend?:string; model?:string; complete?:boolean; matches_active_release?:boolean; matches_active_configuration?:boolean; suites:Suite[] }
export interface RetrievalReport {checked_at?:string;split?:string;release?:string;configuration_sha256?:string;backend?:string;k?:number;history_groups?:Record<string,{cases:number;gold_recall_at_8:number|null}>;eligible_cases?:number;hits?:number;hit_rate?:number|null;gold_recall_at_8?:number|null;source?:Artifact;cases?:{id:string;hit:boolean;gold_recall_at_8:number|null}[]}
export interface FaithfulnessReport {checked_at?:string;configuration_sha256?:string;judge_model?:string;sampled_faithfulness?:number|null;scored_cases:number;expected_cases:number;total_judged_claims:number;source?:Artifact;cases?:{id:string;status:string;score:number|null;supported_claims?:number;total_claims?:number}[]}
export interface EvaluationData {status?:string;runs?:EvaluationRun[];default_run_id?:string;active_release?:string;active_configuration_sha256?:string;retrieval_runs?:RetrievalReport[];faithfulness_runs?:FaithfulnessReport[];sources?:Artifact[];errata?:{artifact:string;case_id:string;correction:string}[];[key:string]:unknown}
export const verdictLabels:Record<Verdict,string> = {pass:'Đạt',partial:'Một phần',fail:'Chưa đạt',awaiting_review:'Chưa rà soát',not_run:'Chưa chạy'}
export const suiteLabels:Record<string,string> = {smoke:'Bộ chính',supplemental:'Bổ sung',natural:'Câu hỏi tự nhiên'}
export const groupLabels:Record<string,string> = {answered:'Trả lời nội dung',clarification:'Hỏi làm rõ',insufficient:'Thiếu chứng cứ / ngoài phạm vi',execution_failure:'Lỗi thực thi'}
export const emptyCounts = ():Counts => ({pass:0,partial:0,fail:0,awaiting_review:0,not_run:0})
export function totals(suites:Suite[]) { return suites.reduce((sum,suite)=>{for(const key of Object.keys(sum) as Verdict[])sum[key]+=suite.counts[key]||0;return sum},emptyCounts()) }
/** Older API responses remain readable during a sequential frontend/backend rollout. */
export function availableRuns(data:EvaluationData):EvaluationRun[] {
 if(data.runs?.length)return data.runs
 if(!data.status||data.status==='not_run')return []
 const cases=((data.case_results||[]) as (CaseResult&{note:string})[]).map(row=>({...row,seconds:row.seconds??null}))
 const summary=((data.results||[]) as Partial<Counts>[])[0]||{}
 const counts=emptyCounts();for(const key of Object.keys(counts) as Verdict[])counts[key]=Number(summary[key])||0
 const expected=Number(data.cases)||counts.pass+counts.partial+counts.fail||cases.length
 const suites:Suite[]=[{split:'smoke',label:'Bộ chính',expected,executed:expected,counts,metrics:(data.metrics||{}) as Metrics,cases}]
 const extra=data.supplemental as {cases:number;completed:number;pass:number;partial:number;fail:number;note:string}|undefined
 if(extra)suites.push({split:'supplemental',label:'Bổ sung',expected:extra.cases,executed:extra.completed,counts:{...emptyCounts(),pass:extra.pass,partial:extra.partial,fail:extra.fail,not_run:extra.cases-extra.completed},metrics:{},cases:[]})
 return [{id:'legacy-summary',checked_at:data.checked_at as string,release:data.evaluation_release as string,model:data.model as string,backend:data.storage_backend as string,configuration_sha256:data.configuration_sha256 as string,matches_active_release:!!data.matches_active_release,matches_active_configuration:!!data.matches_active_configuration,suites}]
}
