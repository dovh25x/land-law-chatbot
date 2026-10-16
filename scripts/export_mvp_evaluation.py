"""Export a CLI run for the versioned evaluation without inventing legal scores.

Run with the committed backend on PYTHONPATH. Results, corpus and configuration
must match; human/source reviews are bound to the exact answer checksum.
"""
import argparse
import hashlib
import json
from pathlib import Path

from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint, dataset, report_metrics
from landlaw.security import utcnow


def export(run_dir, output, release_path, suite_path=Path("data/evaluation/smoke.jsonl")):
    records = json.loads((run_dir / 'records.json').read_text())
    metadata = json.loads((run_dir / 'metadata.json').read_text())
    if metadata['configuration_sha256'] != configuration_fingerprint(Settings()):
        raise ValueError('Configuration mismatch; never mix runs or providers')
    suite_checksum = hashlib.sha256(suite_path.read_bytes()).hexdigest()
    if metadata.get('suite_sha256', suite_checksum) != suite_checksum:
        raise ValueError('Suite mismatch; never mix datasets')
    cases = dataset(suite_path)
    release = json.loads(release_path.read_text())
    sources = {c['id']: (d, c) for d in release['documents'] for c in d['chunks']}
    reviews_path = output / 'reviews.json'
    reviews = json.loads(reviews_path.read_text()) if reviews_path.exists() else {}
    rows = []
    for case in cases:
        matches = [r for r in records if r['case_id'] == case['id'] and r['mode'] == 'agentic']
        if not matches:
            continue
        answer = matches[-1]['result']
        if answer['corpus_release'] != release['id'] or answer['model'] != Settings().generation_model:
            raise ValueError('Corpus/model mismatch in result')
        valid = True if answer.get('citations') else None
        for citation in answer.get('citations', []):
            pair = sources.get(citation['id'])
            valid &= bool(pair and pair[0]['id'] == citation['document_id']
                and pair[1]['text'] == citation['excerpt']
                and pair[1]['locator'] == citation['locator']
                and pair[0]['url'] == citation['url']
                and hashlib.sha256(pair[1]['text'].encode()).hexdigest() == pair[1]['checksum'])
        checksum = hashlib.sha256(json.dumps(answer, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        review = reviews.get(case['id'], {})
        reviewed = review.get('answer_sha256') == checksum
        rows.append({'id': case['id'], 'question': case['question'], 'as_of': case.get('as_of'),
            'rubric': case['rubric'], 'gold_chunk_ids': case.get('gold_chunk_ids', []),
            'answer_origin': matches[-1].get('answer_origin', 'deterministic' if answer.get('llm_calls') == 0 else 'unknown'),
            'status': answer['status'], 'seconds': answer['elapsed_ms'] / 1000,
            'citations_valid': valid, 'answer': answer,
            'review': review['verdict'] if reviewed else 'awaiting_review',
            'review_note': review.get('note', '') if reviewed else '',
            'review_method': review.get('review_method', 'unspecified') if reviewed else 'awaiting_review',
            'answer_sha256': checksum})
    complete = len(rows) == len(cases) and all(r['status'] not in {'error', 'limited'} for r in rows)
    all_reviewed = complete and all(r['review'] in {'pass', 'partial', 'fail'} for r in rows)
    report = {'checked_at': utcnow().isoformat(), 'status': 'reviewed' if all_reviewed else 'awaiting_review' if complete else 'partial',
        'transport': 'operator_cli', 'storage_backend': metadata.get('storage_backend', 'unknown'), 'mode': 'agentic', 'model': Settings().generation_model,
        'identity': {'release': release['id'], 'configuration_sha256': metadata['configuration_sha256']},
        'suite_sha256': hashlib.sha256(suite_path.read_bytes()).hexdigest(),
        'history_mode': 'Frozen displayed history where provided; real conversational HTTPS checks are separate.',
        'legal_acceptance': False, 'acceptance_passed': False, 'independent_legal_certification': False,
        'scope': 'Actual model calls using the local source configuration and frozen corpus via operator CLI; not a deployment verification or HTTP latency benchmark.',
        'results': rows}
    report['review_methods'] = sorted({row['review_method'] for row in rows})
    report['metrics'] = report_metrics(rows)
    attempts = [json.loads(p.read_text()) for p in sorted((run_dir / 'attempts').glob('*.json'))]
    report['attempt_history'] = {'available_attempts': len(attempts),
        'limited_or_error_attempts': sum(a['record']['result']['status'] in {'limited', 'error'} for a in attempts),
        'scope': 'All retained execution attempts; retries inside a turn are counted in llm_calls.'}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'attempts.json').write_text(json.dumps({'scope': report['scope'],
        'configuration_sha256': metadata['configuration_sha256'], 'attempts': attempts}, ensure_ascii=False, indent=2)+'\n')
    (output / 'evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    counts = {verdict: sum(r['review'] == verdict for r in rows) for verdict in ('pass', 'partial', 'fail', 'awaiting_review')}
    lines = ['# Kết quả đánh giá hệ thống', '', f"Trạng thái: **{report['status']}**. Đã chạy {len(rows)}/{len(cases)} ca agentic.",
        f"Model: `{report['model']}`; release: `{release['id']}`; fingerprint: `{metadata['configuration_sha256']}`.",
        '', '**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.',
        '', f"Rà soát kỹ thuật theo tiêu chí/nguồn: {counts['pass']} pass, {counts['partial']} partial, {counts['fail']} fail, {counts['awaiting_review']} chưa rà soát.",
        'Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.',
        'Phương pháp rà soát: ' + '; '.join(report['review_methods']) + '.',
        '', '| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |', '|---|---|---:|---|---|']
    lines += [f"| {r['id']} | {r['status']} | {r['seconds']:.2f} | {r['citations_valid'] if r['citations_valid'] is not None else 'Không áp dụng'} | {r['review']} |" for r in rows]
    lines += ['', '## Kết quả theo hành vi', '', '| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |', '|---|---:|---:|---:|---:|---:|']
    lines += [f"| {name} | {g['cases']} | {g['pass']} | {g['partial']} | {g['fail']} | {g['awaiting_review']} |" for name, g in report['metrics']['groups'].items()]
    lines += ['', 'Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.',
              'Nguồn đáp án: ' + json.dumps(report['metrics']['answer_origin'], ensure_ascii=False) + '. unknown: artifact cũ không ghi nhận nguồn sinh.',
              '', '## Thống kê lượt chạy', '', '| Chỉ số | Số mẫu | Tổng | Median | p95 |', '|---|---:|---:|---:|---:|']
    lines += [f"| {name} | {v['samples']} | {v['total']} | {v['median']} | {v['p95']} |" for name, v in report['metrics']['usage'].items()]
    lines += ['', 'Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.']
    lines += ['', '## Ghi chú từng ca'] + [f"- {r['id']}: {r['review_note'] or 'Chưa rà soát nội dung.'}" for r in rows]
    (output / 'results.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'completed': len(rows), 'status': report['status'], 'reviews': counts}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, default=Path('data/evaluation/smoke.jsonl'))
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--release', type=Path, default=Path('data/releases/corpus-de584c31fc95f9a2.json'))
    parser.add_argument('--public-summary', type=Path, help='Publish a reviewed technical summary, never legal acceptance')
    parser.add_argument('--output', type=Path, default=Path('reports/evaluation/smoke'))
    args = parser.parse_args()
    export(args.run_dir, args.output, args.release, args.suite)
    if args.public_summary:
        report = json.loads((args.output / 'evaluation.json').read_text())
        if report['status'] != 'reviewed':
            raise SystemExit('Refusing public summary: every case must be executed and reviewed')
        rows = report['results']
        if any(r['citations_valid'] is False for r in rows):
            raise SystemExit('Refusing public summary: citation integrity check failed')
        summary = {k: report[k] for k in ('status', 'checked_at', 'model', 'mode', 'scope', 'suite_sha256', 'storage_backend', 'review_methods')}
        summary.update({'split': args.suite.stem, 'cases': len(rows), 'release': report['identity']['release'],
            'configuration_sha256': report['identity']['configuration_sha256'], 'acceptance_passed': False,
            'independent_legal_certification': False, 'transport': 'operator_cli',
            'results': [{'mode': 'agentic', 'completed': len(rows), 'reviewed': len(rows),
                'pass': sum(r['review']=='pass' for r in rows), 'partial': sum(r['review']=='partial' for r in rows),
                'fail': sum(r['review']=='fail' for r in rows), 'citation_sources_match_corpus': all(r['citations_valid'] is not False for r in rows)}],
            'limitations': ['Small regression-suite technical review only; not independent legal certification.',
                'Source IDs/excerpts matching the corpus do not prove every generated legal statement.',
                f'Read per-case reviews in {args.output}/results.md; no independent legal certification.'],
            'failed_case_ids': [r['id'] for r in rows if r['review']=='fail'],
            'partial_case_ids': [r['id'] for r in rows if r['review']=='partial'],
            'metrics': report['metrics'],
            'case_results':[{'id':r['id'],'status':r['status'],'review':r['review'],'seconds':r['seconds'],'note':r['review_note'],'citations_valid':r['citations_valid'],'answer_origin':r['answer_origin']} for r in rows]})
        args.public_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
