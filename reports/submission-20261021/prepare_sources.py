"""Adapt immutable Phase 4 prose into a separate academic delivery folder."""
from pathlib import Path
import re, os, json
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OLD = ROOT/'reports/final-submission/2026-10-21'
rename={'EVALUATION_SUMMARY.md':'EVALUATION.md','KNOWN_LIMITATIONS.md':'LIMITATIONS.md','DEMO_SCRIPT.md':'DEMO_GUIDE.md','FINAL_PROJECT_REPORT.md':'Final_Project_Report.md'}
def links(text):
 def sub(m):
  dest=m.group(2)
  if dest.startswith(('http:','https:','#','mailto:')): return m.group(0)
  path,mark,anchor=dest.partition('#')
  target=(OLD/path).resolve()
  if target.parent==OLD and target.name in rename: target=OUT/rename[target.name]
  return f'{m.group(1)}({os.path.relpath(target,OUT)}{mark}{anchor})'
 return re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',sub,text)
for source,target in rename.items():
 text=links((OLD/source).read_text())
 if source=='FINAL_PROJECT_REPORT.md':
  text=text.replace('# BÁO CÁO ĐỒ ÁN CUỐI KỲ — BẢN THẢO','# BÁO CÁO ĐỒ ÁN CUỐI KỲ')
  text=text.replace('Phase 2C/2 D','Phase 2C/2D').replace('Bộsmoke 20 +supplemental 4 +natural 8','Bộ smoke 20 + supplemental 4 + natural 8').replace('citizen-v 2-draft','citizen-v2-draft')
  text=text.replace('Báo cáo Markdown cần được sinh viên chuyển sang định dạng nộp chính thức và kiểm tra lại số trang, hình, mục lục và trích dẫn theo mẫu học phần; không giả định đã có bản PDF/DOCX hoặc bộ slide hoàn chỉnh.','Báo cáo này có bản PDF và slide PPTX/PDF đi kèm. Cần điền thông tin hành chính và đối chiếu mẫu học phần trước khi nộp; việc xuất file không xác nhận đã đáp ứng rubric chưa được cung cấp.')
  # The release chronology is described as an evidence cutoff, not a claim about later deployment.
  text=text.replace('Candidate chưa commit và chưa deploy trong các phase cuối.','Tại mốc bằng chứng Phase 4, candidate chưa commit và chưa deploy; trạng thái phát hành sau mốc này được ghi trong phụ lục cập nhật cuối báo cáo.')
  text=text.replace('các bản vá vẫn ở working tree. Freeze manifest riêng mô tả source tree sau packaging, dependency locks và trạng thái candidate_commit=null.','các bản vá tại mốc Phase 4 vẫn ở working tree. Freeze manifest Phase 4 mô tả source tree sau packaging, dependency locks và trạng thái candidate_commit=null tại mốc đó. Trạng thái phát hành cập nhật được tách riêng ở phụ lục cuối.')
 (OUT/target).write_text(text)
status=OUT/'delivery-status.json'
if not status.exists():
 status.write_text(json.dumps({'as_of_vietnam':'2026-10-21','release_sha':None,'branch':None,'push':'PENDING','ci':'NOT TESTED','deployment':'NOT VERIFIED','public_e2e':'NOT TESTED','c02_new_pilot':'NOT RUN','c02_evidence':None,'release_manifest':None,'notes':'Trạng thái Phase 4 được giữ riêng; cập nhật chỉ khi có bằng chứng từ release owner.'},ensure_ascii=False,indent=2)+'\n')
