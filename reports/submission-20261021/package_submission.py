"""Package academic documents deterministically; no Git, cloud, API or database writes.

Run only after the final build/export/validation. Sources remain in the repository;
this zip overlays reports/submission-20261021 in that source tree.
"""
from pathlib import Path
import argparse
import hashlib
import json
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DELIVERABLES = ['Final_Project_Report.pdf', 'Final_Project_Presentation.pptx', 'Final_Project_Presentation.pdf']
REQUIRED = DELIVERABLES + ['README.md', 'EVALUATION.md', 'DEMO_GUIDE.md', 'LIMITATIONS.md', 'SUBMISSION_CHECKLIST.md', 'delivery-status.json', 'asset-validation.json']
EXTERNAL_METADATA = [
    'reports/release-final-20261021/candidate-freeze.json',
    'reports/release-final-20261021/image-probe-final.json',
    'reports/release-final-20261021/qa/evidence-index.json',
    'reports/release-final-20261021/release-manifest.json',
    'reports/release-final-20261021/EVIDENCE_INDEX.md',
    'reports/release-final-20261021/ROLLBACK_FINAL.md',
]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', default=str(ROOT / 'dist/submission-20261021'))
    args = parser.parse_args()
    output = Path(args.output_directory).resolve()
    if not output.is_relative_to((ROOT / 'dist/submission-20261021').resolve()):
        raise SystemExit('Archive output must stay inside ignored dist/submission-20261021/.')
    for name in REQUIRED:
        if not (BASE / name).is_file():
            raise SystemExit('Missing required deliverable: ' + name)
    validation = json.loads((BASE / 'asset-validation.json').read_text())
    if validation.get('status') != 'PASS' or validation.get('source_export_provenance', {}).get('status') != 'PASS':
        raise SystemExit('Asset validation is not PASS; rebuild or report the error.')
    checked = json.loads((BASE / 'DELIVERABLES_SHA256.json').read_text())
    for name in DELIVERABLES:
        digest = sha((BASE / name).read_bytes())
        if checked.get(name) != digest:
            raise SystemExit('Deliverable changed after validation: ' + name)
        pdf_receipt = validation.get('pdf', {}).get(name, {})
        receipt_hash = pdf_receipt.get('sha256') if name.endswith('.pdf') else validation.get('pptx', {}).get('sha256')
        if receipt_hash != digest:
            raise SystemExit('Validation receipt/hash mismatch: ' + name)
    build_path = BASE / 'build-source-identity.json'
    build = json.loads(build_path.read_text())
    if sha(build_path.read_bytes()) != validation['source_export_provenance']['build_source_identity_sha256']:
        raise SystemExit('Build changed after validation.')
    for name, expected in {**build['inputs_sha256'], **build['generated_sha256']}.items():
        if sha((BASE / name).read_bytes()) != expected:
            raise SystemExit('Source/asset changed after validation: ' + name)
    status = json.loads((BASE / 'delivery-status.json').read_text())
    contents = {}
    for path in sorted(BASE.iterdir()):
        if not path.is_file() or path.is_symlink():
            continue
        if path.name in {'submission-package-manifest.json', 'pdf-text-bounds.json'}:
            continue
        if path.suffix in {'.md', '.html', '.json', '.py', '.cjs', '.txt'} or path.name in DELIVERABLES:
            contents[str(path.relative_to(ROOT))] = path.read_bytes()
    for rel in EXTERNAL_METADATA:
        path = ROOT / rel
        if path.is_file():
            contents[rel] = path.read_bytes()
    start = f'''# Gói nộp Hanoi Land Law Assistant\n\nCode candidate: {status.get('candidate_code_sha', 'NOT CONFIRMED')}\nMode: SOURCE_LOOKUP_ONLY=true; GENERATION_ENABLED=false.\nDeployment: {status.get('deployment', 'NOT VERIFIED')}\nCI: {status.get('ci', 'NOT TESTED')}\n\nMở reports/submission-20261021/README.md, PDF và PPTX.\nGói này gồm tài liệu và metadata gọn, không thay source release/corpus/model assets.\nĐể các liên kết evidence đầy đủ, giải nén overlay vào đúng repository/source release được cung cấp riêng.\nKhông có credentials, database, production backup hoặc toàn bộ corpus trong ZIP học thuật.\nS06 FAIL; C01 INCOMPLETE; C02/C03 NOT RUN Phase 3A. C02 allocation mới INCOMPLETE.\nRetrieval Recall@5 97,37% không phải legal-answer accuracy.\n'''
    contents['START_HERE.md'] = start.encode()
    manifest = {
        'format': 1,
        'scope': 'Academic documents and minimal evidence metadata; not deployment or corpus/model package',
        'candidate_code_sha': status.get('candidate_code_sha'),
        'delivery_status': status,
        'content_sha256': {name: sha(data) for name, data in sorted(contents.items())},
        'self_hash_excluded': 'This manifest is generated from the other archived contents; it does not hash itself.',
        'reproducibility': 'Fixed ZIP timestamp, sorted paths and DEFLATE level9. PDF bytes reflect the actual final Chromium export.',
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    manifest_sha = sha(manifest_bytes)
    manifest_path = BASE / 'submission-package-manifest.json'
    manifest_path.write_bytes(manifest_bytes)
    contents[str(manifest_path.relative_to(ROOT))] = manifest_bytes
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'Final_Submission_Package_{manifest_sha[:12]}.zip'
    if archive.exists():
        raise SystemExit('Archive exists; keep it and choose another output directory or verify the existing bytes.')
    with ZipFile(archive, 'x', compression=ZIP_DEFLATED, compresslevel=9) as handle:
        for name, data in sorted(contents.items()):
            info = ZipInfo(name, date_time=(2026, 10, 21, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            handle.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(archive) as handle:
        if handle.testzip():
            raise SystemExit('ZIP integrity failure.')
        for name, digest in manifest['content_sha256'].items():
            if sha(handle.read(name)) != digest:
                raise SystemExit('ZIP member hash mismatch: ' + name)
    checksum = archive.with_suffix('.zip.sha256')
    checksum.write_text(f'{sha(archive.read_bytes())}  {archive.name}\n')
    print(json.dumps({'archive': str(archive), 'members': len(contents), 'sha256': sha(archive.read_bytes()), 'status': 'PASS_ARCHIVE_INTEGRITY'}, ensure_ascii=False))

if __name__ == '__main__':
    main()
