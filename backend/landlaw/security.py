import hashlib
import hmac
import ipaddress
import re
import secrets
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


def local_date():
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


def utcnow():
    return datetime.now(timezone.utc)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower().replace("đ", "d"))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_ip(ip: str, secret: str) -> str:
    return hmac.new(secret.encode(), ip.encode(), hashlib.sha256).hexdigest()


def redact(text: str) -> str:
    """Conservative pattern redaction; not a guarantee of anonymisation."""
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL ĐÃ ẨN]", text)
    def phone(match):
        value=match[0]
        digits=re.sub(r'\D','',value)
        length=len(digits)
        valid=length in ({11,12} if value.startswith('+84') else {10,11})
        # Numeric legal dates (including a following PDF page number) are not contacts.
        date_like=re.search(r'\b\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*(?:19|20)\d{2}\b',value)
        return '[SỐ LIÊN HỆ ĐÃ ẨN]' if valid and not date_like else value
    text = re.sub(r"(?<!\d)(?:\+84|0)[\d .-]{8,14}\d(?!\d)", phone, text)
    text = re.sub(r"(?<!\d)\d{12}(?!\d)", "[ĐỊNH DANH ĐÃ ẨN]", text)
    return text


def official_url(url: str, publication_url: str | None = None) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
        return False
    if host in {"dichvucong.gov.vn", "thutuc.dichvucong.gov.vn", "vbpl.vn", "vbpl.moj.gov.vn", "vanban.chinhphu.vn", "congbao.chinhphu.vn",
                "datafiles.chinhphu.vn", "xaydungchinhsach.chinhphu.vn", "baochinhphu.vn"}:
        return True
    if host == "hanoi.gov.vn" or host.endswith(".hanoi.gov.vn"):
        return True
    if host == 'storage-vnportal.vnpt.vn':
        return bool(parsed.path.startswith('/gov-hni/') and publication_url and official_url(publication_url))
    return bool(host in {"sqhx-hanoi.mediacdn.vn", "congbaocdn.chinhphu.vn", "g7.cdnchinhphu.vn", "xdcs.cdnchinhphu.vn"}
                and publication_url and official_url(publication_url))


def public_ip_address(ip: str) -> bool:
    address = ipaddress.ip_address(ip)
    return address.is_global
