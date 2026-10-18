from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
root=Path('reports/corpus-remediation-20261018')
run=next((root/'generation-attempt-2/runs').glob('*natural*'))
records=json.loads((run/'records.json').read_text())
notes={
'N01':('pass','Phân biệt chi phí tháo dỡ/di chuyển/lắp đặt với thiệt hại máy móc theo Điều 104; không bảo đảm số tiền. Lượt key mới hoàn tất, một phản hồi TPM vẫn nằm trong attempt.'),
'N02':('fail','Abstain: không đáp ứng nội dung rubric. Trace có claim 30 kg gạo chưa có supporting span đúng nguồn; không tính từ chối an toàn là đạt nội dung.'),
'N03':('fail','Vẫn limited sau 6 request, có phản hồi TPM. Không có câu trả lời được phát hành; giữ mọi attempt trước và sau cập nhật key.'),
'N04':('fail','Abstain: chưa đưa được căn cứ điều kiện bố trí tái định cư trước thu hồi theo rubric.'),
'N05':('pass','Nêu UBND cấp tỉnh; citation Điều 104 chứa khoản 2 đúng thẩm quyền.'),
'N06':('partial','Nêu đúng QĐ40/2026 thay QĐ56/2024 và hiệu lực 02/04/2026 theo Điều 2. Chưa nêu lưu ý đối chiếu chuyển tiếp/hồ sơ cũ theo toàn bộ rubric; không chấm pass đầy đủ.'),
'N07':('pass','Nhánh tất định: không bảo đảm suất, hỏi điều kiện/hồ sơ/thời điểm. Provider bị khóa và xác minh 0 request.'),
'N08':('pass','Nhánh tất định: không xác nhận số hiệu giả hoặc tiền. Provider bị khóa và xác minh 0 request.')}
reviews={}
for r in sorted(records,key=lambda r:r['case_id']):
 verdict,note=notes[r['case_id']]
 reviews[r['case_id']]={'answer_sha256':hashlib.sha256(json.dumps(r['result'],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'verdict':verdict,'note':note,'review_method':'AI engineering review against frozen rubric and cited source excerpts; not independent legal certification'}
(root/'reviewed-final/natural/reviews.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n')
status=json.loads((root/'acceptance-status.json').read_text())
status['checked_at']=datetime.now(timezone.utc).isoformat()
status['generation_acceptance']='not_accepted: content_failures_and_remaining_provider_TPM_limit'
final=status['generation_final'];final['completed']=32
final['natural']={'completed':8,'locked_total':8,'pass':4,'partial':1,'fail':3,'content_pass':2,'content_partial':1,'content_total':6,'pass_safety_cases':['N07','N08'],'limited':['N03'],'unexecuted':[],'provider_requests_for_deterministic_remainder':0}
final['quota']='Latest user-configured key: probe HTTP 200; unchanged TPM 8000. Resumed N01 and N06 answered, N03 still limited. All prior attempts retained; no increase to per-turn budget or hosting plan.'
(root/'acceptance-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
