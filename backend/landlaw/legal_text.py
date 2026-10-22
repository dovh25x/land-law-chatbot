"""Deterministic validation for generated legal references.

This is a rejection guard, not proof of legal correctness. It checks that the
article, paragraph and document identifiers named by a generated sentence exist
in the evidence cited for that sentence, and it flags condition-style claims
whose wording has no observable lexical support in that evidence. The final
semantic judgment remains a human/legal-review step.
"""
import re

from .security import normalize

ARTICLE = re.compile(r"\bdieu\s+(\d+[a-z]?)\b")
CLAUSE = re.compile(r"\bkhoan\s+(\d+[a-z]?)\s+(?:dieu\s+)?(\d+[a-z]?)?")
DOCUMENT = re.compile(
    r"\b(\d{1,4})\s*/\s*(\d{4})\s*/\s*(QH\d+|ND-?CP|TTLT|TT|NQ|QD-?UBND|QD|UBND)\b", re.I)
MARKER = re.compile(r"[\[【]\s*S(\d+)\s*[\]】]", re.I)
CONDITION = re.compile(
    r"\b(dieu kien|phai|neu|khong thuoc|thuoc dien|duoc boi thuong|duoc ho tro|"
    r"duoc bo tri|duoc tai dinh cu|truong hop|co quyen)\b")
ABSOLUTE = re.compile(
    r"\b(chac chan|luon luon|tat ca (?:cac )?truong hop|moi truong hop|"
    r"khong the khong|duoc huong|duoc dam bao)\b")
NEGATION = re.compile(r"(?:khong|chua|chang|kho|chua the|khong the|ko)\s+(?:the\s+)?(?:du\s+)?$")
CONTENT = re.compile(r"[a-z0-9]{3,}")
# Function words only. Legal content words (quy dinh, dieu, khoan, thu hoi,
# boi thuong, ...) must stay in the n-grams or a legitimate paraphrase of a
# source sentence looks unsupported.
GRAM_STOP = {
    'toi', 'cua', 'co', 'la', 'va', 'hay', 'thi', 'ma', 'khi', 'duoc', 'theo',
    'nhung', 'nao', 'nhu', 'voi', 'trong', 'tai', 've', 'cho', 'den', 'tren',
    'mot', 'cac', 'nhieu', 'nay', 'do', 'khong', 'chua', 'luon', 'can', 'con',
    'phai', 'toan', 'bo', 'ngay', 'nam', 'xin', 'giup', 'hay', 'lieu', 'se',
    'da', 'dang', 'hoac', 'vi', 'nen', 'cung', 'sau', 'truoc', 'nguoi', 'xin',
}


def marker_ids(answer: str) -> list[str]:
    """Normalize harmless bracket/spacing variants without judging range."""
    return list(dict.fromkeys(f"S{match.group(1)}" for match in MARKER.finditer(answer or '')))


def _content_ngrams(text: str, size: int = 3) -> set[str]:
    words = [word for word in CONTENT.findall(normalize(text or '')) if word not in GRAM_STOP]
    if len(words) < size:
        return set()
    return {' '.join(words[index:index + size]) for index in range(len(words) - size + 1)}


def _evidence_text(item) -> str:
    return normalize(f"{item.document.document_number or ''} {item.document.title} "
                     f"{item.chunk.locator} {item.chunk.text}")


def _document_number(item) -> str:
    value = normalize(item.document.document_number or '')
    return re.sub(r"[^a-z0-9/]", "", value.replace('đ', 'd'))


def _canonical_document(number: str, year: str, suffix: str) -> str:
    return re.sub(r"[^a-z0-9/]", "", f"{number}/{year}/{suffix}".casefold().replace('đ', 'd'))


def _cited_segments(answer: str) -> list[tuple[str, list[str]]]:
    segments: list[tuple[str, list[str]]] = []
    start = 0
    for span in MARKER.finditer(answer or ''):
        statement = (answer or '')[start:span.start()]
        cited = [f"S{span.group(1)}"]
        if statement.strip():
            segments.append((statement, cited))
        elif segments:
            text, ids = segments[-1]
            segments[-1] = (text, ids + cited)
        start = span.end()
    tail = (answer or '')[start:]
    if tail.strip():
        if segments:
            text, ids = segments[-1]
            segments[-1] = (text + " " + tail, ids)
        else:
            segments.append((tail, []))
    return segments


def reference_issues(answer: str, source_map: dict) -> list[str]:
    """Return identifiers that a cited passage does not support.

    Checks per citation segment, so evidence cited for another sentence cannot
    silently support a different article, paragraph or document number.
    """
    issues: list[str] = []
    for statement, cited in _cited_segments(answer):
        sources = [source_map[key] for key in cited if key in source_map]
        if not sources:
            continue
        evidence = " ".join(_evidence_text(item) for item in sources)
        numbers = {_document_number(item) for item in sources}
        normalized = normalize(statement)
        for article in set(ARTICLE.findall(normalized)):
            if not re.search(rf"\bdieu\s+{re.escape(article)}\b", evidence):
                issues.append(f"Điều {article} không có trong nguồn được dẫn")
        for clause, article in CLAUSE.findall(normalized):
            if not article:
                continue
            if not re.search(rf"(?:^|\s){re.escape(clause)}\.\s", evidence):
                issues.append(f"Khoản {clause} Điều {article} không có trong nguồn được dẫn")
        for number, year, suffix in DOCUMENT.findall(normalized):
            ident = _canonical_document(number, year, suffix)
            if not any(ident == candidate or ident in candidate for candidate in numbers):
                issues.append(f"Văn bản {number}/{year}/{suffix} không được dẫn đúng nguồn")
    return issues


def _fragments(statement: str) -> list[str]:
    parts = re.split(r"[,;()\[\]]|\bva\b|\bhoac\b|\bnhung\b", normalize(statement))
    return [part.strip() for part in parts if part.strip()]


SPECIFIC_CONDITION = (
    'phuong an', 'phe duyet', 'quyet dinh', 'thong bao', 'xac nhan',
    'giay chung nhan', 'so do', 'so hong', 'cu tru', 'vi pham', 'bi cam',
    'thuoc dien', 'cam thu hoi', 'cuong che', 'khoi kien', 'khieu nai',
)


def condition_support_issues(answer: str, source_map: dict) -> list[str]:
    """Flag added procedural/eligibility conditions that the cited passage lacks.

    Citizens frequently paraphrase a source premise; a generic paraphrase of
    "bị thu hồi hết đất ở" must not be rejected. The guard therefore looks for
    specific procedural or qualifying phrases (phương án, phê duyệt, giấy chứng
    nhận, cư trú, vi phạm, ...): if the model adds one of these but the cited
    passage never mentions it, the answer is withheld. This is a rejection
    guard, not proof that the remaining text is legally complete.
    """
    issues: list[str] = []
    for statement, cited in _cited_segments(answer):
        sources = [source_map[key] for key in cited if key in source_map]
        if not sources:
            continue
        evidence = " ".join(_evidence_text(item) for item in sources)
        for fragment in _fragments(statement):
            if not CONDITION.search(fragment):
                continue
            for phrase in SPECIFIC_CONDITION:
                if phrase in fragment and phrase not in evidence:
                    issues.append(f"Điều kiện “{phrase}” không có trong nguồn được dẫn")
                    break
            else:
                continue
            break
    return issues


CONTEXT_ONLY = {'official_news', 'project_decision'}
LEGAL_ASSERTION = re.compile(
    r"\b(duoc boi thuong|boi thuong|duoc ho tro|ho tro on dinh|tai dinh cu|"
    r"duoc bo tri|dieu kien duoc|quyen su dung|duoc huong|duoc dam bao)\b")


def source_role_issues(answer: str, source_map: dict) -> list[str]:
    """Context/project sources must not prove a household entitlement."""
    issues: list[str] = []
    for statement, cited in _cited_segments(answer):
        sources = [source_map[key] for key in cited if key in source_map]
        if not sources or not LEGAL_ASSERTION.search(normalize(statement)):
            continue
        if all((item.document.source_kind or 'legal') in CONTEXT_ONLY for item in sources):
            issues.append("Nguồn bối cảnh/dự án không đủ để chứng minh quyền lợi")
    return issues


def confidence_issues(answer: str) -> list[str]:
    """Reject absolute outcome wording that the product must not publish.

    A negated certainty phrase ("chưa đủ chắc chắn") is a safe clarification
    and must not be treated as an absolute claim.
    """
    normalized = normalize(answer or '')
    for match in ABSOLUTE.finditer(normalized):
        prefix = normalized[max(0, match.start() - 60):match.start()]
        if NEGATION.search(prefix) or re.search(r"\b(?:khong|chua|chang|kho|ko)\b", prefix):
            continue
        return ["Câu trả lời dùng từ ngữ khẳng định tuyệt đối"]
    return []


def validate_answer(answer: str, source_map: dict) -> list[str]:
    """All deterministic release guards in one bounded call."""
    return (reference_issues(answer, source_map) + condition_support_issues(answer, source_map)
            + source_role_issues(answer, source_map) + confidence_issues(answer))
