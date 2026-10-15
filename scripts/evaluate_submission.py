"""Twenty agentic cases against the public demo; checkpoint, no quota bypass.

Does not publish or grade legal correctness. Never persists session credentials.
Run: .venv/bin/python scripts/evaluate_submission.py
"""
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = 'https://land-law-chatbot.onrender.com'
OUT = Path('reports/submission')


def write(report):
    OUT.mkdir(parents=True, exist_ok=True)
    report['checked_at'] = datetime.now(timezone.utc).isoformat()
    (OUT / 'evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    reviews_path=OUT/'reviews.json'
    reviews=json.loads(reviews_path.read_text()) if reviews_path.exists() else {}
    for row in report['results']:
        review=reviews.get(row['id'],{})
        answer_hash=hashlib.sha256(json.dumps(row['answer'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        if review.get('answer_sha256')==answer_hash:
            row['review']=review['verdict'];row['review_note']=review['note']
    (OUT / 'evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    lines = ['# Kết quả 20 ca trên API cloud', '',
             f"Trạng thái: **{report['status']}**. Đã chạy {len(report['results'])}/20. Chưa tự động chấm đúng pháp lý.", '',
             '| Ca | Trạng thái API | Giây | Trích dẫn khớp nguồn | Review nội dung |',
             '|---|---|---:|---|---|']
    for row in report['results']:
        lines.append(f"| {row['id']} | {row.get('status','error')} | {row.get('seconds','')} | {row.get('citations_valid')} | {row.get('review','awaiting_review')} |")
    lines += ['', 'Phạm vi: API công khai, một người dùng, có thể gồm cold start. Không phải p95/SLA; không ghép báo cáo cấu hình khác.',
              'Câu tiếp nối S14 dùng câu trả lời thật của lượt mở đầu cùng phiên; không chèn lịch sử giả.']
    lines += ['', '## Ghi chú rà soát kỹ thuật (không phải thẩm định pháp lý độc lập)']
    for row in report['results']:
        if row.get('review_note'): lines.append('- '+row['id']+': '+row['review_note'])
    if report.get('blocker'): lines += ['', 'Trở ngại: '+report['blocker']]
    (OUT/'results.md').write_text('\n'.join(lines)+'\n')


def main():
    cases_path=Path('data/evaluation/smoke.jsonl')
    cases=[json.loads(s) for s in cases_path.read_text().splitlines() if s.strip()]
    suite_hash=hashlib.sha256(cases_path.read_bytes()).hexdigest()
    report={'status':'running','base_url':BASE,'mode':'agentic','suite_sha256':suite_hash,
            'runner_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'legal_acceptance':False,'results':[]}
    file=OUT/'evaluation.json'
    if file.exists():
        old=json.loads(file.read_text())
        if old.get('suite_sha256')==suite_hash: report=old
    write(report)
    with httpx.Client(timeout=150, transport=httpx.HTTPTransport(retries=3)) as client:
        try:
            ready=client.get(BASE+'/readyz'); ready.raise_for_status()
            active=client.get(BASE+'/api/v1/evaluations/latest');active.raise_for_status()
            identity={'release':ready.json().get('corpus_release'),
                      'configuration_sha256':active.json().get('active_configuration_sha256')}
            if not identity['release'] or not identity['configuration_sha256']:
                raise ValueError('API does not expose release/configuration identity')
            if report.get('identity') and report['identity']!=identity:
                raise ValueError('Active configuration changed; archive previous checkpoint before rerunning')
            report['identity']=identity;report['readiness']=ready.json();report.pop('blocker',None)
            def post(path,payload,headers=None):
                # Wait for public abuse protection; do not create sessions to evade it.
                for attempt in range(4):
                    r=client.post(BASE+path,json=payload,headers=headers)
                    if r.status_code!=429: r.raise_for_status();return r
                    delay=min(86400,max(1,int(r.headers.get('Retry-After','60'))))
                    if delay>65: raise ValueError('Public daily/provider limit: resume checkpoint later')
                    print(json.dumps({'waiting_seconds':delay}),flush=True);time.sleep(delay)
                raise ValueError('Public rate limit persists; resume checkpoint later')
            def chat(session,question,date):
                r=post('/api/v1/chat',{'session_id':session['session_id'],'message':question,
                       'as_of':date,'mode':'agentic'}, {'Authorization':'Bearer '+session['token']})
                events=[json.loads(l[6:]) for l in r.text.splitlines() if l.startswith('data: ')]
                return next((e for e in events if 'trace_id' in e),{'status':'error','content':'No final SSE result'})
            done={r['id'] for r in report['results']}
            for case in cases:
                if case['id'] in done:continue
                session=post('/api/v1/sessions',{}).json()
                if case.get('history'):
                    chat(session,case['history'][0]['content'],case['as_of'])
                start=time.monotonic();answer=chat(session,case['question'],case.get('as_of'))
                valid=True
                for citation in answer.get('citations',[]):
                    r=client.get(BASE+'/api/v1/documents/'+citation['document_id'],params={'locator':citation['locator']})
                    valid &= r.status_code==200 and any(c['id']==citation['id'] and c['text']==citation['excerpt'] for c in r.json().get('document',{}).get('chunks',[]))
                check=client.get(BASE+'/api/v1/evaluations/latest');check.raise_for_status()
                if check.json().get('active_configuration_sha256')!=identity['configuration_sha256']:
                    raise ValueError('Configuration changed during evaluation; stop without mixing records')
                report['results'].append({'id':case['id'],'question':case['question'],'as_of':case.get('as_of'),
                    'rubric':case['rubric'],'gold_chunk_ids':case.get('gold_chunk_ids',[]),
                    'status':answer.get('status'),'seconds':round(time.monotonic()-start,2),
                    'citations_valid':valid,'answer':answer,'review':'awaiting_review'})
                write(report); print(json.dumps({'case':case['id'],'status':answer.get('status')}),flush=True)
            report['status']='awaiting_review'
        except (httpx.HTTPError,ValueError,KeyError) as exc:
            report['status']='partial'; report['blocker']=type(exc).__name__+': '+str(exc).split('?')[0][:200]
        write(report)
    print(json.dumps({'status':report['status'],'completed':len(report['results'])}))


if __name__=='__main__':
    import fcntl
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'.evaluation.lock').open('w') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise SystemExit('Another submission runner is active')
        main()
