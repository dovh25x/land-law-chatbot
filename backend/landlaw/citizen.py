"""Bounded citizen interaction and evidence policy within the existing graph.

Templates below only help identify papers/context. They never prescribe a legal
procedure, required document, competent office, entitlement, fee or deadline.
"""
import re
from datetime import timedelta

from pydantic import BaseModel

from .models import CitizenIntent, Clarification
from .security import local_date, normalize, utcnow


class CitizenNeed(BaseModel):
    intent: CitizenIntent = 'orientation'
    document_type: str | None = None
    fact_origin: str | None = None
    general_question: bool = False
    orientation_only: bool = False
    clarification: Clarification | None = None


PAPER_TYPES = [('thong bao thu hoi dat','recovery_notice'),
               ('quyet dinh thu hoi dat','recovery_decision'),
               ('phuong an boi thuong','compensation_plan'),
               ('bien ban kiem ke','inventory_record')]


def paper_type(text):
    text = normalize(text)
    for phrase,value in PAPER_TYPES:
        for match in re.finditer(re.escape(phrase),text):
            clause=re.split(r'[,;.!?\n]|\b(?:nhung|ma|thuc ra)\b',text[:match.start()])[-1]
            if not re.search(r'\b(?:khong phai|chua co|khong co)(?:\s+\w+){0,5}\s*$',clause):
                return value
    return None


def assess_need(message, history):
    text = normalize(message)
    origin, paper = 'current_user', paper_type(message)
    # A current denial/unknown title must not resurrect a superseded history fact.
    correction=bool(re.search(r'\b(?:khong phai|chua co|khong co)\b',text)) or any(
        term in text for term in ('khong ro ten giay','khong biet ten giay','chua ro ten giay'))
    if not paper and not correction:
        origin = 'history_user'
        for item in reversed(history):
            if item['role'] == 'user' and (paper := paper_type(item['content'])):
                break
    need = CitizenNeed(document_type=paper,fact_origin=origin if paper else None)
    need.general_question = any(t in text for t in ('nghia la','la gi','phan biet','giai thich','quy dinh chung','khai niem','duoc hieu the nao'))
    if any(t in text for t in ('noi hoi','lien he','gui cho ai','nop o dau','dia chi','so dien thoai','tim co quan')):
        need.intent='find_contact'
    elif any(t in text for t in ('khieu nai','khong dong y','chua dong y','gop y','muon kien')):
        need.intent='disagreement'
    elif any(t in text for t in ('giay to gi','mang giay','chuan bi giay','ho so gi')):
        need.intent='prepare_documents'
    elif need.general_question:
        need.intent='explain_term'
    elif any(t in text for t in ('ho tro','tai dinh cu','boi thuong','den bu')):
        need.intent='understand_benefit'
    paper_query = any(t in text for t in ('nhan giay','nhan mot to giay','giay toi','ten giay','giay do','giay ve','giay nay'))
    unknown = any(t in text for t in ('khong ro','khong biet','chua ro','khong doc duoc'))
    if paper_query and not need.general_question and not paper:
        need.intent='explain_document'
        need.orientation_only=True
        already_asked = any(item['role']=='assistant' and 'Trên giấy ghi tên nào' in item['content'] for item in history)
        if not (unknown and already_asked):
            need.clarification=Clarification(fact='document_type',
                question='Trên giấy ghi tên nào? Bạn chỉ cần đọc dòng tên, không nhập thông tin cá nhân.',
                options=['Thông báo thu hồi đất','Quyết định thu hồi đất'])
    elif any(t in text for t in ('chua ro minh dang o buoc','khong biet bat dau','chua biet bat dau')) and not paper:
        need.orientation_only=True
        need.clarification=Clarification(fact='stage',question='Bạn đang muốn tìm hiểu việc nào trước?',
            options=['Tôi vừa nhận giấy','Tôi đang xem phương án','Tôi chưa đồng ý nội dung'])
    return need


def clarification_for_missing(facts):
    text=normalize(' '.join(facts))
    if any(t in text for t in ('ngay','thoi diem','chuyen tiep')):
        return Clarification(fact='date',question='Bạn có biết ngày ghi trên quyết định hoặc phương án đang hỏi không? Chỉ nhập ngày, không nhập số hồ sơ.')
    if any(t in text for t in ('dia ban','xa/','xa ','phuong','huyen','vi tri')):
        return Clarification(fact='place',question='Tên xã/phường trong giấy tờ là gì? Chỉ cần tên địa bàn, không nhập số nhà hoặc số thửa.')
    if any(t in text for t in ('loai dat','dat o','giay to')):
        return Clarification(fact='land_type',question='Bạn đang muốn tìm hiểu quy định cho loại đất nào?',
            options=['Đất ở','Đất nông nghiệp','Tôi chưa rõ loại đất'])
    if facts:
        return Clarification(fact='stage',question='Bạn đang ở bước nào trong việc đang hỏi?',
            options=['Vừa nhận giấy','Đang xem phương án','Chưa rõ'])
    return None


def repeated_clarification(question, history, message):
    previous=[m['content'] for m in history if m['role']=='assistant']
    count=sum(question.question in content for content in previous)
    unknown=any(t in normalize(message) for t in ('khong biet','khong ro','chua ro'))
    return count>=2 or (count>=1 and unknown)


def operational_claim(claim):
    return (claim.kind in {'procedure','contact'} or claim.section=='actions'
        or bool(re.search(r'\b(?:phai nop|nop tai|gui den|dia chi lien he|so dien thoai|han cuoi|ho so gom)\b',normalize(claim.text))))


def source_policy_issues(claim, evidence, as_of):
    """Structural source-role/freshness veto; semantic verification still applies."""
    cited=[e for e in evidence if e.chunk.id in claim.citation_ids]
    kinds={e.document.source_kind for e in cited}
    issues=[]
    operational=operational_claim(claim)
    if 'official_directory' in kinds and claim.kind!='contact':
        issues.append('Danh bạ chỉ dùng cho claim liên hệ được rà soát, không làm nguồn bối cảnh hoặc quyền lợi')
    if claim.kind=='contact' and not {'official_directory','official_procedure'} & kinds:
        issues.append('Thiếu nguồn thủ tục/danh bạ đúng chức năng cho đầu mối liên hệ')
    if claim.kind=='procedure' and not {'legal','official_procedure'} & kinds:
        issues.append('Nguồn bối cảnh hoặc danh bạ không chứng minh thủ tục')
    if claim.kind=='legal_rule' and not {'legal','project_decision'} & kinds:
        issues.append('Nguồn thủ tục/danh bạ/tin tức không tự chứng minh quyền hoặc điều kiện pháp lý')
    if operational:
        if as_of>local_date():
            issues.append('Chưa thể xác nhận hướng dẫn tác nghiệp cho thời điểm tương lai')
        if not cited or any(e.document.source_kind=='official_news' for e in cited):
            issues.append('Hướng dẫn tác nghiệp cần nguồn đúng vai trò, không dùng tin dự án')
        now=utcnow()
        for item in cited:
            d=item.document
            if d.source_kind=='official_directory' and as_of!=local_date():
                issues.append('Danh bạ hiện tại không chứng minh kênh liên hệ trong quá khứ hoặc tương lai')
            stamp=d.operational_reviewed_at
            if (d.operational_review_status!='unchanged' or stamp is None or stamp.tzinfo is None
                    or not now-timedelta(days=7)<=stamp<=now):
                issues.append('Nguồn hướng dẫn tác nghiệp chưa có rà soát còn hạn; snapshot override không đủ')
            if d.effective_from and as_of<d.effective_from or d.effective_to and as_of>=d.effective_to:
                issues.append('Nguồn hướng dẫn tác nghiệp không áp dụng tại ngày hỏi')
        selected={e.document.id for e in cited}
        if any(set(e.document.required_dependency_ids)-selected for e in cited):
            issues.append('Thiếu nguồn phụ thuộc để kiểm tra hướng dẫn tác nghiệp')
        if claim.kind=='contact' and re.search(r'\b(nop|gui|giai quyet|tham quyen)\b',normalize(claim.text)) and not {'legal','official_procedure'} & kinds:
            issues.append('Danh bạ không tự chứng minh thẩm quyền nhận hoặc giải quyết hồ sơ')
    return list(dict.fromkeys(issues))
