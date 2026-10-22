"""Deterministic conversational intents that run before legal retrieval.

The classifier is deliberately narrow. Social phrases are matched as complete
utterances after removing a leading greeting, while legal questions require a
recognisable land-law signal. This prevents a friendly sentence such as "Bạn có
thể giúp gì?" from becoming a legal query, without turning real questions such
as "Bạn có thể giúp tôi xác định điều kiện bồi thường không?" into small talk.
"""

from dataclasses import dataclass
import re
from typing import Literal

from .security import normalize


IntentKind = Literal[
    "greeting", "identity", "capabilities", "gratitude", "farewell",
    "out_of_scope", "legal", "ambiguous",
]


@dataclass(frozen=True)
class ConversationalIntent:
    kind: IntentKind
    reply: str
    reason: str


GREETING_REPLY = (
    "Xin chào! Mình là trợ lý AI hỗ trợ tra cứu pháp luật đất đai liên quan "
    "đến dự án Vành đai 4 Hà Nội. Bạn đang quan tâm đến bồi thường, hỗ trợ "
    "hay tái định cư?"
)
IDENTITY_REPLY = (
    "Mình là trợ lý AI hỗ trợ tìm hiểu pháp luật đất đai liên quan đến dự án "
    "Vành đai 4 Hà Nội. Mình có thể giúp bạn tra cứu thông tin về thu hồi đất, "
    "bồi thường, hỗ trợ và tái định cư, kèm nguồn pháp luật để bạn đối chiếu."
)
CAPABILITIES_REPLY = (
    "Mình có thể giải thích các quy định về thu hồi đất, điều kiện bồi thường, "
    "những khoản hỗ trợ có thể áp dụng và vấn đề tái định cư. Bạn có thể mô tả "
    "tình huống của mình, chẳng hạn loại đất, giấy tờ hiện có hoặc lý do thu hồi, "
    "để mình hỗ trợ tra cứu."
)
GRATITUDE_REPLY = (
    "Rất vui được hỗ trợ bạn. Nếu còn tình huống nào cần tra cứu, bạn cứ mô tả "
    "thêm nhé."
)
FAREWELL_REPLY = (
    "Chào bạn nhé. Khi cần tra cứu về bồi thường, hỗ trợ hoặc tái định cư, "
    "bạn quay lại bất cứ lúc nào."
)
OUT_OF_SCOPE_REPLY = (
    "Mình chỉ hỗ trợ các câu hỏi về pháp luật đất đai trong phạm vi dự án "
    "Vành đai 4 Hà Nội. Bạn có thể hỏi về thu hồi đất, bồi thường, hỗ trợ "
    "hoặc tái định cư."
)
AMBIGUOUS_REPLY = (
    "Mình có thể giúp bạn tra cứu quy định về thu hồi đất, bồi thường, hỗ trợ "
    "và tái định cư. Bạn mô tả rõ hơn tình huống, loại đất, giấy tờ đang có "
    "hoặc thời điểm thu hồi để mình tra cứu đúng nguồn nhé."
)

# These are complete-utterance patterns on the accent-free canonical form.
_PREFIX = re.compile(r"^(?:xin chao|chao|hello|hi|hey)(?: ban| ca nha| chatbot| tro ly)?\s+")
_GREETING = re.compile(r"^(?:xin chao|chao|hello|hi|hey)(?: ban| ca nha| chatbot| tro ly)?$")
_IDENTITY = re.compile(
    r"^(?:ban|bot|chatbot|tro ly|assistant)(?: nay)?"
    r"(?: la ai| la gi| ten (?:la )?gi| co phai la ai| la nguoi that| la may"
    r"| gioi thieu(?: ve ban)?| lam duoc gi)(?: vay)?$"
)
_IDENTITY_ALT = re.compile(r"^(?:gioi thieu ve ban|ban la ai vay|ban ten la gi vay)$")
_CAPABILITIES = re.compile(
    r"^(?:ban|bot|chatbot|tro ly)(?: nay)?"
    r"(?: co the giup(?: gi| duoc gi)?(?: cho (?:toi|minh))?(?: khong)?"
    r"| co the lam(?: duoc)? gi(?: cho (?:toi|minh))?"
    r"| lam duoc(?: nhung)? gi"
    r"| giup(?: duoc)? gi(?: cho (?:toi|minh))?"
    r"| dung de lam gi)$"
)
_CAPABILITIES_ALT = re.compile(
    r"^(?:huong dan(?: toi| minh)? su dung|ban giup duoc gi|"
    r"ban co the giup minh khong|chatbot nay dung de lam gi)$"
)
_GRATITUDE = re.compile(
    r"^(?:xin )?(?:cam on|thank you|thanks|tks|thank)(?: nhieu| nhe| a| chi| anh| em| ban){0,3}$"
)
_FAREWELL = re.compile(
    r"^(?:tam biet|chao nhe|chao ban nhe|bye|goodbye|hen gap lai)"
    r"(?: nhieu| nhe| a| ban){0,2}$"
)
_OUT_OF_SCOPE = re.compile(
    r"\b(?:thoi tiet|du bao thoi tiet|chung khoan|gia vang|nau an|mon an|"
    r"lap trinh|viet code|python|javascript|bong da|the thao|tin tuc|"
    r"dich thuat|tieng anh|toan hoc|vay tien|ngan hang|bitcoin|"
    r"tuyen sinh|du lich|suc khoe|thuoc|benh)\b"
)
_FOLLOW_UP = re.compile(
    r"^(?:vay|vay thi|vay neu|the|the thi|the nao|va|con|nhu vay|neu vay|"
    r"truong hop (?:do|nay)|cai (?:do|nay)|dieu (?:do|nay)|van de (?:do|nay)|thi sao)"
)
_AMBIGUOUS = re.compile(
    r"^(?:giup(?: toi| minh)?(?: voi)?|toi can hoi|toi muon hoi|cho hoi|"
    r"tu van(?: cho toi)?|khong biet|toi can giup do|hoi mot chut|"
    r"co the giup(?: toi| minh)?(?: khong)?|ban co the giup(?: toi| minh)?(?: khong)?)$"
)

# Strong Vietnamese terms are checked on the original text so "đặt câu hỏi"
# cannot be mistaken for "đất". Accent-free variants support common typing.
_LEGAL_VI = re.compile(
    r"\b(?:đất|thu hồi|bồi thường|tái định cư|sổ đỏ|sổ hồng|"
    r"giấy chứng nhận|quyền sử dụng|Vành đai|Luật Đất đai|nghị định|"
    r"thông tư|quyết định|điều kiện|thủ tục|hồ sơ|giấy tờ|đền bù|"
    r"giải phóng mặt bằng|quy hoạch|thửa đất|chủ sở hữu|chuyển nhượng|"
    r"tách thửa|hợp thửa|thừa kế|thế chấp|tranh chấp|khiếu nại|"
    r"khởi kiện|cưỡng chế|pháp luật|chính sách|bảng giá|khung giá|"
    r"quy định|bao nhiêu tiền|số tiền|được bao nhiêu|tiền bồi thường|tiền đền bù)\b",
    re.I,
)
_LEGAL_ASCII = re.compile(
    r"\b(?:dat dai|dat o|dat nong nghiep|dat phi nong nghiep|thu hoi dat|"
    r"boi thuong|tai dinh cu|so do|so hong|giay chung nhan|quyen su dung|"
    r"vanh dai|luat dat dai|nghi dinh|thong tu|quyet dinh|dieu kien|"
    r"thu tuc|ho so|giay to|den bu|giai phong mat bang|quy hoach|"
    r"thua dat|chu so huu|chuyen nhuong|tach thua|hop thua|thua ke|"
    r"the chap|tranh chap|khieu nai|khoi kien|cuong che|phap luat|"
    r"chinh sach|bang gia|khung gia|quy dinh|bao nhieu tien|so tien|"
    r"duoc bao nhieu|tien boi thuong|tien den bu)\b"
)
_LEGAL_CONTEXT = re.compile(r"\b(?:dat|nha|nha o|du an|bi lay|lay dat|giai toa)\b")


def _canonical(message: str) -> str:
    """Lowercase, remove diacritics/punctuation and collapse whitespace."""
    text = normalize(message)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return " ".join(text.split())


def _social_body(canonical: str) -> str:
    return _PREFIX.sub("", canonical).strip()


def _has_legal_signal(canonical: str, original: str) -> bool:
    if _LEGAL_VI.search(original) or _LEGAL_ASCII.search(canonical):
        return True
    # Short or unaccented questions often omit "đất". These phrases still make
    # the subject unambiguous without treating every use of "đặt" as legal.
    return bool(re.search(
        r"\b(?:dat|nha)\b.*\b(?:bi lay|thu hoi|den bu|boi thuong|tai dinh cu)\b",
        canonical,
    ))


def classify(message: str, history=()) -> ConversationalIntent:
    canonical = _canonical(message)
    social = _social_body(canonical)
    original = message.casefold()
    if not canonical:
        return ConversationalIntent("ambiguous", AMBIGUOUS_REPLY, "Empty request")
    if _IDENTITY.fullmatch(social) or _IDENTITY_ALT.fullmatch(social):
        return ConversationalIntent("identity", IDENTITY_REPLY, "Assistant identity")
    if _CAPABILITIES.fullmatch(social) or _CAPABILITIES_ALT.fullmatch(social):
        return ConversationalIntent("capabilities", CAPABILITIES_REPLY, "Assistant capabilities")
    if _GRATITUDE.fullmatch(social):
        return ConversationalIntent("gratitude", GRATITUDE_REPLY, "Gratitude")
    if _FAREWELL.fullmatch(social):
        return ConversationalIntent("farewell", FAREWELL_REPLY, "Farewell")
    if _GREETING.fullmatch(canonical):
        return ConversationalIntent("greeting", GREETING_REPLY, "Greeting")
    # A land-law signal must win over a generic topic word ("ngân hàng",
    # "tin tức", ...) so a real legal question cannot bypass retrieval.
    if _has_legal_signal(canonical, original):
        return ConversationalIntent("legal", "", "Legal question")
    if _OUT_OF_SCOPE.search(canonical):
        return ConversationalIntent("out_of_scope", OUT_OF_SCOPE_REPLY, "Out of scope")
    previous = ""
    for item in reversed(list(history or ())):
        role = item.get("role") if isinstance(item, dict) else getattr(item, "role", None)
        if role == "user":
            previous = item.get("content", "") if isinstance(item, dict) else item.content
            break
    if _FOLLOW_UP.search(social) and previous and _has_legal_signal(
            _canonical(previous), previous.casefold()):
        return ConversationalIntent("legal", "", "Legal follow-up")
    if _AMBIGUOUS.fullmatch(social) or len(canonical.split()) <= 4:
        return ConversationalIntent("ambiguous", AMBIGUOUS_REPLY, "Ambiguous request")
    return ConversationalIntent("ambiguous", AMBIGUOUS_REPLY, "Ambiguous request")


_CONTINUATION = re.compile(
    r"^(?:vay|vay thi|vay neu|the|the thi|the nao|va|con|nhu vay|neu vay|"
    r"truong hop (?:do|nay)|cai (?:do|nay)|dieu (?:do|nay)|van de (?:do|nay)|"
    r"thi sao|nhung|ma|dat toi|nha toi)\b")
_NEW_TOPIC = re.compile(
    r"\b(khieu nai|khoi kien|thu tuc|ho so|giay to|bang gia|khung gia|"
    r"thua ke|tach thua|hop thua|chuyen nhuong|tranh chap|the chap|cuong che)\b")


def contextual_retrieval_query(message: str, history=()) -> tuple[str, bool]:
    """Resolve short/contextual follow-ups for retrieval.

    A short continuation or an explicit follow-up opener inherits the previous
    legal user question so references such as "đất tôi ở thuộc dự án Vành đai 4"
    or "vậy nếu chưa có sổ đỏ?" keep their subject. A new-topic keyword keeps the
    message standalone, and no user facts are inferred.
    """
    text = (message or '').strip()
    canonical = _canonical(text)
    previous = ''
    for item in reversed(list(history or ())):
        role = item.get('role') if isinstance(item, dict) else getattr(item, 'role', None)
        content = item.get('content', '') if isinstance(item, dict) else getattr(item, 'content', '')
        if role == 'user' and isinstance(content, str) and content.strip():
            previous = content.strip()
            break
    if not previous or not _has_legal_signal(_canonical(previous), previous.casefold()):
        return text, False
    if not _CONTINUATION.search(canonical):
        return text, False
    if _NEW_TOPIC.search(canonical) and not _CONTINUATION.search(canonical):
        return text, False
    return f"{previous[:600]} — {text}", True
