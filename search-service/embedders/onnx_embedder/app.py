import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import onnxruntime as ort
import orjson
from fastapi import FastAPI, Request, Response
from huggingface_hub import hf_hub_download
from pydantic import BaseModel, field_validator
from transformers import AutoTokenizer

from config import (
    BATCH_PATHS,
    BATCH_SIZE,
    DEVICE,
    DOCUMENT_PREFIX,
    EMBEDDING_OUTPUT_NAME,
    MAX_LENGTH,
    MKL_NUM_THREADS,
    MODEL_FILE_NAME,
    MODEL_ID,
    OMP_NUM_THREADS,
    ORT_INTER_OP_NUM_THREADS,
    ORT_INTRA_OP_NUM_THREADS,
    QUERY_PREFIX,
    TRUST_REMOTE_CODE,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("onnx_embedder")

state: dict = {}
_inference_lock = threading.Lock()


class EmbedRequest(BaseModel):
    input: str


class BatchEmbedRequest(BaseModel):
    inputs: list[str]

    @field_validator("inputs", mode="before")
    @classmethod
    def wrap_str_in_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v


class OnnxEmbedder:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            trust_remote_code=TRUST_REMOTE_CODE,
        )
        self.model_path = _resolve_model_path()
        self.session = _create_session(self.model_path)
        self.input_names = {item.name for item in self.session.get_inputs()}
        self.output_names = [item.name for item in self.session.get_outputs()]
        self.embedding_output_name = _resolve_embedding_output_name(self.output_names)
        self.max_length = _resolve_max_length(self.tokenizer)
        self.dim = self._resolve_embedding_dim()

    def encode(self, texts: list[str]) -> np.ndarray:
        batches = []
        for start in range(0, len(texts), BATCH_SIZE):
            batches.append(self._encode_batch(texts[start : start + BATCH_SIZE]))
        if not batches:
            return np.empty((0, self.dim), dtype=np.float32)
        return np.vstack(batches)

    def _encode_batch(self, texts: list[str]) -> np.ndarray:
        tokenizer_kwargs = {
            "padding": True,
            "truncation": True,
            "return_tensors": "np",
        }
        if self.max_length:
            tokenizer_kwargs["max_length"] = self.max_length

        tokens = self.tokenizer(texts, **tokenizer_kwargs)
        feed = {name: tokens[name] for name in self.input_names if name in tokens}
        if "position_ids" in self.input_names and "position_ids" not in feed:
            batch_size, seq_len = tokens["input_ids"].shape[:2]
            position_ids = np.arange(seq_len, dtype=np.int64).reshape(1, -1)
            feed["position_ids"] = np.repeat(position_ids, batch_size, axis=0)
        if not feed:
            raise ValueError(
                f"Tokenizer produced none of the ONNX inputs: {sorted(self.input_names)}"
            )

        raw = self.session.run([self.embedding_output_name], feed)[0]
        embeddings = _pool_embeddings(np.asarray(raw, dtype=np.float32), tokens)
        return _l2_normalize(embeddings)

    def _resolve_embedding_dim(self) -> int:
        output = next(
            item
            for item in self.session.get_outputs()
            if item.name == self.embedding_output_name
        )
        if output.shape and isinstance(output.shape[-1], int):
            return output.shape[-1]
        return int(self.encode(["dimension probe"]).shape[-1])


@asynccontextmanager
async def lifespan(_: FastAPI):
    _configure_thread_env()
    log.info(
        "Loading ONNX model %s file_name=%s device=%s batch_size=%d",
        MODEL_ID,
        MODEL_FILE_NAME,
        DEVICE,
        BATCH_SIZE,
    )
    embedder = OnnxEmbedder()
    log.info(
        "Model loaded. embedding_dim=%d max_length=%s inputs=%s outputs=%s",
        embedder.dim,
        embedder.max_length or "-",
        ",".join(sorted(embedder.input_names)),
        ",".join(embedder.output_names),
    )
    embedder.encode([_with_prefix("warmup", QUERY_PREFIX)])
    log.info("Warmup done")

    state["embedder"] = embedder
    state["dim"] = embedder.dim
    state["output"] = embedder.embedding_output_name
    yield
    state.clear()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_batch_size(request: Request, call_next):
    if request.url.path in BATCH_PATHS:
        body = await request.body()
        try:
            n = len(json.loads(body).get("inputs", []))
        except Exception:
            n = -1

        async def _receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = _receive
        t0 = time.perf_counter()
        response = await call_next(request)
        log.info(
            "batch %s n=%d %.0fms",
            request.url.path,
            n,
            (time.perf_counter() - t0) * 1000,
        )
        return response
    return await call_next(request)


@app.get("/health")
def health():
    return {
        "status": "ok" if "embedder" in state else "loading",
        "model": MODEL_ID,
        "backend": "onnxruntime",
        "model_file_name": MODEL_FILE_NAME,
        "embedding_output": state.get("output"),
        "dim": state.get("dim"),
    }


@app.post("/embed/query")
def embed_query(req: EmbedRequest):
    return _json_response({"embedding": _encode_many([req.input], QUERY_PREFIX)[0]})


@app.post("/embed/document")
def embed_document(req: EmbedRequest):
    return _json_response({"embedding": _encode_many([req.input], DOCUMENT_PREFIX)[0]})


@app.post("/embed/queries")
def embed_queries(req: BatchEmbedRequest):
    return _embedding_response(_encode_many(req.inputs, QUERY_PREFIX))


@app.post("/embed/documents")
def embed_documents(req: BatchEmbedRequest):
    return _embedding_response(_encode_many(req.inputs, DOCUMENT_PREFIX))


@app.post("/embed/meilisearch")
def embed_meilisearch(req: BatchEmbedRequest):
    return _embedding_response(_encode_many(req.inputs, QUERY_PREFIX))


def _encode_many(texts: list[str], prefix: str) -> np.ndarray:
    embedder: OnnxEmbedder = state["embedder"]
    prefixed = [_with_prefix(text, prefix) for text in texts]
    with _inference_lock:
        return embedder.encode(prefixed)


def _embedding_response(mat: np.ndarray) -> Response:
    return _json_response({"embeddings": mat})


def _json_response(payload: dict) -> Response:
    return Response(
        content=orjson.dumps(payload, option=orjson.OPT_SERIALIZE_NUMPY),
        media_type="application/json",
    )


def _with_prefix(text: str, prefix: str) -> str:
    known_prefixes = tuple(item for item in (QUERY_PREFIX, DOCUMENT_PREFIX) if item)
    if not prefix or (known_prefixes and text.startswith(known_prefixes)):
        return text
    return f"{prefix}{text}"


def _resolve_model_path() -> Path:
    model_path = Path(MODEL_ID)
    if model_path.exists():
        path = model_path / MODEL_FILE_NAME if MODEL_FILE_NAME else model_path
        _ensure_external_data_file(path)
        return path

    path = Path(hf_hub_download(repo_id=MODEL_ID, filename=MODEL_FILE_NAME))
    external_name = f"{MODEL_FILE_NAME}_data"
    try:
        hf_hub_download(repo_id=MODEL_ID, filename=external_name)
    except Exception as exc:
        log.info("No external ONNX data file downloaded for %s: %s", external_name, exc)
    return path


def _ensure_external_data_file(path: Path) -> None:
    external_path = path.with_name(f"{path.name}_data")
    if path.exists() and not external_path.exists():
        log.info("No local external ONNX data file found at %s", external_path)


def _create_session(model_path: Path) -> ort.InferenceSession:
    options = ort.SessionOptions()
    if ORT_INTRA_OP_NUM_THREADS > 0:
        options.intra_op_num_threads = ORT_INTRA_OP_NUM_THREADS
    if ORT_INTER_OP_NUM_THREADS > 0:
        options.inter_op_num_threads = ORT_INTER_OP_NUM_THREADS
    return ort.InferenceSession(
        str(model_path),
        sess_options=options,
        providers=_providers_for_device(),
    )


def _providers_for_device() -> list[str]:
    available = ort.get_available_providers()
    if DEVICE.startswith("cuda") and "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def _resolve_embedding_output_name(output_names: list[str]) -> str:
    if EMBEDDING_OUTPUT_NAME and EMBEDDING_OUTPUT_NAME in output_names:
        return EMBEDDING_OUTPUT_NAME
    if "sentence_embedding" in output_names:
        return "sentence_embedding"
    if len(output_names) == 1:
        return output_names[0]
    raise ValueError(
        "Cannot choose embedding output. "
        f"Set EMBEDDING_OUTPUT_NAME; available outputs: {', '.join(output_names)}"
    )


def _resolve_max_length(tokenizer) -> int:
    if MAX_LENGTH > 0:
        return MAX_LENGTH
    model_max_length = int(getattr(tokenizer, "model_max_length", 0) or 0)
    if model_max_length > 1_000_000:
        return 0
    return model_max_length


def _l2_normalize(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / np.clip(norms, a_min=1e-12, a_max=None)


def _pool_embeddings(raw: np.ndarray, tokens) -> np.ndarray:
    if raw.ndim == 2:
        return raw
    if raw.ndim != 3:
        raise ValueError(f"Unsupported ONNX embedding output shape: {raw.shape}")

    attention_mask = np.asarray(tokens["attention_mask"], dtype=np.float32)
    mask = attention_mask[..., None]
    summed = np.sum(raw * mask, axis=1)
    counts = np.clip(np.sum(mask, axis=1), a_min=1e-12, a_max=None)
    return summed / counts


def _configure_thread_env() -> None:
    if OMP_NUM_THREADS > 0:
        os.environ["OMP_NUM_THREADS"] = str(OMP_NUM_THREADS)
    if MKL_NUM_THREADS > 0:
        os.environ["MKL_NUM_THREADS"] = str(MKL_NUM_THREADS)
