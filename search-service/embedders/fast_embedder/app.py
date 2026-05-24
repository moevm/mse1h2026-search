import json
import logging
import math
import os
import threading
import time
from contextlib import asynccontextmanager
from typing import Iterable

import orjson
from fastapi import FastAPI, Request, Response
from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType
from pydantic import BaseModel, field_validator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("fast_embedder")

MODEL_ID = os.getenv("MODEL_ID", "intfloat/multilingual-e5-small")
MODEL_SOURCE = os.getenv("MODEL_SOURCE", MODEL_ID)
MODEL_FILE = os.getenv("MODEL_FILE", os.getenv("MODEL_FILE_NAME", "onnx/model.onnx"))
MODEL_EXTRA_FILES = [
    item.strip()
    for item in os.getenv("MODEL_EXTRA_FILES", "").split(",")
    if item.strip()
]
MODEL_DIM = int(os.getenv("MODEL_DIM", os.getenv("EMBEDDER_DIM", "384")))
CACHE_DIR = os.getenv("FASTEMBED_CACHE_PATH", "/app/.cache/fastembed")
ONNX_THREADS = int(
    os.getenv(
        "ONNX_THREADS",
        os.getenv("ORT_INTRA_OP_NUM_THREADS", os.getenv("TORCH_THREADS", "0")),
    )
)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
PARALLEL = os.getenv("PARALLEL")
NORMALIZE_EMBEDDINGS = os.getenv("NORMALIZE_EMBEDDINGS", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MAX_INPUT_CHARS = int(
    os.getenv("MAX_INPUT_CHARS", os.getenv("DOCUMENT_TEMPLATE_MAX_BYTES", "2500"))
)

QUERY_PREFIX = os.getenv(
    "QUERY_PREFIX", "query: " if MODEL_ID.startswith("intfloat/") else ""
)
DOCUMENT_PREFIX = os.getenv(
    "DOCUMENT_PREFIX", "passage: " if MODEL_ID.startswith("intfloat/") else ""
)

state: dict = {}
_inference_lock = threading.Lock()


def _parallel_value() -> int | None:
    if PARALLEL is None or PARALLEL == "":
        return None
    return int(PARALLEL)


def _providers() -> list[str] | None:
    raw = os.getenv("ONNX_PROVIDERS", "CPUExecutionProvider")
    providers = [provider.strip() for provider in raw.split(",") if provider.strip()]
    return providers or None


def _is_supported_model(model_id: str) -> bool:
    return any(
        model.get("model") == model_id
        for model in TextEmbedding.list_supported_models()
    )


def _register_custom_model() -> None:
    if _is_supported_model(MODEL_ID):
        return

    log.info(
        "Registering custom FastEmbed model model=%s source=%s file=%s dim=%d",
        MODEL_ID,
        MODEL_SOURCE,
        MODEL_FILE,
        MODEL_DIM,
    )
    TextEmbedding.add_custom_model(
        model=MODEL_ID,
        pooling=PoolingType.MEAN,
        normalization=True,
        sources=ModelSource(hf=MODEL_SOURCE),
        dim=MODEL_DIM,
        model_file=MODEL_FILE,
        additional_files=MODEL_EXTRA_FILES,
    )


def _embed_kwargs() -> dict:
    kwargs: dict = {"batch_size": BATCH_SIZE}
    parallel = _parallel_value()
    if parallel is not None:
        kwargs["parallel"] = parallel
    return kwargs


def _run_embed(method: str, texts: list[str]) -> list[list[float]]:
    model: TextEmbedding = state["model"]
    kwargs = _embed_kwargs()
    if method == "query" and hasattr(model, "query_embed"):
        vectors = model.query_embed(texts, **kwargs)
    elif method == "passage" and hasattr(model, "passage_embed"):
        vectors = model.passage_embed(texts, **kwargs)
    else:
        vectors = model.embed(texts, **kwargs)
    return [_vector_to_list(vector) for vector in vectors]


def _vector_to_list(vector: Iterable[float]) -> list[float]:
    values = [float(value) for value in vector]
    if not NORMALIZE_EMBEDDINGS:
        return values

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]


def _with_prefix(text: str, prefix: str) -> str:
    stripped = text.lstrip().lower()
    if not prefix or stripped.startswith(("query:", "passage:")):
        return text
    return f"{prefix}{text}"


def _truncate_text(text: str) -> str:
    if MAX_INPUT_CHARS <= 0 or len(text) <= MAX_INPUT_CHARS:
        return text
    return text[:MAX_INPUT_CHARS]


def _mode_for(text: str, default_mode: str) -> str:
    stripped = text.lstrip().lower()
    if stripped.startswith(("query:", "passage:")):
        return "raw"
    return default_mode


def _encode_many(texts: list[str], default_mode: str) -> list[list[float]]:
    groups: dict[str, list[tuple[int, str]]] = {"raw": [], "query": [], "passage": []}
    for index, text in enumerate(texts):
        text = _truncate_text(text)
        groups[_mode_for(text, default_mode)].append((index, text))

    embeddings: list[list[float] | None] = [None] * len(texts)
    with _inference_lock:
        for mode, indexed_texts in groups.items():
            if not indexed_texts:
                continue
            batch = [text for _, text in indexed_texts]
            vectors = _run_embed(mode, batch)
            for (index, _), vector in zip(indexed_texts, vectors, strict=True):
                embeddings[index] = vector

    return [embedding for embedding in embeddings if embedding is not None]


def _encode_one(text: str, default_mode: str) -> list[float]:
    return _encode_many([text], default_mode)[0]


@asynccontextmanager
async def lifespan(_: FastAPI):
    _register_custom_model()

    providers = _providers()
    threads = ONNX_THREADS if ONNX_THREADS > 0 else None
    log.info(
        "Loading ONNX model %s cache_dir=%s providers=%s threads=%s batch_size=%d parallel=%s max_input_chars=%d",
        MODEL_ID,
        CACHE_DIR,
        providers,
        threads or "auto",
        BATCH_SIZE,
        PARALLEL or "none",
        MAX_INPUT_CHARS,
    )
    model = TextEmbedding(
        model_name=MODEL_ID,
        cache_dir=CACHE_DIR,
        threads=threads,
        providers=providers,
    )

    warmup = _vector_to_list(
        next(model.embed([_with_prefix("warmup", QUERY_PREFIX)], batch_size=1))
    )
    state["model"] = model
    state["dim"] = len(warmup)
    log.info("Model loaded. embedding_dim=%d", state["dim"])

    yield
    state.clear()


app = FastAPI(lifespan=lifespan)

BATCH_PATHS = {"/embed/documents", "/embed/queries", "/embed/meilisearch"}


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


class EmbedRequest(BaseModel):
    input: str


class EmbedResponse(BaseModel):
    embedding: list[float]


class BatchEmbedRequest(BaseModel):
    inputs: list[str]

    @field_validator("inputs", mode="before")
    @classmethod
    def wrap_str_in_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v


class BatchEmbedResponse(BaseModel):
    embeddings: list[list[float]]


@app.get("/health")
def health():
    return {
        "status": "ok" if "model" in state else "loading",
        "backend": "fastembed",
        "model": MODEL_ID,
        "dim": state.get("dim"),
        "max_input_chars": MAX_INPUT_CHARS,
    }


@app.post("/embed/query", response_model=EmbedResponse)
def embed_query(req: EmbedRequest):
    return {"embedding": _encode_one(_with_prefix(req.input, QUERY_PREFIX), "raw")}


@app.post("/embed/document", response_model=EmbedResponse)
def embed_document(req: EmbedRequest):
    return {"embedding": _encode_one(_with_prefix(req.input, DOCUMENT_PREFIX), "raw")}


@app.post("/embed/queries", response_model=BatchEmbedResponse)
def embed_queries(req: BatchEmbedRequest):
    return _embedding_response(
        _encode_many([_with_prefix(text, QUERY_PREFIX) for text in req.inputs], "raw")
    )


@app.post("/embed/documents", response_model=BatchEmbedResponse)
def embed_documents(req: BatchEmbedRequest):
    return _embedding_response(
        _encode_many(
            [_with_prefix(text, DOCUMENT_PREFIX) for text in req.inputs], "raw"
        )
    )


@app.post("/embed/meilisearch", response_model=BatchEmbedResponse)
def embed_meilisearch(req: BatchEmbedRequest):
    return _embedding_response(_encode_many(req.inputs, "query"))


def _embedding_response(embeddings: list[list[float]]) -> Response:
    return Response(
        content=orjson.dumps({"embeddings": embeddings}),
        media_type="application/json",
    )
