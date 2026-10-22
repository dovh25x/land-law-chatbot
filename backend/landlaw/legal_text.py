"""Deterministic validation for generated legal references.

This is a rejection guard, not proof of legal correctness. It checks that the
article, paragraph and document identifiers named by a generated sentence exist
in the evidence cited for that sentence, and it flags condition-style claims
whose wording has no observable lexical support in that evidence. The final
semantic judgment remains a human/legal-review step.
"""
from dataclasses import dataclass
import re

from .security import normalize

ARTICLE = re.compile(r"\bdieu\s+(\d+[a-z]?)\b")
CLAUSE = re.compile(r"\bkhoan\s+(\d+[a-z]?)\s+(?:dieu\s+)?(\d+[a-z]?)?")
DOCUMENT = re.compile(
    r"\b(\d{1,4})\s*/\s*(\d{4})\s*/\s*(QH\d+|ND-?CP|TTLT|TT|NQ|QD-?UBND|QD|UBND)\b", re.I)
# A marker group may contain several adjacent IDs, e.g. "[S1, S2]" or
# "【S1】【S2】". Both are common harmless renderings of the documented format.
MARKER = re.compile(
    r"[\[【]\s*(S\d+(?:\s*[,;]\s*S\d+)*)\s*[\]】]", re.I)
MARKER_ID = re.compile(r"S(\d+)", re.I)
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


@dataclass(frozen=True)
class ValidationResult:
    """Internal, redacted outcome of deterministic answer validation.

    The public API never exposes this structure. Callers may copy only fixed
    reason codes into trace diagnostics; answer text and evidence excerpts stay
    out of logs.
    """
    valid: bool
    reason_codes: tuple[str, ...]
    issues: tuple[str, ...]
    cited: tuple[str, ...]
    unknown: tuple[str, ...]
    claim_sentences: int
    uncited_claims: int
    clarification_only: bool


def _marker_groups(answer: str):
    """Yield (start, end, ids) for each recognized citation group."""
    for match in MARKER.finditer(answer or ''):
        ids = tuple(f"S{identifier.group(1)}" for identifier in MARKER_ID.finditer(match.group(1)))
        if ids:
            yield match.start(), match.end(), ids


def marker_ids(answer: str) -> list[str]:
    """Normalize harmless bracket/spacing variants without judging range."""
    found = [identifier for _, _, ids in _marker_groups(answer) for identifier in ids]
    return list(dict.fromkeys(found))


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
    for group_start, group_end, ids in _marker_groups(answer):
        statement = (answer or '')[start:group_start]
        if statement.strip():
            segments.append((statement, list(ids)))
        elif segments:
            text, previous = segments[-1]
            segments[-1] = (text, previous + list(ids))
        start = group_end
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
        # A follow-up question may sit in the same citation segment as the
        # grounded explanation. Asking whether a document exists is not an
        # added legal condition, so only claim-bearing sentences are checked.
        for sentence in _answer_sentences(statement):
            if '?' in sentence:
                continue
            for fragment in _fragments(sentence):
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
        if not sources:
            continue
        claims = [sentence for sentence in _answer_sentences(statement) if '?' not in sentence]
        if not any(LEGAL_ASSERTION.search(normalize(sentence)) for sentence in claims):
            continue
        if all((item.document.source_kind or 'legal') in CONTEXT_ONLY for item in sources):
            issues.append("Nguồn bối cảnh/dự án không đủ để chứng minh quyền lợi")
    return issues


def confidence_issues(answer: str) -> list[str]:
    """Reject absolute outcome wording that the product must not publish.

    A negated certainty phrase ("chưa đủ chắc chắn") is a safe clarification
    and must not be treated as an absolute claim. A question asking whether a
    right applies is not an assertion either, so it is checked sentence-wise
    and skipped when it is interrogative.
    """
    for sentence in _answer_sentences(answer or ''):
        if '?' in sentence:
            continue
        normalized = normalize(sentence)
        for match in ABSOLUTE.finditer(normalized):
            prefix = normalized[max(0, match.start() - 60):match.start()]
            if NEGATION.search(prefix) or re.search(r"\b(?:khong|chua|chang|kho|ko)\b", prefix):
                continue
            return ["Câu trả lời dùng từ ngữ khẳng định tuyệt đối"]
    return []


# A legal proposition signal is intentionally narrower than the general
# CONDITION regex. It lets a genuine clarification ("Bạn đã nhận quyết định
# thu hồi đất chưa?") pass without a citation, while still catching an uncited
# assertion ("Hộ có sổ đỏ được bồi thường.") as a substantive legal claim.
CLAIM_SIGNAL = re.compile(
    r"\b(?:duoc|khong duoc)\s+(?:boi thuong|ho tro|bo tri|tai dinh cu|huong|dam bao)\b|"
    r"\b(?:co|khong co)\s+(?:quyen|nghia vu)\b|"
    r"\b(?:phai|khong phai)\b|"
    r"\b(?:du|khong du)\s+dieu kien\b|"
    r"\bdieu kien\s+(?:duoc|de|ap dung)\b|"
    r"\bthuoc\s+(?:dien|truong hop)\b|"
    r"\b(?:ap dung|khong ap dung)\b|"
    r"\b(?:theo|tai)\s+(?:dieu|khoan)\b|"
    r"\bquy dinh tai\b|"
    r"\bphap luat quy dinh\b|"
    r"\bnha nuoc thu hoi\b|"
    r"\b(?:bi|duoc)\s+thu hoi\b|"
    r"\b(?:muc|so tien|ty le)\s+(?:boi thuong|ho tro)\b|"
    r"\b(?:ho tro|boi thuong|tai dinh cu)\s+(?:on dinh|thiet hai|chi phi|bang|theo|duoc|la|gom|bao gom|tai cho)\b|"
    r"\b(?:thoi han|gia dat)\s+(?:boi thuong|ho tro|tai dinh cu)\b"
)
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def _answer_sentences(answer: str) -> list[str]:
    units = [unit.strip() for unit in SENTENCE.split(answer or '') if unit.strip()]
    merged: list[str] = []
    only_marker = re.compile(
        r"^[\s\-–—*•]*(?:" + MARKER.pattern + r"[\s\-–—*•]*)+$", re.I)
    for unit in units:
        if only_marker.fullmatch(unit) and merged:
            merged[-1] += " " + unit
        else:
            merged.append(unit)
    return merged


def _claim_counts(answer: str) -> tuple[int, int]:
    claims = uncited = 0
    for sentence in _answer_sentences(answer):
        if '?' in sentence:
            continue
        normalized = normalize(sentence)
        if not (CLAIM_SIGNAL.search(normalized) or ARTICLE.search(normalized)
                or DOCUMENT.search(normalized)):
            continue
        claims += 1
        if not marker_ids(sentence):
            uncited += 1
    return claims, uncited


def validate_answer_result(answer: str, source_map: dict[str, object],
                           clarification_question: str = "") -> ValidationResult:
    """Validate a model draft without requiring a citation for pure questions.

    A substantive legal assertion still needs a recognized, in-range marker for
    the sentence that makes the assertion. A clarification-only draft carries
    no such assertion and is therefore allowed to have zero markers. This is a
    narrow contract, not a general relaxation of ``validate_answer``: unknown
    IDs, unsupported references/conditions and context-only proof remain
    rejection reasons.
    """
    cited = tuple(marker_ids(answer))
    unknown = tuple(identifier for identifier in cited if identifier not in source_map)
    refs = tuple(reference_issues(answer, source_map))
    conditions = tuple(condition_support_issues(answer, source_map))
    roles = tuple(source_role_issues(answer, source_map))
    confidence = tuple(confidence_issues(answer))
    issues = tuple(dict.fromkeys(refs + conditions + roles + confidence))
    claims, uncited = _claim_counts(answer)
    reason_codes: list[str] = []
    if uncited:
        reason_codes.append('missing_required_citation')
    if unknown:
        reason_codes.append('unknown_citation_id')
    if refs:
        reason_codes.append('reference_identity_mismatch')
    if conditions:
        reason_codes.append('unsupported_legal_condition')
    if roles:
        reason_codes.append('invalid_claim_grounding')
    if confidence:
        reason_codes.append('unsupported_legal_claim')
    valid = not reason_codes
    if valid:
        has_question = '?' in (answer or '') or '?' in (clarification_question or '')
        if claims:
            reason_codes.append('grounded_answer')
        elif has_question:
            reason_codes.append('legitimate_clarification')
        else:
            reason_codes.append('claim_free_response')
    return ValidationResult(
        valid=valid,
        reason_codes=tuple(reason_codes),
        issues=issues,
        cited=cited,
        unknown=unknown,
        claim_sentences=claims,
        uncited_claims=uncited,
        clarification_only=claims == 0,
    )


def validate_answer(answer: str, source_map: dict) -> list[str]:
    """All deterministic release guards in one bounded call."""
    return (reference_issues(answer, source_map) + condition_support_issues(answer, source_map)
            + source_role_issues(answer, source_map) + confidence_issues(answer))
