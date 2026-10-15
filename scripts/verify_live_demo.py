"""Authenticated HTTPS smoke; only observed results, never provider output in logs."""
import asyncio
import json
from pathlib import Path
import httpx
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint


async def main():
    base='https://land-law-chatbot.onrender.com'
    async with httpx.AsyncClient(timeout=180) as client:
        ready=await client.get(base+'/readyz');ready.raise_for_status()
        evaluation=(await client.get(base+'/api/v1/evaluations/latest')).json()
        if evaluation.get('active_configuration_sha256')!=configuration_fingerprint(Settings()):
            raise ValueError('Deployed configuration differs from local code/model')
        s=(await client.post(base+'/api/v1/sessions')).json()
        headers={'Authorization':'Bearer '+s['token']}
        checks=[]
        for question in ['Điều 104 Luật Đất đai 2024 quy định chi phí di chuyển tài sản gồm những khoản nào?',
                         'Văn bản đó quy định cơ quan nào quyết định mức bồi thường tại Điều 104?',
                         'Thông tin dự án Olympic có đủ xác định tiền bồi thường của hộ không?']:
            r=await client.post(base+'/api/v1/chat',headers=headers,json={'session_id':s['session_id'],'message':question})
            r.raise_for_status()
            frames=[json.loads(line[6:]) for line in r.text.splitlines() if line.startswith('data: ')]
            result=next((v for v in frames if 'trace_id' in v),None)
            if not result or result['status'] in {'limited','error'}:raise ValueError('No completed public answer')
            for citation in result['citations']:
                doc=await client.get(base+'/api/v1/documents/'+citation['document_id']);doc.raise_for_status()
            trace=await client.get(base+f"/api/v1/sessions/{s['session_id']}/traces/{result['trace_id']}",headers=headers)
            trace.raise_for_status()
            unauthorized=await client.get(base+f"/api/v1/sessions/{s['session_id']}/traces/{result['trace_id']}",headers={'Authorization':'Bearer invalid'})
            if unauthorized.status_code not in {401,404}:raise ValueError('Trace access isolation failed')
            checks.append({'question':question,'status':result['status'],'content':result['content'],
                'citations':len(result['citations']),'llm_calls':result['llm_calls'],'model':result['model'],
                'elapsed_ms':result['elapsed_ms']})
        if not checks[0]['citations'] or not checks[0]['llm_calls']:raise ValueError('Source-backed generation missing')
        if 'chỉ hỗ trợ Vành đai 4' not in checks[2]['content'] or checks[2]['llm_calls']!=0:
            raise ValueError('Project scope guard failed')
        history=await client.get(base+f"/api/v1/sessions/{s['session_id']}/messages",headers=headers)
        if len(history.json()['messages'])!=6:raise ValueError('History persistence failed')
        path=Path('reports/submission/live-demo.json');path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'passed':True,'configuration_sha256':configuration_fingerprint(Settings()),
            'matches_evaluation':evaluation.get('matches_active_configuration'),'checks':checks},ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'passed':True,'turns':len(checks)}))


if __name__=='__main__':asyncio.run(main())
