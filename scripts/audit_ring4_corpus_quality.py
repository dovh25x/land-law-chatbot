"""Read-only Ring Road 4 corpus/relevance audit.

Produces the required QA deliverables without touching PostgreSQL, the serving
release or any source-review receipt:

- reports/qa/ring4-corpus-quality.md
- reports/qa/ring4-coverage-matrix.json

The A–F classification is an evidence-based review aid. It does not certify a
document or provision as legally current, and it never promotes a review.
"""
import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 10, 22)

# A — core applicable law, B — Ring4 project authority, C — official context,
# D — historical/transitional, E — unrelated/unsuitable, F — needs verification.
CATEGORY = {
    'luat-dat-dai-2024': 'A',
    'luat-43-2024': 'A',
    'luat-thu-do-2026': 'A',
    'nd-226-2025': 'A',
    'nd-49-2026': 'A',
    'nd-88-2024': 'A',
    'nq-254-2025': 'A',
    'qd-40-2026-hanoi': 'A',
    'ring4-nq56-2022': 'B',
    'ring4-hadong-2025': 'C',
    'ring4-hotro-2025': 'C',
    'ring4-phuluong-2025': 'C',
    'ring4-trienkhai-2022': 'C',
    'luat-dat-dai-2013': 'D',
    'luat-quy-hoach-2017': 'D',
    'luat-thu-do-2024': 'D',
    'nd-06-2020': 'D',
    'nd-47-2014': 'D',
    'nd-151-2025': 'D',
    'qd-10-2026-hanoi': 'D',
    'qd-20-2022-hanoi': 'D',
    'qd-27-2024-hanoi': 'D',
    'qd-38-2025-hanoi': 'D',
    'qd-56-2024-hanoi': 'D',
    'qd-566-2026-hanoi': 'D',
    'luat-nha-o-2023': 'F',
    'luat-quy-hoach-2025': 'F',
    'luat-quy-hoach-do-thi-2024': 'F',
    'luat-khieu-nai-2011': 'F',
    'nd-124-2020': 'F',
    'luat-136-2025': 'F',
    'nd-101-2024': 'F',
    'nd-102-2024': 'F',
    'nd-103-2024': 'F',
    'nd-104-2024': 'F',
    'nd-71-2024': 'F',
    'nd-141-2025': 'F',
    'nd-155-2026': 'F',
    'nd-178-2025': 'F',
    'nq-258-2025': 'F',
    'nq-90-2026-hanoi': 'F',
    'nq-52-2025-hanoi': 'F',
    'qd-40-2025-hanoi': 'F',
    'qd-55-2024-hanoi': 'F',
    'qd-61-2024-hanoi': 'F',
    'qd-71-2024-hanoi': 'F',
    'qd-89-2025-hanoi': 'F',
    'qd-19-2026-hanoi': 'F',
    'luat-35-2018': 'F',
    'luat-58-2024': 'F',
    'luat-71-2025': 'F',
    'luat-84-2025': 'F',
    'luat-93-2025': 'F',
    'luat-95-2025': 'F',
    'luat-116-2025': 'F',
    'luat-130-2025': 'F',
    'luat-142-2025': 'F',
    'luat-144-2025': 'F',
    'luat-146-2025': 'F',
    'luat-147-2025': 'F',
}
JUSTIFICATION = {
    'A': 'Văn bản trung tâm đã có receipt/review và được phép dùng làm căn cứ khi đoạn tương ứng còn hiệu lực theo policy.',
    'B': 'Văn bản pháp lý của dự án Vành đai 4; có thể giải thích phạm vi dự án, không tự chứng minh quyền lợi của hộ.',
    'C': 'Tin/progress chính thức; chỉ là bối cảnh, không dùng để chứng minh quyền lợi hoặc thửa đất cụ thể.',
    'D': 'Văn bản lịch sử/chuyển tiếp/hết hiệu lực một phần hoặc toàn phần; cần cho câu hỏi về giai đoạn trước nhưng không dùng sai cho hiện tại.',
    'E': 'Không phục vụ câu hỏi Vành đai 4 nếu không có yêu cầu cụ thể; giữ cho đối chiếu quan hệ pháp lý nhưng không ưu tiên review.',
    'F': 'Văn bản chính thức có khả năng liên quan nhưng chưa có receipt/đoạn được review; cần xác minh điều khoản và hiệu lực trước khi dùng.',
}
REQUIRED_PROVISIONS = {
    'C01': ['Luật Đất đai 2024 Điều 83–87 (trình tự, thủ tục thu hồi)', 'NĐ 88/2024 Điều 20–29', 'QĐ 40/2026-HN Điều 17'],
    'C02': ['Luật Đất đai 2024 Điều 95, 96, 101, 104, 108', 'NĐ 88/2024 Điều 4–11, 19', 'QĐ 40/2026-HN Điều 17'],
    'C03': ['Luật Đất đai 2024 Điều 96, 104, 111', 'NĐ 88/2024 Điều 30–31', 'Luật Nhà ở 2023 Điều 72', 'QĐ 40/2026-HN Điều 21'],
    'C04': ['NĐ 88/2024 Điều 4–11', 'Luật Khiếu nại 2011', 'NĐ 124/2020'],
    'C05': ['Luật Khiếu nại 2011', 'NĐ 124/2020', 'Luật 136/2025'],
    'C06': ['NĐ 151/2025', 'QĐ 40/2025-HN', 'Luật 136/2025'],
    'C07': ['Nguồn vận hành: đầu mối tiếp nhận, lịch tiếp dân, biểu mẫu'],
    'C08': ['Luật Đất đai 2024 Điều 3, 137', 'NĐ 88/2024', 'NĐ 102/2024'],
    'C09': ['Nghị quyết 56/2022/QH15', 'Nghị quyết 106/2022/QH15 (chưa có trong release)', 'Tin chính thức 4 quận/huyện'],
    'C10': ['Luật Đất đai 2024 Điều 254–255, 260', 'Luật Đất đai 2013', 'NĐ 47/2014', 'QĐ 56/2024-HN', 'QĐ 40/2026-HN'],
    'C11': ['Luật Khiếu nại 2011', 'NĐ 124/2020', 'Luật 136/2025'],
    'C12': ['Nguồn vận hành: kênh trợ giúp, tiếp công dân, số điện thoại/địa chỉ chính thức'],
}
PRIORITY_FOR = {
    'luat-dat-dai-2024': 'Điều 95/96/98/104/107/108/111 và các điều chuyển tiếp; đối chiếu Luật 43/2024, Nghị quyết 254/2025.',
    'luat-43-2024': 'Sửa đổi Luật Đất đai/Nhà ở/Kinh doanh bất động sản; cần cho mốc hiệu lực.',
    'luat-thu-do-2026': 'Quy định riêng Hà Nội đang thay thế dần Luật Thủ đô 2024.',
    'nd-88-2024': 'Điều 11 bồi thường đất ở; Điều 19 hỗ trợ; Điều 30/31 tái định cư; đối chiếu NĐ 226/2025 và NĐ 49/2026.',
    'nd-226-2025': 'Sửa NĐ 88/2024, NĐ 151/2025 và các nghị định thi hành Luật Đất đai.',
    'nd-49-2026': 'Tháo gỡ vướng mắc thi hành Luật Đất đai; bãi bỏ một phần NĐ 151/2025/NĐ 226/2025.',
    'nq-254-2025': 'Cơ chế đặc thù, ưu tiên áp dụng cho một số dự án; cần đọc cùng Điều 13 khoản 3.',
    'qd-40-2026-hanoi': 'Quy định bồi thường, hỗ trợ, tái định cư Hà Nội đang áp dụng; thay thế QĐ 56/2024 và QĐ 38/2025.',
    'luat-nha-o-2023': 'Điều 72 bố trí nhà ở tái định cư/chỗ ở tạm thời; đang bị top-K bỏ qua vì chưa có receipt.',
    'luat-quy-hoach-2025': 'Phân biệt quy hoạch với quyết định thu hồi; chưa có receipt nên chưa được dùng làm căn cứ.',
    'nq-258-2025': 'Cơ chế thí điểm đặc thù; cần kiểm tra phạm vi áp dụng cho Vành đai 4.',
    'nq-90-2026-hanoi': 'Hà Nội thực hiện khoản 4 Điều 7 Nghị quyết 258/2025 về bồi thường đất.',
}


def load(path):
    return json.loads((ROOT / path).read_text())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def reviewed_chunk_count(receipt):
    if not receipt:
        return 0
    return len({chunk for window in receipt.get('verified_scope') or []
                for chunk in window.get('chunk_checksums', {})})


def standing_scope(release, policy):
    scope = {}
    for doc_id, entry in (policy.get('standing') or {}).items():
        checksums = dict(entry.get('standing_chunks') or {})
        for window in entry.get('legal_windows') or []:
            if date.fromisoformat(window['as_of_from']) <= AS_OF < date.fromisoformat(window['as_of_to']):
                checksums.update(window.get('chunk_checksums') or {})
        if checksums:
            scope[doc_id] = checksums
    return scope


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', default='data/staging/phase2c-current/release-v5.json')
    parser.add_argument('--sources', default='data/sources.json')
    parser.add_argument('--policy', default='reports/source-review-20261022/standing/source-gate-v2-candidate-20261022.json')
    parser.add_argument('--receipts', default='reports/source-review-20261022/receipts-20261022')
    parser.add_argument('--requirements', default='data/citizen_source_requirements.json')
    parser.add_argument('--relations', default='data/legal_relations.json')
    parser.add_argument('--output-dir', default='reports/qa')
    args = parser.parse_args()

    release = load(args.release)
    manifest = load(args.sources)
    policy = load(args.policy)
    requirements = load(args.requirements)
    relations = load(args.relations)
    receipts = {}
    for path in sorted((ROOT / args.receipts).glob('*.json')):
        receipt = json.loads(path.read_text())
        receipts[receipt['document_id']] = receipt
    documents = {doc['id']: doc for doc in release['documents']}
    chunks = sum(len(doc.get('chunks', [])) for doc in release['documents'])
    scope = standing_scope(release, policy)

    rows = []
    for doc_id, doc in sorted(documents.items()):
        category = CATEGORY.get(doc_id, 'F')
        receipt = receipts.get(doc_id)
        admitted = len(scope.get(doc_id, {}))
        rows.append({
            'id': doc_id, 'title': doc['title'], 'document_number': doc.get('document_number'),
            'source_kind': doc.get('source_kind'), 'project': doc.get('project'),
            'effective_from': doc.get('effective_from'), 'effective_to': doc.get('effective_to'),
            'category': category, 'review_status': receipt.get('status') if receipt else None,
            'reviewed_chunks': reviewed_chunk_count(receipt),
            'admitted_passages_20261022': admitted,
            'justification': JUSTIFICATION[category],
            'priority_note': PRIORITY_FOR.get(doc_id),
            'relations_count': sum(1 for relation in relations
                                   if doc_id in {relation.get('source_id'), relation.get('target_id')}),
        })

    by_category = {}
    for row in rows:
        by_category.setdefault(row['category'], []).append(row['id'])

    coverage = []
    for requirement in requirements['requirements']:
        candidates = requirement.get('candidate_document_ids') or []
        present = [doc_id for doc_id in candidates if doc_id in documents]
        reviewed = [doc_id for doc_id in present if doc_id in receipts]
        admitted = {doc_id: len(scope.get(doc_id, {})) for doc_id in present if scope.get(doc_id)}
        gaps = [doc_id for doc_id in present if doc_id not in receipts]
        operational = bool(requirement.get('needs_operational_source'))
        if admitted:
            answerability = 'partial'
            remaining = 'Có đoạn được review nhưng cần đối chiếu đủ điều/khoản liệt kê; không phải mọi điều khoản bắt buộc đã có review.'
        elif reviewed:
            answerability = 'missing_evidence'
            remaining = 'Tài liệu đã có receipt nhưng không có đoạn nào admitted tại ngày audit.'
        elif present:
            answerability = 'missing_review'
            remaining = 'Tài liệu có trong release nhưng chưa có receipt/đoạn review.'
        else:
            answerability = 'missing_operational_source' if operational else 'missing_document'
            remaining = 'Cần nguồn vận hành chính thức chưa được review.' if operational else 'Chưa có tài liệu nguồn trong release.'
        coverage.append({
            'requirement_id': requirement['id'],
            'question': requirement.get('question') or requirement.get('title') or requirement.get('summary'),
            'required_provisions': REQUIRED_PROVISIONS.get(requirement['id'], []),
            'candidate_documents': candidates,
            'present_in_release': present,
            'reviewed_documents': reviewed,
            'admitted_passages_20261022': admitted,
            'retrieval_status': 'admitted' if admitted else ('reviewed_not_admitted' if reviewed else 'not_reviewed'),
            'missing_review_documents': gaps,
            'needs_operational_source': operational,
            'answerability': answerability,
            'remaining_gap': remaining,
        })

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix = {
        'audit': 'ring4-corpus-quality',
        'as_of': str(AS_OF),
        'release_id': release['id'],
        'manifest_records': len(manifest),
        'release_documents': len(documents),
        'release_chunks': chunks,
        'reviewed_documents': len(receipts),
        'reviewed_passages': len({chunk for receipt in receipts.values()
                                  for window in receipt.get('verified_scope', [])
                                  for chunk in window.get('chunk_checksums', {})}),
        'admissible_passages_20261022': sum(len(value) for value in scope.values()),
        'categories': {key: by_category.get(key, []) for key in 'ABCDEF'},
        'requirements': coverage,
    }
    (output_dir / 'ring4-coverage-matrix.json').write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2) + '\n')

    lines = [
        '# Ring Road 4 corpus quality and relevance audit',
        '',
        f'- Ngày audit (read-only): {AS_OF}',
        f'- Release đang xét: `{release["id"]}` — {len(documents)} tài liệu, {chunks} chunks.',
        f'- Manifest `data/sources.json`: {len(manifest)} bản ghi; {sum(1 for s in manifest if s.get("review_status") == "verified")} verified.',
        f'- Receipt hợp lệ đang pin: {len(receipts)} tài liệu; đoạn reviewed: {matrix["reviewed_passages"]}; đoạn admitted ngày {AS_OF}: {matrix["admissible_passages_20261022"]}.',
        '- Phân biệt các lớp: tồn tại nguồn ≠ manifest verified ≠ toàn vẹn nội dung ≠ liên quan chính sách ≠ review điều khoản ≠ hiệu lực pháp lý ≠ admission runtime.',
        '',
        '## 1. Phân loại A–F',
        '',
        '| ID | Số hiệu | Loại | Nguồn | Dự án | Hiệu lực | Receipt | Reviewed | Admitted 22/10 | Lý do |',
        '|---|---|---|---|---|---|---|---:|---:|---|',
    ]
    for row in rows:
        lines.append('| `{id}` | {number} | {category} | {kind} | {project} | {start}→{end} | {review} | {reviewed} | {admitted} | {why} |'.format(
            id=row['id'], number=row['document_number'] or '—', category=row['category'],
            kind=row['source_kind'], project=row['project'] or 'shared',
            start=row['effective_from'] or '—', end=row['effective_to'] or 'nay',
            review=row['review_status'] or 'none', reviewed=row['reviewed_chunks'],
            admitted=row['admitted_passages_20261022'],
            why=row['justification'] + (f" **Ưu tiên:** {row['priority_note']}" if row['priority_note'] else '')))
    lines += [
        '',
        '## 2. Vì sao chunk nhiều nhưng admitted ít',
        '',
        '1. Release chứa toàn bộ văn bản và chunk để tra cứu thư viện, nhưng chỉ đoạn có receipt và scope được review mới được dùng làm căn cứ.',
        '2. Chỉ 10/60 tài liệu có receipt đang pin; các đoạn ngoài `verified_scope` là `unknown` và bị loại fail-closed.',
        '3. Policy v2 chỉ chuyển các scope ngắn hạn (≤2 ngày) thành standing; các cửa sổ lịch sử vẫn giữ nguyên ngày, nên 31 đoạn reviewed không đủ điều kiện tại 22/10/2026.',
        '4. Kết quả 43 đoạn ngày 22/10 = 42 standing + 1 đoạn trong legal window của QĐ 40/2026; từ 28/10 còn 42 và ngày 01/01/2025 là 20.',
        '',
        '## 3. Khoảng trống ưu tiên',
        '',
        '- Điều 72 Luật Nhà ở 2023 (bố trí chỗ ở tạm thời/tái định cư) và Điều 94/95/104/107/108/111 Luật Đất đai: một phần đã review nhưng đang nằm ngoài cửa sổ hiện hành hoặc chưa có receipt.',
        '- Quy hoạch so với quyết định thu hồi: Luật Quy hoạch 2025 và Luật Quy hoạch đô thị và nông thôn 2024 chưa có receipt.',
        '- Khiếu nại/tố cáo: Luật Khiếu nại 2011, NĐ 124/2020, Luật 136/2025 chưa có receipt.',
        '- Nguồn vận hành Hà Nội (thủ tục tiếp nhận, lịch tiếp dân) còn thiếu trong release.',
        '- Văn bản dự án: Nghị quyết 56/2022/QH15 và 4 tin chính thức chỉ là context; chưa được review thành receipt và không được dùng để chứng minh quyền lợi.',
        '',
        '## 4. Đề xuất (chưa kích hoạt)',
        '',
        '- Giữ toàn bộ nguồn lịch sử và không hard-delete.',
        '- Review theo thứ tự: Điều 72 Luật Nhà ở; Điều 94/95/98/104/107/108/111 Luật Đất đai theo hiệu lực hiện hành; NĐ 88/2024 các điều 11/19/30/31; QĐ 40/2026 và các quan hệ sửa đổi; Luật Quy hoạch 2025; nhóm khiếu nại; nguồn vận hành Hà Nội.',
        '- Chỉ tạo policy/receipt mới sau khi đọc văn bản gốc, ghi rõ điều/khoản, hiệu lực và quan hệ sửa đổi; không suy diễn từ PDF không đổi.',
        '',
        '## 5. Giới hạn',
        '',
        '- Audit này là phân tích kỹ thuật đọc-only, không phải thẩm định pháp lý độc lập và không chứng nhận hiệu lực.',
        '- Chưa kết nối PostgreSQL production; số liệu lấy từ release/receipt/policy đã phiên bản hóa trong repo.',
        '- Phân loại A–F là khuyến nghị ưu tiên review, không phải kết luận áp dụng cho mọi tình huống.',
    ]
    (output_dir / 'ring4-corpus-quality.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({
        'documents': len(documents), 'chunks': chunks,
        'reviewed_documents': len(receipts),
        'admissible_20261022': matrix['admissible_passages_20261022'],
        'categories': {key: len(value) for key, value in matrix['categories'].items()},
        'requirements': {item['requirement_id']: item['answerability'] for item in coverage},
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
