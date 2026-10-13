"""Portable CPU embedding job. No application secrets, API credits or GPU required."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time
import urllib.request
import zipfile

MODEL = {
    "name": "multilingual-e5-small-onnx-q8-window-v1",
    "dimensions": 384,
    "onnx_revision": "761b726dd34fb83930e26aab4e9ac3899aa1fa78",
    "tokenizer_revision": "614241f622f53c4eeff9890bdc4f31cfecc418b3",
    "onnx_sha256": "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193",
    "tokenizer_sha256": "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
    "preprocessing": "e5-prefix-each-window-sp-offset1-mask-mean-l2-window-mean-l2-v1",
    "passage_max_tokens": 512,
    "query_max_tokens": 128,
    "overlap_tokens": 64,
}
MAX_INPUT_BYTES = 64 * 1024 * 1024


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value))
    temporary.replace(path)


def export_bundle(release_path, destination):
    release = json.loads(release_path.read_text())
    rows = []
    for doc in release["documents"]:
        for chunk in doc["chunks"]:
            if sha(chunk["text"].encode()) != chunk["checksum"]:
                raise ValueError("Source chunk checksum mismatch")
            rows.append({"id": chunk["id"], "document_id": doc["id"], "title": doc["title"],
                         "text": chunk["text"], "checksum": chunk["checksum"],
                         "locator": chunk["locator"], "page": chunk.get("page")})
    if not rows or len(rows) > 20000 or len({r['id'] for r in rows}) != len(rows):
        raise ValueError("Empty, oversized or duplicate input corpus")
    data = {"format": 1, "source_release": release["id"], "model": MODEL, "rows": rows}
    raw = canonical(data)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds 64 MB")
    worker = Path(__file__).read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"format": 1, "input_sha256": sha(raw), "worker_sha256": sha(worker),
                "chunks": len(rows), "source_release": release["id"], "model": MODEL}
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("input.json", raw)
        bundle.writestr("manifest.json", canonical(manifest))
        bundle.writestr("offline_e5_colab.py", worker)
    print(json.dumps({"bundle": str(destination), "chunks": len(rows),
                      "input_sha256": manifest["input_sha256"], "bytes": destination.stat().st_size}))
    return manifest


def load_input(bundle_path):
    with zipfile.ZipFile(bundle_path) as bundle:
        if bundle.getinfo("manifest.json").file_size > 100000:
            raise ValueError("Manifest exceeds size limit")
        if bundle.getinfo("input.json").file_size > MAX_INPUT_BYTES:
            raise ValueError("Input exceeds 64 MB")
        raw = bundle.read("input.json")
        manifest = json.loads(bundle.read("manifest.json"))
    data = json.loads(raw)
    if (sha(raw) != manifest["input_sha256"] or data["model"] != MODEL or manifest["model"] != MODEL
            or data.get("format") != 1 or data["source_release"] != manifest["source_release"]):
        raise ValueError("Input checksum or embedding contract mismatch")
    rows = data["rows"]
    if not rows or len(rows) > 20000 or len({r['id'] for r in rows}) != len(rows):
        raise ValueError("Invalid input rows")
    if len(rows) != manifest["chunks"] or any(sha(r['text'].encode()) != r['checksum'] for r in rows):
        raise ValueError("Input source checksum/count mismatch")
    return data, manifest


def vector_valid(vector):
    return (isinstance(vector, list) and len(vector) == 384
            and all(type(x) in (int, float) and math.isfinite(x) for x in vector)
            and abs(sum(x*x for x in vector) - 1.0) < 1e-4)


def checkpoint_key(row):
    return sha(canonical({"model": MODEL, "title": row["title"], "checksum": row["checksum"]}))


def read_ledger(path, repair=False):
    """A terminated batch may leave a torn final line; never discard earlier work."""
    records = {}
    if not path.exists():
        return records
    with path.open("r+b" if repair else "rb") as stream:
        while True:
            start = stream.tell()
            line = stream.readline()
            if not line:
                break
            if not line.endswith(b"\n"):
                if not repair:
                    raise ValueError("Checkpoint ledger has an incomplete final line")
                stream.seek(start)
                stream.truncate()
                break
            record = json.loads(line)
            key, vector = record["key"], record["embedding"]
            if len(key) != 64 or not vector_valid(vector):
                raise ValueError("Invalid checkpoint vector")
            if key in records and records[key] != vector:
                raise ValueError("Conflicting checkpoint vectors")
            records[key] = vector
    return records


class Encoder:
    def __init__(self, model_dir, threads=2):
        import numpy as np
        import onnxruntime as ort
        import sentencepiece as spm
        self.np = np
        model_dir.mkdir(parents=True, exist_ok=True)
        files = [
            ("model_quantized.onnx", MODEL["onnx_sha256"],
             f"https://huggingface.co/Xenova/multilingual-e5-small/resolve/{MODEL['onnx_revision']}/onnx/model_quantized.onnx"),
            ("sentencepiece.bpe.model", MODEL["tokenizer_sha256"],
             f"https://huggingface.co/intfloat/multilingual-e5-small/resolve/{MODEL['tokenizer_revision']}/sentencepiece.bpe.model"),
        ]
        for name, checksum, url in files:
            path = model_dir/name
            if not path.exists() or self.file_sha(path) != checksum:
                temporary = path.with_suffix(path.suffix + ".download")
                with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as output:
                    while block := response.read(1024 * 1024):
                        output.write(block)
                if self.file_sha(temporary) != checksum:
                    temporary.unlink(missing_ok=True)
                    raise ValueError("Downloaded model checksum mismatch")
                temporary.replace(path)
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        self.session = ort.InferenceSession(str(model_dir/"model_quantized.onnx"),
                                           sess_options=options, providers=["CPUExecutionProvider"])
        self.tokenizer = spm.SentencePieceProcessor(model_file=str(model_dir/"sentencepiece.bpe.model"))

    @staticmethod
    def file_sha(path):
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    def token_ids(self, text):
        return [3 if i == 0 else i + 1 for i in self.tokenizer.encode(text, out_type=int)]

    def encode(self, text, query=False):
        np = self.np
        prefix = self.token_ids("query: " if query else "passage: ")
        body = self.token_ids(text)
        limit = MODEL["query_max_tokens" if query else "passage_max_tokens"] - len(prefix) - 2
        stride = limit - min(MODEL["overlap_tokens"], limit // 4)
        vectors = []
        for start in range(0, max(1, len(body)), stride):
            ids = np.array([[0] + prefix + body[start:start+limit] + [2]], dtype=np.int64)
            output = self.session.run(None, {"input_ids": ids, "attention_mask": np.ones_like(ids),
                                             "token_type_ids": np.zeros_like(ids)})[0]
            vector = output.mean(axis=1)[0]
            vector /= np.linalg.norm(vector)
            vectors.append(vector)
            if start + limit >= len(body):
                break
        result = np.stack(vectors).mean(axis=0)
        result /= np.linalg.norm(result)
        vector = result.tolist()
        if not vector_valid(vector):
            raise ValueError("Model produced an invalid vector")
        return vector


def validate_output(bundle_path, result_path):
    data, manifest = load_input(bundle_path)
    with zipfile.ZipFile(result_path) as result:
        if result.getinfo("summary.json").file_size > 100000 or result.getinfo("vectors.jsonl").file_size > 160 * 1024 * 1024:
            raise ValueError("Result exceeds size limit")
        summary = json.loads(result.read("summary.json"))
        if summary.get("status") != "complete" or summary.get("input_sha256") != manifest["input_sha256"] or summary.get("model") != MODEL:
            raise ValueError("Result does not match input/contract or is incomplete")
        raw = result.read("vectors.jsonl")
    if sha(raw) != summary["vectors_sha256"]:
        raise ValueError("Result vector checksum mismatch")
    records = [json.loads(line) for line in raw.splitlines()]
    by_id = {r["id"]: r for r in records}
    if len(by_id) != len(records) or len(records) != len(data["rows"]) or summary["completed_chunks"] != len(records):
        raise ValueError("Missing or duplicate result chunks")
    for row in data["rows"]:
        record = by_id.get(row["id"], {})
        if record.get("key") != checkpoint_key(row) or record.get("checksum") != row["checksum"] or not vector_valid(record.get("embedding")):
            raise ValueError("Result source/vector mismatch")
    return summary


def run_job(bundle_path, work_dir, output_path, model_dir, threads=2, limit=None):
    data, manifest = load_input(bundle_path)
    work_dir.mkdir(parents=True, exist_ok=True)
    descriptor = work_dir/"job.json"
    if descriptor.exists() and json.loads(descriptor.read_text()) != manifest:
        raise ValueError("Work directory belongs to a different input; use a new directory")
    atomic_json(descriptor, manifest)
    ledger_path = work_dir/"checkpoints.jsonl"
    cached = read_ledger(ledger_path, repair=True)
    encoder = None
    started = time.monotonic()
    newly_embedded = 0
    with ledger_path.open("ab") as ledger:
        for index, row in enumerate(data["rows"], 1):
            key = checkpoint_key(row)
            if key not in cached:
                if limit is not None and newly_embedded >= limit:
                    break
                encoder = encoder or Encoder(model_dir, threads)
                vector = encoder.encode(row["title"] + "\n" + row["text"])
                ledger.write(canonical({"key": key, "embedding": vector}) + b"\n")
                ledger.flush()
                os.fsync(ledger.fileno())
                cached[key] = vector
                newly_embedded += 1
            if index % 32 == 0 or index == len(data["rows"]):
                print(json.dumps({"processed": index, "total": len(data["rows"]),
                                  "new": newly_embedded, "seconds": round(time.monotonic()-started, 1)}), flush=True)
    completed = sum(checkpoint_key(row) in cached for row in data["rows"])
    summary = {"status": "complete" if completed == len(data["rows"]) else "partial",
               "input_sha256": manifest["input_sha256"], "source_release": data["source_release"],
               "model": MODEL, "total_chunks": len(data["rows"]), "completed_chunks": completed,
               "newly_embedded": newly_embedded, "run_seconds": round(time.monotonic()-started, 2)}
    atomic_json(work_dir/"progress.json", summary)
    if summary["status"] == "complete":
        raw = b"".join(canonical({"id": r["id"], "key": checkpoint_key(r), "checksum": r["checksum"],
                                  "embedding": cached[checkpoint_key(r)]}) + b"\n" for r in data["rows"])
        summary["vectors_sha256"] = sha(raw)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as result:
            result.writestr("vectors.jsonl", raw)
            result.writestr("summary.json", canonical(summary))
        temporary.replace(output_path)
        validate_output(bundle_path, output_path)
    print(json.dumps(summary), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("release", type=Path)
    export.add_argument("bundle", type=Path)
    run = commands.add_parser("run")
    run.add_argument("bundle", type=Path)
    run.add_argument("--work-dir", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--model-dir", type=Path, default=Path("/tmp/landlaw-e5-model"))
    run.add_argument("--threads", type=int, choices=range(1, 9), default=2)
    run.add_argument("--limit", type=int)
    validate = commands.add_parser("validate")
    validate.add_argument("bundle", type=Path)
    validate.add_argument("result", type=Path)
    args = parser.parse_args()
    if args.command == "export":
        export_bundle(args.release, args.bundle)
    elif args.command == "run":
        run_job(args.bundle, args.work_dir, args.output, args.model_dir, args.threads, args.limit)
    else:
        print(json.dumps(validate_output(args.bundle, args.result)))


if __name__ == "__main__":
    main()
