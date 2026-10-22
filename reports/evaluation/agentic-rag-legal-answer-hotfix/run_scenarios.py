"""Run deterministic legal-answer scenarios against one checked-out runtime.

Usage:
  PYTHONPATH=backend .venv/bin/python reports/evaluation/agentic-rag-legal-answer-hotfix/run_scenarios.py OUT.json

Run the script against the baseline worktree by pointing PYTHONPATH at that
worktree's backend. No network/model calls are made. The mocked provider returns
a fixed draft so the same scenario can be compared across baseline and hotfix.
"""
import asyncio
import json
import sys
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace

from landlaw.agentic_rag import BoundedAgenticRAG
from landlaw.config import Settings
from landlaw.models import ChatRequest
from landlaw.security import new_token
from landlaw.simple_rag import SimpleAnswer
from landlaw.store import Store

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests/fixtures/legal-answer-hotfix-release.json"


class Provider:
    configured = True

    def __init__(self, settings, answer, query="bồi thường tái định cư", direct=None):
        self.settings = settings
        self.answer = answer
        self.query = query
        self.direct = direct
        self.tool_steps = 0
        self.generations = 0
        self.payload = None

    async def embed(self, *args, **kwargs):
        budget = kwargs.get("budget")
        if budget is not None:
            budget.embedding_calls += 1
        return []

    async def tool_step(self, instruction, messages, tools, budget, **kwargs):
        self.tool_steps += 1
        budget.llm()
        if self.direct is not None:
            return self.direct
        return {
            "content": "",
            "tool_calls": [{
                "id": "call-1",
                "name": "search_legal_evidence",
                "arguments": json.dumps({"query": self.query}, ensure_ascii=False),
            }],
        }

    async def generate(self, schema, instruction, payload, budget, **kwargs):
        self.generations += 1
        self.payload = payload
        budget.llm()
        return self.answer


T01 = SimpleAnswer(
    answer=(
        "Việc nằm trong vùng quy hoạch chưa đủ để kết luận về tái định cư. "
        "Khi Nhà nước thu hồi đất ở và hộ đủ điều kiện bồi thường về đất ở, việc bố trí tái định cư "
        "được thực hiện theo phương án đã được phê duyệt [S1]. "
        "Bạn đã nhận quyết định thu hồi đất hoặc thông báo thu hồi chưa?"
    ),
    clarification_question="Bạn đã nhận quyết định thu hồi đất hoặc thông báo thu hồi chưa?",
    limitation="Đây là quy định chung; quyền lợi cụ thể phụ thuộc hồ sơ và phương án của dự án.",
)
T02 = SimpleAnswer(
    answer=(
        "Có giấy chứng nhận quyền sử dụng đất là một căn cứ quan trọng để xét điều kiện được bồi thường "
        "về đất khi Nhà nước thu hồi đất [S1]. Trường hợp không có giấy chứng nhận vẫn có thể được xét "
        "theo quy định về giấy tờ và nguồn gốc sử dụng đất [S1]. Bạn đang có loại giấy tờ nào?"
    ),
    clarification_question="Bạn đang có loại giấy tờ nào?",
)
L01 = SimpleAnswer(
    answer=(
        "Khi Nhà nước thu hồi hết đất ở hoặc phần diện tích đất ở còn lại nhỏ hơn diện tích tối thiểu "
        "được phép tách thửa, hộ gia đình đủ điều kiện được bồi thường có thể được bồi thường bằng "
        "giao đất ở có thu tiền sử dụng đất, mua nhà ở tái định cư hoặc bằng tiền [S3]. "
        "Điều kiện bồi thường còn phụ thuộc giấy tờ và nguồn gốc của thửa đất; bạn đang có loại giấy tờ nào?"
    ),
    clarification_question="Bạn đang có loại giấy tờ nào?",
)
L02 = SimpleAnswer(
    answer=(
        "Hộ gia đình đủ điều kiện bồi thường về đất ở có thể được bồi thường bằng giao đất ở tái định cư "
        "theo phương án đã được phê duyệt [S1, S2]. Bạn đã nhận được quyết định giao đất tái định cư chưa?"
    ),
    clarification_question="Bạn đã nhận được quyết định giao đất tái định cư chưa?",
)
L03 = SimpleAnswer(
    answer=(
        "Hỗ trợ ổn định đời sống được xét cho hộ gia đình, cá nhân đang sử dụng đất nông nghiệp nếu đủ "
        "điều kiện được bồi thường về đất [S1]. Mức và thời gian hỗ trợ phụ thuộc quy định của địa phương "
        "và diện tích đất thu hồi [S1]. Bạn bị thu hồi bao nhiêu phần trăm diện tích đất nông nghiệp?"
    ),
    clarification_question="Bạn bị thu hồi bao nhiêu phần trăm diện tích đất nông nghiệp?",
)
PURE = SimpleAnswer(
    answer="Bạn đã nhận được quyết định thu hồi đất hoặc thông báo thu hồi chưa?",
    clarification_question="Bạn đã nhận được quyết định thu hồi đất hoặc thông báo thu hồi chưa?",
)
UNCITED = SimpleAnswer(answer="Hộ gia đình có sổ đỏ được bồi thường về đất khi Nhà nước thu hồi đất.")
GROUPED = SimpleAnswer(
    answer="Theo Điều 95 [S1, S3], điều kiện bồi thường về đất được xét theo giấy tờ và nguồn gốc đất."
)
UNKNOWN = SimpleAnswer(
    answer="Theo Điều 95 [S1, S9], điều kiện bồi thường về đất được xét theo hồ sơ."
)

SCENARIOS = [
    ("T01", "Nhà tôi nằm trong khu vực quy hoạch đường Vành đai 4 Hà Nội, tôi có được bố trí tái định cư không?",
     "quy hoạch Vành đai 4 bố trí tái định cư", T01),
    ("T02", "Tôi không có sổ đỏ thì có được bồi thường về đất khi thu hồi không?",
     "không có sổ đỏ điều kiện bồi thường về đất", T02),
    ("L01", "Tôi có sổ đỏ, khi thu hồi đất có được bồi thường không?",
     "sổ đỏ bồi thường đất ở thu hồi", L01),
    ("L02", "Tôi đã nhận quyết định giao đất tái định cư, vậy có được bồi thường thêm không?",
     "quyết định giao đất tái định cư", L02),
    ("L03", "Hỗ trợ ổn định đời sống khi thu hồi đất nông nghiệp được tính thế nào?",
     "hỗ trợ ổn định đời sống đất nông nghiệp", L03),
    ("T01-CLARIFY", "Nhà tôi trong vùng quy hoạch Vành đai 4 thì có được bố trí tái định cư không?",
     "quy hoạch Vành đai 4 tái định cư", PURE),
    ("T02-CLARIFY", "Tôi không có sổ đỏ thì có được bồi thường về đất khi thu hồi không?",
     "không có sổ đỏ điều kiện bồi thường về đất",
     SimpleAnswer(answer="Bạn đang có loại giấy tờ nào?", clarification_question="Bạn đang có loại giấy tờ nào?")),
    ("UNCITED", "Tôi có sổ đỏ thì có được bồi thường về đất không?",
     "bồi thường đất ở", UNCITED),
    ("GROUPED", "Điều kiện bồi thường về đất là gì?",
     "điều kiện bồi thường về đất", GROUPED),
    ("UNKNOWN", "Điều kiện bồi thường về đất là gì?",
     "điều kiện bồi thường về đất", UNKNOWN),
]


def main(out_path):
    settings = Settings(
        _env_file=None, app_env="development", database_url="", admin_database_url="",
        llm_provider="groq", groq_model="openai/gpt-oss-120b",
        embedding_provider="local_onnx",
        embedding_model="multilingual-e5-small-onnx-q8-window-v1",
        embedding_dimensions=384, backup_encryption_key="",
        sqlite_path=str(Path(tempfile.mkdtemp(prefix="hotfix-scenarios-")) / "local.db"),
        data_dir=Path(tempfile.mkdtemp(prefix="hotfix-data-")),
        reports_dir=Path(tempfile.mkdtemp(prefix="hotfix-reports-")),
        groq_api_key="test-key", ip_hash_secret="a" * 32,
    )
    store = Store(settings)
    payload = json.loads(FIXTURE.read_text())
    payload["id"] = "legal-hotfix-fixture"
    store.stage(payload)
    store.publish("legal-hotfix-fixture")
    records = []
    try:
        for scenario_id, message, query, answer in SCENARIOS:
            sid = str(uuid.uuid4())
            store.create_session(sid, new_token())
            provider = Provider(settings, answer, query=query)
            req = ChatRequest(session_id=sid, message=message, history=[], mode="agentic_rag")
            try:
                result = asyncio.run(BoundedAgenticRAG(store, provider).run(
                    req, lambda _: None, "legal-hotfix-fixture"))
                request_data = result.model_dump(mode="json")
            except Exception as exc:
                request_data = {"status": "exception", "content": f"{type(exc).__name__}: {exc}"}
            records.append({
                "id": scenario_id,
                "message": message,
                "query": query,
                "status": request_data.get("status"),
                "content": request_data.get("content", ""),
                "citations": [
                    {"document_id": c.get("document_id"), "document_number": c.get("document_number"),
                     "locator": c.get("locator")}
                    for c in request_data.get("citations", [])
                ],
                "trace": [
                    {"step": e.get("step"), "tool": e.get("tool"), "summary": e.get("summary"),
                     "document_ids": e.get("document_ids", [])}
                    for e in request_data.get("trace", [])
                ],
                "llm_calls": request_data.get("llm_calls"),
                "tool_calls": request_data.get("tool_calls"),
                "support_level": request_data.get("support_level"),
                "provider_generations": provider.generations,
                "provider_tool_steps": provider.tool_steps,
            })
    finally:
        store.close()
    Path(out_path).write_text(json.dumps({
        "fixture": "tests/fixtures/legal-answer-hotfix-release.json",
        "fixture_provenance": payload.get("provenance"),
        "scenarios": records,
    }, ensure_ascii=False, indent=1))
    print(out_path)


if __name__ == "__main__":
    main(sys.argv[1])
