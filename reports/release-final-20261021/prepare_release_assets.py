"""Stage immutable public release assets after academic and browser QA; no network."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

root=Path('reports/release-final-20261021')
submission=Path('reports/submission-20261021')
out=Path('dist/academic-release-20261021')
if out.exists():
    raise ValueError('Preserve previous release assets; choose a new release identifier')
manifest=json.loads((root/'release-manifest.json').read_text())
assert manifest['decision']=='READY_FOR_RESTRICTED_SOURCE_LOOKUP'
validation=json.loads((submission/'asset-validation.json').read_text())
# The academic packager enforces build/export provenance separately.
package_manifest=json.loads((Path('dist/submission-20261021')/'package-result.json').read_text())
package=Path(package_manifest['archive'])
assert hashlib.sha256(package.read_bytes()).hexdigest()==package_manifest['sha256']
out.mkdir(parents=True)
for name in ('Final_Project_Report.pdf','Final_Project_Presentation.pptx','Final_Project_Presentation.pdf'):
    shutil.copyfile(submission/name,out/name)
shutil.copyfile(package,out/package.name)
shutil.copyfile('dist/final-corpus-release-20261021/corpus-backup.json',out/'corpus-backup.json')
shutil.copyfile('dist/final-corpus-release-20261021/manifest.json',out/'corpus-manifest.json')
shutil.copyfile(root/'release-manifest.json',out/'release-manifest.json')
shutil.copyfile(root/'EVIDENCE_INDEX.md',out/'EVIDENCE_INDEX.md')
legal=Path('reports/phase2c-current-20261021')
with zipfile.ZipFile(out/'legal-source-receipts.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
    for path in [legal/'source-gate-final.json',*sorted((legal/'receipts-final').glob('*.json'))]:
        archive.write(path,str(path))
(out/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in sorted(out.iterdir()) if p.is_file()))
print(json.dumps({'status':'PREPARED_NOT_PUBLISHED','directory':str(out),'assets':sorted(p.name for p in out.iterdir()),'report_pages':validation['pdf']['Final_Project_Report.pdf']['pages']}))
