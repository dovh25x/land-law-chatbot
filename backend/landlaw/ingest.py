import asyncio
import hashlib
import io
import json
import logging
import re
import shutil
import socket
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .config import Settings
from .models import Chunk, Document, Relation
from .provider import Gemini, ProviderUnavailable
from .embedding import contract
from .security import digest, normalize, official_url, public_ip_address, redact, utcnow
from .store import RateLimited

MAX_DOWNLOAD = 25 * 1024 * 1024
logger = logging.getLogger(__name__)


class Quarantine(Exception):
    pass


def json_write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


async def download(client, url, publication_url=None):
    """Allowlisted domains, checked redirects, public DNS, bounded body and explicit timeouts."""
    from urllib.parse import urlparse

    for _ in range(5):
        if not official_url(url, publication_url):
            raise Quarantine("URL outside the official-source allowlist")
        host = urlparse(url).hostname
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, 443)
        if not addresses or any(not public_ip_address(x[4][0]) for x in addresses):
            raise Quarantine("Source DNS contains a private/reserved address")
        async with client.stream("GET", url, follow_redirects=False) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            response.raise_for_status()
            if int(response.headers.get("content-length", "0")) > MAX_DOWNLOAD:
                raise Quarantine("Download exceeds 25 MB")
            content = bytearray()
            async for part in response.aiter_bytes():
                content.extend(part)
                if len(content) > MAX_DOWNLOAD:
                    raise Quarantine("Download exceeds 25 MB")
            return bytes(content), url
    raise Quarantine("Too many redirects")


def html_text(content: bytes, legal=False):
    soup = BeautifulSoup(content, "html.parser")
    for item in soup.select("script,style,nav,header,footer,aside,iframe"):
        item.decompose()
    # ASP.NET portals wrap their entire document in a server form. Preserve its content.
    for item in soup.select("form"):
        item.unwrap()
    for item in soup.select(".related-news,.related-articles,.detail__related,.box-related,.VCSortableInPreviewMode[type='RelatedOneNews']"):
        item.decompose()
    candidates = soup.select("#block_detail.document-detail,#news-bodyhtml,.detail-body,.detail__content,.vbContent,.toanvan,.detail-content,.article-content,.entry-content")
    if not candidates:
        candidates = soup.select("article,main,.content-detail")
    if candidates:
        node = max(candidates, key=lambda n: len(n.get_text()))
    else:
        node = soup.body or soup
    text = node.get_text("\n", strip=True)
    if len(text) < 300 or "dang tai noi dung" in normalize(text[:2000]):
        raise Quarantine("Portal loading shell or no substantive article")
    if legal and not re.search(r"Điều\s+\d+", text, re.IGNORECASE):
        raise Quarantine("Metadata page is not legal full text; PDF attachment required")
    return [(None, text)]


def ocr_page(content: bytes, page_index: int):
    if not shutil.which("tesseract") or not shutil.which("pdftoppm"):
        raise Quarantine("Scanned PDF requires offline Tesseract vie + pdftoppm")
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        pdf = folder / "source.pdf"
        pdf.write_bytes(content)
        subprocess.run(["pdftoppm", "-f", str(page_index + 1), "-l", str(page_index + 1),
                        "-r", "170", "-singlefile", "-png", str(pdf), str(folder / "page")],
                       check=True, timeout=90, capture_output=True)
        result = subprocess.run(["tesseract", str(folder / "page.png"), "stdout", "-l", "vie+eng"],
                                check=True, timeout=90, capture_output=True, text=True)
        return result.stdout


TABLE_MARKER = "[BẢNG / ĐƠN GIÁ — giữ dòng, tiêu đề, đơn vị; đối chiếu trang gốc]"
ARTICLE_HEADING = re.compile(r"^[ \t]*Điều[ \t]+(\d+)(?:[ \t]*[.:]|[ \t]*(?=\n|$))", re.MULTILINE | re.IGNORECASE)


def article_headings(text):
    """Do not turn a wrapped reference ending in 'Điều 65.' into a heading."""
    for match in ARTICLE_HEADING.finditer(text):
        tail = text[match.end():].split('\n', 1)
        if not tail[0].strip():
            following = tail[1].lstrip() if len(tail) > 1 else ''
            preceding = text[:match.start()].rstrip().split('\n')[-1] if match.start() else ''
            punctuated = match[0].rstrip().endswith(('.', ':'))
            if (not following or (punctuated and re.match(r'(?:\d+[.)]|[a-zđ]\))', following))
                    or re.search(r'\btai\s+(?:khoan|diem)\b', normalize(preceding))):
                continue
        yield match


def table_layout(text):
    """A price mentioned in prose is not evidence of a table."""
    lines = text.splitlines()
    columns = [line for line in lines if re.search(r"\S[ \t]{3,}\S", line)]
    if len(columns) < 2:
        return False
    if any(re.search(r"\b(?:STT|TT)\b|Tên đường|Tên phố", line, re.IGNORECASE) for line in columns):
        return True
    numeric_rows = sum(bool(re.search(r"\S[ \t]{3,}\d[\d.,]*(?:[ \t]{3,}|$)", line)) for line in columns)
    return numeric_rows >= 2 and bool(re.search(r"đơn vị tính|đơn giá|mức giá", text, re.IGNORECASE))


def pdf_pages(content: bytes, allow_ocr=False):
    reader = PdfReader(io.BytesIO(content))
    if reader.is_encrypted:
        raise Quarantine("Encrypted PDF")
    if len(reader.pages) > 500:
        raise Quarantine("PDF exceeds 500 pages")
    pages = []
    for index, page in enumerate(reader.pages):
        # Layout extraction keeps table columns aligned. Avoid a quadratic grid search
        # over thousands of price-table cells, which consumes gigabytes offline.
        text = page.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False) or ""
        if len(text.strip()) < 60:
            plain = page.extract_text() or ""
            if len(plain.strip()) >= 60:
                text = plain
            elif not page.images and not re.sub(r"[\d\W_]", "", plain):
                # Truly blank separator/back pages are not failed scans.
                continue
        if len(text.strip()) < 60:
            if not allow_ocr:
                raise Quarantine(f"Page {index+1} requires offline OCR")
            text = ocr_page(content, index)
            if len(text.strip()) < 120 or text.count("�") > 2:
                raise Quarantine(f"Low quality OCR on page {index+1}")
        if table_layout(text):
            text = TABLE_MARKER + "\n" + text
        pages.append((index + 1, text))
    return pages


def chunks_for(doc_id, pages):
    chunks = []
    active_article = None
    appendix = False
    for page_index, (page, text) in enumerate(pages):
        # Reclassify old parse caches too: v4 marked any prose mentioning 'đơn giá'.
        text = redact(text).replace(TABLE_MARKER + "\n", "").strip()
        if "�" in text and text.count("�") / max(len(text), 1) > 0.005:
            raise Quarantine("Encoding/OCR quality insufficient")
        appendix_heading = None if appendix else re.search(r'^\s*PHỤ LỤC\s*$', text, re.MULTILINE | re.IGNORECASE)
        appendix_start = appendix_heading.start() if appendix_heading else None
        main_text = text[:appendix_start] if appendix_start is not None else text
        positions = [] if appendix else [m.start() for m in article_headings(main_text)]
        boundaries = sorted(set([0, *positions, *([appendix_start] if appendix_start is not None else []), len(text)]))
        for section_index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
            if appendix_start is not None and start >= appendix_start:
                active_article, appendix = None, True
            section = text[start:end].strip()
            if len(section) < 30:
                continue
            match = None if appendix else ARTICLE_HEADING.match(section)
            if match:
                active_article = match[1]
            locator = f"Điều {active_article}" if active_article else f"Trang {page}" if page else f"Đoạn {section_index+1}"
            words = section.split()
            # Conservative estimate: Vietnamese words typically span multiple subword tokens.
            if table_layout(section):
                # Preserve whole rows, spacing, units and page headers in price tables.
                # PDF layout may add thousands of padding spaces per row. Keep a
                # column separator, every value and every row; never embed padding.
                lines = [re.sub(r'[ \t]{3,}', '   ', line).rstrip() for line in section.splitlines()]
                first_row = next((i for i, line in enumerate(lines)
                    if i >= 1 and re.match(r"^[ \t]*\d+(?:\.\d+)*[.)]?[ \t]{2,}\S", line)), min(8, len(lines)))
                header_lines = lines[:first_row]
                header = TABLE_MARKER + "\n" + "\n".join(header_lines)
                segments, current, count = [], [], 0
                # A section appears once; subsequent segments repeat only its header.
                for line in lines[first_row:]:
                    size = len(line.split())
                    if current and count + size > 330:
                        segments.append(header + "\n" + "\n".join(current))
                        current, count = [], 0
                    current.append(line)
                    count += size
                if current or not segments:
                    segments.append(header + "\n" + "\n".join(current))
                parent_text = header + "\n" + "\n".join(lines[first_row:first_row+16])
            else:
                segments, start = [], 0
                while start < len(words):
                    end = min(start+330, len(words))
                    if len(words)-end <= 60:
                        end = len(words)
                    segments.append(" ".join(words[start:end]))
                    if end == len(words):
                        break
                    start += 300
                parent_text = " ".join(words[:660])
            parent_id = None
            if len(segments) > 1:
                parent_id = f"{doc_id}-{page_index}-{section_index}-parent"
                # A parent retains headings and enough context without unbounded prompts.
                chunks.append(Chunk(id=parent_id, document_id=doc_id, text=parent_text,
                                    locator=locator + " · ngữ cảnh", page=page, checksum=digest(parent_text)))
            for index, segment in enumerate(segments):
                chunk_id = f"{doc_id}-{page_index}-{section_index}-{index}"
                chunks.append(Chunk(id=chunk_id, document_id=doc_id, text=segment, locator=locator,
                                    page=page, parent_id=parent_id, checksum=digest(segment)))
    if not chunks:
        raise Quarantine("No usable text chunks")
    # Publication headers alone have no rule or context; retain page/locator on
    # substantive passages and preserve their stable IDs/checkpoints.
    allowed_header_words=set('cong bao ha noi so ngay thang nam'.split())
    chunks=[chunk for chunk in chunks if not (len(normalize(chunk.text))<180
        and 'cong bao' in normalize(chunk.text)
        and set(re.findall(r'[a-z]+',normalize(chunk.text)))<=allowed_header_words)]
    if not chunks:raise Quarantine('No substantive text after publication-header removal')
    return chunks


async def collect_source(source, settings, client, offline=False, allow_ocr=False):
    source_id = source["id"]
    if not re.fullmatch(r"[a-z0-9-]+", source_id):
        raise Quarantine("Invalid source ID")
    if not official_url(source["url"], source.get("publication_url")):
        raise Quarantine("Unapproved source URL")
    raw_dir = settings.data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    contents = []
    paths = []
    file_urls = list(source.get('attachment_urls') or [])
    if offline:
        candidates = [Path(p) for p in source.get("raw_paths", [])]
        if not candidates:
            candidates = sorted(raw_dir.glob(f"{source_id}*.pdf")) or [raw_dir / f"{source_id}.html"]
        for path in candidates:
            if not path.resolve().is_relative_to(raw_dir.resolve()):
                raise Quarantine("Raw file path outside data/raw")
            contents.append(path.read_bytes())
            paths.append(path)
    else:
        content, final_url = await download(client, source["url"], source.get("publication_url"))
        if content.startswith(b"%PDF"):
            (raw_dir / f"{source_id}.pdf").write_bytes(content)
            contents.append(content)
            paths.append(raw_dir / f"{source_id}.pdf")
            file_urls = [source['url']]
        else:
            (raw_dir / f"{source_id}.html").write_bytes(content)
            soup = BeautifulSoup(content, "html.parser")
            links = source.get("attachment_urls", [])
            if not links and source["source_kind"] == "legal":
                links = [urljoin(final_url, str(a["href"])) for a in soup.select("a[href]")
                         if ".pdf" in str(a["href"]).lower()][:8]
            if links:
                file_urls = links
                for index, link in enumerate(links):
                    pdf, _ = await download(client, link, source["url"])
                    if not pdf.startswith(b"%PDF"):
                        raise Quarantine("Attachment is not a PDF")
                    (raw_dir / f"{source_id}-{index}.pdf").write_bytes(pdf)
                    contents.append(pdf)
                    paths.append(raw_dir / f"{source_id}-{index}.pdf")
            else:
                contents.append(content)
                paths.append(raw_dir / f"{source_id}.html")
    reviewed_checksums = set(source.get("raw_checksums", {}).values())
    if source.get("review_status") != "verified":
        raise Quarantine("Source full text / legal metadata awaiting review")
    if not reviewed_checksums or any(digest(content) not in reviewed_checksums for content in contents):
        raise Quarantine("Source content changed or has no reviewed checksum; metadata must be reviewed again")
    pages = []
    source_files = []
    for file_index, (path, content) in enumerate(zip(paths, contents, strict=True)):
        first_page_index = len(pages)
        if content.startswith(b"%PDF"):
            sidecar = next((item for item in source.get("ocr_sidecars", []) if item.get("pdf_sha256") == digest(content)), None)
            if sidecar:
                ocr_path = Path(sidecar["ocr_path"])
                if not ocr_path.resolve().is_relative_to(raw_dir.resolve()) or sidecar.get("review_status") != "verified":
                    raise Quarantine("OCR sidecar awaiting quality and numeric review")
                ocr_bytes = ocr_path.read_bytes()
                if digest(ocr_bytes) != sidecar["ocr_sha256"]:
                    raise Quarantine("OCR sidecar checksum mismatch")
                ocr_pages = ocr_bytes.decode("utf-8").split("\f")
                if ocr_pages and not ocr_pages[-1].strip():
                    ocr_pages.pop()
                if len(ocr_pages) != len(PdfReader(io.BytesIO(content)).pages):
                    raise Quarantine("OCR sidecar page count mismatch")
                if any(len(text.strip()) < 60 or text.count("�") > 2 for text in ocr_pages):
                    raise Quarantine("OCR sidecar contains low quality pages")
                pages.extend((index+1, text) for index, text in enumerate(ocr_pages))
            else:
                parse_cache = settings.data_dir / "checkpoints" / f"parse-layout-v4-{digest(content)}.json"
                if parse_cache.exists():
                    pages.extend(json.loads(parse_cache.read_text())["pages"])
                else:
                    parsed = await asyncio.to_thread(pdf_pages, content, allow_ocr)
                    json_write(parse_cache, {"pages": parsed})
                    pages.extend(parsed)
            file_url = (file_urls[file_index] if len(file_urls) == len(contents) else
                        source['url'] if source['url'].split('?')[0].endswith('.pdf') else None)
            if file_url and official_url(file_url, source.get('publication_url') or source['url']):
                source_files.append({'url': file_url, 'checksum': digest(content),
                    'first_page_index': first_page_index, 'last_page_index': len(pages)-1})
        else:
            pages.extend(html_text(content, legal=source["source_kind"] == "legal"))
    if source["source_kind"] == "legal" and not any(re.search(r"Điều\s+\d+", text) for _, text in pages):
        raise Quarantine("Legal full text not identified")
    # Public individual compensation schedules contain names/addresses. Do not publish without explicit review.
    if source.get("contains_personal_data") and source.get("anonymisation_reviewed") is not True:
        raise Quarantine("Individual records require anonymisation review")
    checksum = hashlib.sha256(b"".join(contents)).hexdigest()
    legal_verified = source.get("review_status") == "verified" and bool(source.get("effective_from"))
    doc = Document(id=source_id, title=source["title"], url=source["url"], publication_url=source.get("publication_url"),
        source_kind=source["source_kind"], document_number=source.get("document_number"), issuer=source.get("issuer"),
        jurisdiction=source.get("jurisdiction", "Hanoi"), project=source.get("project"), topics=source.get("topics", []),
        issued_on=source.get("issued_on"), effective_from=source.get("effective_from"), effective_to=source.get("effective_to"),
        applicability_verified=legal_verified,
        provision_validity=source.get("provision_validity", []),
        source_review_notes=source.get('source_review_notes', ''),
        source_files=source_files,
        checked_at=datetime.fromisoformat(source["checked_at"].replace("Z", "+00:00")) if offline else utcnow(), checksum=checksum,
        chunks=chunks_for(source_id, pages))
    return doc


async def embed_pending(provider, pending, title, issues, doc_id):
    """Checkpoint every successful batch, including peers of a throttled request."""
    concurrency, successes, offset = 2, 0, 0
    async def batch_run(batch):
        throttled = False
        for attempt in range(3):
            try:
                vectors = await provider.embed_many([c.text for c, _ in batch], title=title)
                for (chunk, checkpoint), vector in zip(batch, vectors, strict=True):
                    chunk.embedding = vector
                    json_write(checkpoint, {"embedding": vector})
                logger.info('Embedding checkpoint: document=%s items=%d provider=%s',
                            doc_id, len(batch), getattr(getattr(provider, 'settings', None), 'embedding_provider', 'injected-test'))
                return len(batch), throttled
            except RateLimited as exc:
                throttled = True
                if exc.retry_after > 60 or attempt == 2:
                    raise
                await asyncio.sleep(exc.retry_after)
            except ProviderUnavailable as exc:
                if not exc.retryable or attempt == 2:
                    raise
                await asyncio.sleep(exc.retry_after or 2 ** attempt)
    while offset < len(pending):
        batches = [pending[start:start+8] for start in range(offset, min(len(pending),offset+8*concurrency),8)]
        results = await asyncio.gather(*(batch_run(b) for b in batches), return_exceptions=True)
        blocked = False
        for result in results:
            if isinstance(result, BaseException):
                if not isinstance(result, (RateLimited, ProviderUnavailable)):
                    raise result
                issues.append({"id": doc_id, "reason": "Embedding provider blocked; checkpoint resume required",
                    "retry_after": getattr(result, 'retry_after', None), "quota_source": getattr(result, 'source', None),
                    "error_type": type(result).__name__, "quarantined": False})
                blocked = True
            else:
                successes += 1
        if blocked:
            return True
        offset += sum(len(b) for b in batches)
        if any(result[1] for result in results if isinstance(result, tuple)):
            concurrency, successes = max(1, concurrency // 2), 0
        elif successes >= 10:
            concurrency = min(8, concurrency*2)
            successes = 0
    return False


async def build_corpus(settings: Settings, provider: Gemini | None, offline=False, embed=False, allow_ocr=False, cached_embeddings_only=False):
    sources = json.loads((settings.data_dir / "sources.json").read_text())
    relations_path = settings.data_dir / "legal_relations.json"
    relations = json.loads(relations_path.read_text()) if relations_path.exists() else []
    documents, issues = [], []
    seen_checksums = {}
    embedding_blocked = cached_embeddings_only
    async with httpx.AsyncClient(timeout=45, headers={"User-Agent": "HanoiLandLawResearch/0.1 (+official legal corpus demo)"}) as client:
        for source in sources:
            try:
                logger.info('Checking source: document=%s offline=%s', source['id'], offline)
                doc = await collect_source(source, settings, client, offline, allow_ocr)
                if doc.checksum in seen_checksums:
                    raise Quarantine(f"Duplicate body with {seen_checksums[doc.checksum]} (possible portal shell)")
                seen_checksums[doc.checksum] = doc.id
                if embed:
                    if provider is None:
                        raise ProviderUnavailable("Embedding requires configured provider")
                    pending = []
                    for chunk in doc.chunks:
                        key = digest(f"embedding-format-v1:{provider.settings.embedding_model}:{doc.title}:{chunk.checksum}")
                        checkpoint = settings.data_dir / "checkpoints" / f"{key}.json"
                        if checkpoint.exists():
                            chunk.embedding = provider.normalize_vector(json.loads(checkpoint.read_text())["embedding"],settings.embedding_dimensions)
                        else:
                            pending.append((chunk, checkpoint))
                        chunk.embedding_model = provider.settings.embedding_model
                    logger.info('Parsed source: document=%s chunks=%d cached=%d pending=%d',
                                doc.id, len(doc.chunks), len(doc.chunks)-len(pending), len(pending))
                    if not embedding_blocked:
                        embedding_blocked = await embed_pending(provider, pending, doc.title, issues, doc.id)
                    if any(c.embedding is None for c in doc.chunks):
                        issues.append({"id": doc.id, "reason": "Parsed staging document has incomplete embeddings; publication blocked", "quarantined": False})
                item = doc.model_dump(mode="json")
                for raw, chunk in zip(item["chunks"], doc.chunks, strict=True):
                    raw["embedding"] = chunk.embedding
                documents.append(item)
            except (Quarantine, OSError, ValueError, httpx.HTTPError, ProviderUnavailable, RateLimited) as exc:
                # Provider errors have deliberately sanitized messages; download errors are public URLs only.
                issues.append({"id": source["id"], "reason": str(exc), "quarantined": True})
    document_ids = {d["id"] for d in documents}
    valid_relations = [Relation.model_validate(r).model_dump(mode="json") for r in relations
                       if r["source_id"] in document_ids and r["target_id"] in document_ids]
    for relation in relations:
        if relation["source_id"] not in document_ids or relation["target_id"] not in document_ids:
            issues.append({"id": relation["target_id"], "reason": "Relation endpoint missing from corpus", "quarantined": True})
    aliases_path = settings.data_dir / "place_aliases.json"
    aliases = json.loads(aliases_path.read_text()) if aliases_path.exists() else []
    unresolved = [r for r in relations if r['source_id'] not in document_ids or r['target_id'] not in document_ids]
    gaps = [{"document_id":s['id'], "document_number":s.get('document_number'), "title":s['title'],
             "url":s.get('publication_url') or s['url'],
             "reason":"Chưa có toàn văn và metadata đạt kiểm tra; không dùng làm căn cứ."}
            for s in sources if s['id'] not in document_ids]
    embedding_contract = contract(settings)
    content_hash = digest(json.dumps({"documents": documents, "relations": valid_relations,
        "unresolved_relations":unresolved,'coverage_gaps':gaps,'embedding_contract':embedding_contract,
        "place_aliases": aliases, "embedding_model": settings.embedding_model, "parser_version": 13}, sort_keys=True, ensure_ascii=False))[:16]
    payload = {"id": f"corpus-{content_hash}", "checked_at": min((d["checked_at"] for d in documents), default=utcnow().isoformat()), "documents": documents,
               "relations": valid_relations, "place_aliases": aliases, "embedding_model": settings.embedding_model,
               "embedding_dimensions":settings.embedding_dimensions,'embedding_contract':embedding_contract,
               "embedded": bool(documents and all(c.get("embedding") for d in documents for c in d["chunks"])),
               "unresolved_relations":unresolved, "coverage_gaps":gaps}
    report = coverage(payload, issues)
    json_write(settings.data_dir / "staging" / f"{payload['id']}.json", payload)
    json_write(settings.reports_dir / "corpus-coverage.json", report)
    return payload, report


def coverage(payload, issues=None):
    docs = payload["documents"]
    legal = sum(d["source_kind"] == "legal" for d in docs)
    projects = {p: sum(d.get("project") == p for d in docs) for p in ("ring4", "songhong", "olympic")}
    verified = sum(d.get("applicability_verified", False) for d in docs if d["source_kind"] == "legal")
    dimensions = payload.get('embedding_dimensions',768)
    embedded = all(c.get("embedding") and len(c["embedding"]) == dimensions for d in docs for c in d["chunks"])
    mandatory = {"luat-dat-dai-2024", "nd-88-2024", "nd-226-2025", "qd-56-2024-hanoi", "qd-40-2026-hanoi", "nq-52-2025-hanoi"}
    missing = sorted(mandatory - {d["id"] for d in docs})
    return {"release": payload["id"], "documents": len(docs), "legal": legal, "verified_legal": verified,
            "projects": projects, "chunks": sum(len(d["chunks"]) for d in docs), "embedded": bool(docs and embedded),
            "coverage_passed": legal >= 30 and all(n >= 5 for n in projects.values()),
            "missing_mandatory_sources": missing,
            "publication_ready": not missing and legal >= 30 and verified == legal and all(n >= 5 for n in projects.values()) and bool(docs and embedded),
            "issues": issues or [], "checked_at": payload["checked_at"]}
