"""Single-mode submission runs must not claim paired benchmark completion."""
import pytest
from landlaw.evaluation import evaluate, summarise, public_report


@pytest.mark.parametrize('modes', [(), ('other',), ('agentic', 'agentic')])
async def test_evaluation_rejects_invalid_mode_selection_before_any_provider_call(modes):
    with pytest.raises(ValueError, match='Evaluation modes'):
        await evaluate(None, None, None, modes=modes)


def test_single_mode_results_do_not_claim_full_paired_review_or_acceptance():
    result={'status':'clarification_needed','elapsed_ms':10,'citations':[],
            'evidence_chunk_ids':[],'verified_claims':[],'llm_calls':0,'tool_calls':0}
    report=public_report(summarise([{'case_id':'S1','mode':'agentic','result':result}],
        [{'id':'S1','ground_truth_status':'source_checked','gold_chunk_ids':[]}], 'suite'))
    assert report['completed_pairs']==0
    assert report['acceptance_passed'] is False
    assert report['quality_metrics_status']=='withheld_pending_full_source_review'
    assert all(row['answer_pass_rate'] is None for row in report['results'])
