"""Export a CLI run for the academic handoff without inventing legal scores.

Run with the committed backend on PYTHONPATH. Results, corpus and configuration
must match; human/source reviews are bound to the exact answer checksum.
"""
import argparse
import hashlib
import json
from html import escape
from pathlib import Path

from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint, dataset
from landlaw.security import utcnow


def export(run_dir, output, release_path):
    records = json.loads((run_dir / 'records.json').read_text())
    metadata = json.loads((run_dir / 'metadata.json').read_text())
    if metadata['configuration_sha256'] != configuration_fingerprint(Settings()):
        raise ValueError('Configuration mismatch; never mix runs or providers')
    cases = dataset(Path('data/evaluation/smoke.jsonl'))
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
        valid = True
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
            'status': answer['status'], 'seconds': answer['elapsed_ms'] / 1000,
            'citations_valid': valid, 'answer': answer,
            'review': review['verdict'] if reviewed else 'awaiting_review',
            'review_note': review.get('note', '') if reviewed else '', 'answer_sha256': checksum})
    complete = len(rows) == len(cases) and all(r['status'] not in {'error', 'limited'} for r in rows)
    all_reviewed = complete and all(r['review'] in {'pass', 'partial', 'fail'} for r in rows)
    report = {'checked_at': utcnow().isoformat(), 'status': 'reviewed' if all_reviewed else 'awaiting_review' if complete else 'partial',
        'transport': 'operator_cli', 'mode': 'agentic', 'model': Settings().generation_model,
        'identity': {'release': release['id'], 'configuration_sha256': metadata['configuration_sha256']},
        'suite_sha256': hashlib.sha256(Path('data/evaluation/smoke.jsonl').read_bytes()).hexdigest(),
        'history_mode': 'Frozen benchmark fixture for S14; real conversational HTTPS smoke is reported separately.',
        'legal_acceptance': False, 'acceptance_passed': False, 'independent_legal_certification': False,
        'scope': 'Actual Groq generation with deployed backend code and Supabase corpus via operator CLI; not an HTTP/browser latency benchmark.',
        'results': rows}
    attempts = [json.loads(p.read_text()) for p in sorted((run_dir / 'attempts').glob('*.json'))]
    report['attempt_history'] = {'available_attempts': len(attempts),
        'limited_or_error_attempts': sum(a['record']['result']['status'] in {'limited', 'error'} for a in attempts),
        'scope': 'All retained execution attempts; retries inside a turn are counted in llm_calls.'}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'attempts.json').write_text(json.dumps({'scope': report['scope'],
        'configuration_sha256': metadata['configuration_sha256'], 'attempts': attempts}, ensure_ascii=False, indent=2)+'\n')
    (output / 'evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    counts = {verdict: sum(r['review'] == verdict for r in rows) for verdict in ('pass', 'partial', 'fail', 'awaiting_review')}
    lines = ['# Kết quả kiểm tra MVP Groq', '', f"Trạng thái: **{report['status']}**. Đã chạy {len(rows)}/{len(cases)} ca agentic.",
        f"Model: `{report['model']}`; release: `{release['id']}`; fingerprint: `{metadata['configuration_sha256']}`.",
        '', '**Cách chạy:** CLI quản trị gọi Groq thật trên corpus Supabase; kiểm chứng HTTPS được kiểm chứng riêng. S14 dùng lịch sử cố định của bộ kiểm tra.',
        '', f"Rà soát kỹ thuật theo rubric/nguồn: {counts['pass']} pass, {counts['partial']} partial, {counts['fail']} fail, {counts['awaiting_review']} chưa rà soát.",
        'Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.',
        '', '| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |', '|---|---|---:|---|---|']
    lines += [f"| {r['id']} | {r['status']} | {r['seconds']:.2f} | {r['citations_valid']} | {r['review']} |" for r in rows]
    lines += ['', '## Ghi chú từng ca'] + [f"- {r['id']}: {r['review_note'] or 'Chưa rà soát nội dung.'}" for r in rows]
    (output / 'results.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'completed': len(rows), 'status': report['status'], 'reviews': counts}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--release', type=Path, default=Path('data/releases/corpus-de584c31fc95f9a2.json'))
    parser.add_argument('--public-summary', type=Path, help='Publish a reviewed academic summary, never legal acceptance')
    parser.add_argument('--output', type=Path, default=Path('reports/submission'))
    args = parser.parse_args()
    export(args.run_dir, args.output, args.release)
    if args.public_summary:
        report = json.loads((args.output / 'evaluation.json').read_text())
        if report['status'] != 'reviewed':
            raise SystemExit('Refusing public summary: every case must be executed and reviewed')
        rows = report['results']
        summary = {k: report[k] for k in ('status', 'checked_at', 'model', 'mode', 'scope', 'suite_sha256')}
        summary.update({'split': 'academic_smoke', 'cases': len(rows), 'release': report['identity']['release'],
            'configuration_sha256': report['identity']['configuration_sha256'], 'acceptance_passed': False,
            'independent_legal_certification': False, 'transport': 'operator_cli',
            'results': [{'mode': 'agentic', 'completed': len(rows), 'reviewed': len(rows),
                'pass': sum(r['review']=='pass' for r in rows), 'partial': sum(r['review']=='partial' for r in rows),
                'fail': sum(r['review']=='fail' for r in rows), 'citation_sources_match_corpus': all(r['citations_valid'] for r in rows)}],
            'limitations': ['20-case academic rubric review only; not independent legal certification.',
                'Source IDs/excerpts matching the corpus do not prove every generated legal statement.',
                'Read per-case failures and partial answers in submission/results.md; no independent legal certification.'],
            'failed_case_ids': [r['id'] for r in rows if r['review']=='fail'],
            'partial_case_ids': [r['id'] for r in rows if r['review']=='partial'],
            'case_results':[{'id':r['id'],'status':r['status'],'review':r['review'],'seconds':r['seconds'],'note':r['review_note']} for r in rows]})
        args.public_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
        html = '<!doctype html><html lang="vi"><meta charset="utf-8"><title>Đánh giá MVP Groq</title><style>body{font:15px/1.7 Arial;max-width:1000px;margin:40px auto;padding:24px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Đánh giá MVP học thuật</h1><p>20 ca agentic; không phải nghiệm thu pháp lý.</p><pre>' + escape(json.dumps(summary, ensure_ascii=False, indent=2)) + '</pre></html>'
        destination = args.public_summary.with_name('benchmark.html') if args.public_summary.name == 'latest.json' else args.public_summary.with_suffix('.html')
        destination.write_text(html)
