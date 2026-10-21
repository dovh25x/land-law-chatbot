"""Source applicability and citation-link helpers shared by runtime paths."""

import re
from datetime import date, timedelta

from .models import Document
from .security import normalize, utcnow


def applicability(doc: Document, as_of: date, chunk=None):
    if doc.source_kind == "official_news":
        return "context"
    if doc.source_kind in {"official_procedure", "official_directory"}:
        if (
            doc.operational_review_status != "unchanged"
            or not doc.operational_reviewed_at
            or doc.operational_reviewed_at.tzinfo is None
            or not utcnow() - timedelta(days=7) <= doc.operational_reviewed_at <= utcnow()
        ):
            return "unverified"
        return "context"
    if not doc.applicability_verified:
        return "unverified"
    if chunk:
        for scope in doc.provision_validity:
            ends = scope.get("effective_to")
            if (
                ends
                and as_of >= date.fromisoformat(ends)
                and "bang gia" in normalize(scope.get("locator", ""))
                and "[BẢNG / ĐƠN GIÁ" in chunk.text
            ):
                return "historical"
            numbers = re.findall(r"Điều\s+(\d+[a-z]?)", scope.get("locator", ""), flags=re.IGNORECASE)
            if any(re.search(rf"^Điều {n}(?:\s|$)", chunk.locator, re.IGNORECASE) for n in numbers):
                starts, ends = scope.get("effective_from"), scope.get("effective_to")
                if (
                    (starts and doc.effective_from and date.fromisoformat(starts) != doc.effective_from)
                    or (ends and as_of >= date.fromisoformat(ends))
                ):
                    return "provision_specific"
    if doc.effective_from and as_of < doc.effective_from:
        return "future"
    if doc.effective_to and as_of >= doc.effective_to:
        return "historical"
    return "current"


def citation_source_url(item):
    """Link a physical page only when its exact source attachment is known."""
    prefix = item.document.id + "-"
    if not item.chunk.id.startswith(prefix) or not item.chunk.page:
        return None
    index = item.chunk.id[len(prefix):].split("-", 1)[0]
    if not index.isdigit():
        return None
    for source in item.document.source_pages:
        if source.page_index == int(index):
            return str(source.url)
    for source in item.document.source_files:
        if source.first_page_index <= int(index) <= source.last_page_index:
            return str(source.url).split("#")[0] + f"#page={item.chunk.page}"
    return None
