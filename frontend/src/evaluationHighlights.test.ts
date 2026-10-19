import {describe,expect,it} from 'vitest'
import {evaluationHighlights} from './evaluationHighlights'
import {emptyCounts,type EvaluationData,type EvaluationRun} from './evaluation'

const run=(id:string,pass:number,reviewed=true):EvaluationRun=>({id,release:'historical',backend:'sqlite',configuration_sha256:id,suites:[{split:'smoke',label:'Bộ chính',checked_at:'2026-10-17T00:00:00Z',expected:20,executed:20,status:reviewed?'reviewed':'awaiting_review',counts:{...emptyCounts(),pass,fail:20-pass},metrics:{},cases:[]}]})
describe('record highlights retain scope and leave the full evaluation archive intact',()=>{
 it('uses a fully reviewed suite and preserves default selection, failures and source version',()=>{
  const data:EvaluationData={default_run_id:'current',runs:[run('current',16),run('historical-best',19),run('unreviewed',20,false)]}
  const original=JSON.stringify(data),best=evaluationHighlights(data)[0]
  expect(best.value).toBe(.95)
  expect(best.configuration_sha256).toBe('historical-best')
  expect(best.sample).toBe('19/20 ca đạt đủ tiêu chí')
  expect(JSON.stringify(data)).toBe(original)
 })
 it('does not label partial runs or an unscored faithfulness sample as a record',()=>{
  const partial=run('partial',20);partial.suites[0].executed=1
  const data:EvaluationData={runs:[partial],faithfulness_runs:[{sampled_faithfulness:null,scored_cases:0,expected_cases:8,total_judged_claims:0}]}
  expect(evaluationHighlights(data)).toEqual([])
 })
 it('keeps the three-case retrieval scope and the six-of-eight historical faithfulness coverage',()=>{
  const data:EvaluationData={active_release:'current',runs:[run('judge-version',19)],retrieval_runs:[
   {k:8,gold_recall_at_8:1,eligible_cases:3,split:'supplemental',release:'current',backend:'postgresql'},
   {k:8,gold_recall_at_8:1,eligible_cases:0,split:'smoke'},
  ],faithfulness_runs:[{configuration_sha256:'judge-version',sampled_faithfulness:12/13,scored_cases:6,expected_cases:8,total_judged_claims:13}]}
  const highlights=evaluationHighlights(data)
  expect(highlights.find(x=>x.kind==='recall')?.sample).toBe('3 ca có gold · Bộ bổ sung')
  expect(highlights.find(x=>x.kind==='recall')?.backend).toBe('postgresql')
  expect(highlights.find(x=>x.kind==='faithfulness')?.sample).toBe('6/8 ca có điểm · 13 mệnh đề')
  expect(highlights.find(x=>x.kind==='faithfulness')?.release).toBe('historical')
 })
})
