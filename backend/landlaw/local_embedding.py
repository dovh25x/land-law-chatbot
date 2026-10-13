"""Pinned E5 CPU inference; the Colab worker uses identical model and preprocessing."""
import hashlib
import math
import threading
import urllib.request
from pathlib import Path

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

def vector_valid(vector):
    return (isinstance(vector, list) and len(vector) == 384
            and all(type(x) in (int, float) and math.isfinite(x) for x in vector)
            and abs(sum(x*x for x in vector) - 1.0) < 1e-4)

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

class LocalE5:
    def __init__(self, model_dir):
        self.model_dir = Path(model_dir)
        self.encoder = None
        self.lock = threading.Lock()

    def embed_many(self, texts, title=None, query=False):
        # One model instance and one inference at a time, including concurrent turns.
        with self.lock:
            if self.encoder is None:
                if not all((self.model_dir/name).is_file() for name in ('model_quantized.onnx','sentencepiece.bpe.model')):
                    raise RuntimeError('Pinned embedding files missing; rebuild the deployment image')
                self.encoder = Encoder(self.model_dir, threads=1)
            return [self.encoder.encode(text if query else (title+'\n'+text if title else text),query=query) for text in texts]


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3 or sys.argv[1] != 'download':
        raise SystemExit('Usage: local_embedding.py download MODEL_DIR')
    Encoder(Path(sys.argv[2]),threads=1)
    print('Pinned model files downloaded, checksums verified and CPU inference session initialized.')
