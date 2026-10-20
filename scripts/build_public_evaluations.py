"""Publish descriptive metrics from committed evaluation artifacts, without model calls."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

SPLITS = {'smoke': 'Bộ chính', 'supplemental': 'Bổ sung', 'natural': 'Câu hỏi tự nhiên'}


def build(root: Path):
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    tracked = subprocess.check_output(['git', 'ls-files', 'reports'], cwd=root, text=True).splitlines()
    suites = {name: [json.loads(line) for line in (root / 'data/evaluation' / (name+'.jsonl')).read_text().splitlines() if line.strip()] for name in SPLITS}
    labels=dict(SPLITS)
    registry_path=root/'data/evaluation/registry.json'
    registry=json.loads(registry_path.read_text()) if registry_path.exists() else {}
    from landlaw.evaluation import frozen_dataset
    for split,entry in registry.get('suites',{}).items():
        if entry.get('executable') is True:
            suites[split]=frozen_dataset(root/'data',split)[0]
            labels[split]=entry.get('label',split)
    runs, retrieval, faithfulness = {}, [], []
    sources = []
    for name in sorted(tracked):
        path = Path(name)
        kind = ('generation' if path.name == 'evaluation.json' else
                'retrieval' if 'retrieval' in path.parts and path.suffix == '.json' else
                'faithfulness' if path.name == 'faithfulness.json' else None)
        if not kind:
            continue
        raw = (root / path).read_bytes()
        value = json.loads(raw)
        if not isinstance(value, dict) or not isinstance(value.get('results'), list):
            continue
        source = {'path': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                  'url': f'https://github.com/dovh25x/land-law-chatbot/blob/{revision}/{name}'}
        sources.append(source)
        if kind == 'retrieval':
            retrieval.append({**{k: value.get(k) for k in ('checked_at', 'split', 'release', 'configuration_sha256', 'backend', 'k', 'eligible_cases', 'hits', 'hit_rate', 'gold_recall_at_8', 'complete_evidence_coverage', 'history_groups', 'scope')},
                'source': source, 'cases': [{k: row.get(k) for k in ('id', 'hit', 'gold_recall_at_8', 'evidence_group_coverage', 'has_history', 'elapsed_ms')} for row in value['results']]})
            continue
        if kind == 'faithfulness':
            faithfulness.append({**{k: value.get(k) for k in ('checked_at', 'configuration_sha256', 'judge_model', 'sampled_faithfulness', 'scored_cases', 'expected_cases', 'total_judged_claims', 'sample_case_ids', 'scope')},
                'source': source, 'cases': [{k: row.get(k) for k in ('id', 'status', 'score', 'supported_claims', 'total_claims')} for row in value['results']]})
            continue
        identity = value.get('identity') or {}
        split = value.get('split') if value.get('split') in suites else path.parent.name if path.parent.name in suites else next((s for prefix, s in [('S', 'smoke'), ('X', 'supplemental'), ('N', 'natural')] if value['results'] and value['results'][0]['id'].startswith(prefix)), None)
        if split is None:
            raise ValueError('Unknown frozen suite: '+name)
        folder = path.parent.parent if path.parent.name in suites else path.parent
        family='legacy' if split in SPLITS else split
        key = str(folder)+':'+str(identity.get('configuration_sha256'))
        if family!='legacy':key+=':'+family
        run = runs.setdefault(key, {'id': hashlib.sha256(key.encode()).hexdigest()[:16],
            'release': identity.get('release'), 'configuration_sha256': identity.get('configuration_sha256'),
            'backend': value.get('storage_backend', 'unknown'), 'model': value.get('model'), 'evaluation_family':family, 'suites': []})
        frozen={case['id']:case for case in suites[split]}
        rows = []
        for row in value['results']:
            answer = row.get('answer') or {}
            rows.append({'id': row['id'], 'question': frozen.get(row['id'], {}).get('question', row.get('question', '')),
                'status': row.get('status'), 'review': row.get('review', 'awaiting_review'),
                'note': row.get('review_note', ''), 'seconds': row.get('seconds'),
                'citations_valid': row.get('citations_valid'), 'answer_origin': row.get('answer_origin', 'unknown'),
                'answer_sha256': row.get('answer_sha256'),
                'llm_calls': answer.get('llm_calls'), 'tool_calls': answer.get('tool_calls'), 'token_usage': answer.get('token_usage')})
        present = {row['id'] for row in rows}
        rows.extend({'id': case['id'], 'question': case['question'], 'status': 'not_run', 'review': 'not_run', 'note': 'Chưa thực hiện trong lần chạy này.', 'seconds': None, 'citations_valid': None, 'answer_origin': 'unknown'} for case in suites[split] if case['id'] not in present)
        counts = Counter(row['review'] for row in rows)
        run['suites'].append({'split': split, 'label': labels[split], 'checked_at': value.get('checked_at'),
            'status': value.get('status'), 'expected': len(suites[split]), 'executed': len(value['results']),
            'counts': {k: counts[k] for k in ('pass', 'partial', 'fail', 'awaiting_review', 'not_run')},
            'metrics': value.get('metrics', {}), 'attempt_history': value.get('attempt_history', {}),
            'citizen_metrics':value.get('citizen_metrics'),
            'source': source, 'cases': rows})
    result = list(runs.values())
    for run in result:
        run['checked_at'] = max(s['checked_at'] or '' for s in run['suites'])
        run['complete'] = len(run['suites']) == (3 if run['evaluation_family']=='legacy' else 1) and all(s['expected'] == s['executed'] for s in run['suites'])
        run['suites'].sort(key=lambda s: list(labels).index(s['split']))
    result.sort(key=lambda r: (r['checked_at'], r['id']), reverse=True)
    # Reviewer errata are annotations; never change the original verdict or artifact.
    errata = []
    for name in tracked:
        if name.endswith('-erratum.json'):
            correction = json.loads((root / name).read_text())
            if correction.get('artifact') in {s['path'] for s in sources}:
                errata.append({k: correction.get(k) for k in ('artifact', 'case_id', 'correction', 'scope')})
    return {'schema_version': 1, 'source_revision': revision, 'runs': result,
            'retrieval_runs': sorted(retrieval, key=lambda r: r.get('checked_at') or '', reverse=True),
            'faithfulness_runs': sorted(faithfulness, key=lambda r: r.get('checked_at') or '', reverse=True),
            'errata': errata, 'sources': sources}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('reports/public-evaluations.json'))
    args = parser.parse_args()
    payload = build(Path(__file__).resolve().parents[1])
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: len(payload[key]) for key in ('runs', 'retrieval_runs', 'faithfulness_runs', 'sources')}))
