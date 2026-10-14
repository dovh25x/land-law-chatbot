import hashlib,importlib.util,json
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('review_preparation',Path(__file__).parents[1]/'scripts/prepare_evaluation_review.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def inputs():
    text='Điều 1. Cần đối chiếu điều kiện pháp luật và hồ sơ.'
    chunk={'id':'law-1','document_id':'law','locator':'Điều 1','text':text,'checksum':hashlib.sha256(text.encode()).hexdigest()}
    release={'id':'r1','documents':[{'id':'law','source_kind':'legal','url':'https://vanban.chinhphu.vn/','chunks':[chunk]}]}
    case={'id':'S01','question':'Điều kiện là gì?','rubric':['Dẫn căn cứ'],'gold_chunk_ids':['law-1']}
    result={'status':'answered','content':'Cần đối chiếu điều kiện pháp luật và hồ sơ.','as_of':'2026-10-14','corpus_release':'r1','evidence_chunk_ids':['law-1'],
            'citations':[{'id':'law-1','document_id':'law','excerpt':text}],
            'verified_claims':[{'kind':'legal_rule','text':text,'citation_ids':['law-1']}]}
    return [{'case_id':'S01','mode':'agentic','result':result}],[case],release


def test_review_bundle_carries_exact_sources_and_hash_but_never_marks_pass():
    records,cases,release=inputs();bundle=module.prepare(records,cases,release)[0]
    assert bundle['citations']['law-1']['text']==release['documents'][0]['chunks'][0]['text']
    assert bundle['result_sha256']==hashlib.sha256(json.dumps(records[0]['result'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    assert bundle['review_status']=='awaiting_source_review' and 'passed' not in bundle


@pytest.mark.parametrize('fault',['wrong_corpus','wrong_excerpt','missing_gold','altered_source'])
def test_review_rejects_changed_proof_before_preparing_bundle(fault):
    records,cases,release=inputs()
    if fault=='wrong_corpus':records[0]['result']['corpus_release']='r2'
    elif fault=='wrong_excerpt':records[0]['result']['citations'][0]['excerpt']='Đoạn khác.'
    elif fault=='missing_gold':cases[0]['gold_chunk_ids']=['missing']
    else:release['documents'][0]['chunks'][0]['text']='Nguồn đã bị thay đổi.'
    with pytest.raises(ValueError):module.prepare(records,cases,release)
