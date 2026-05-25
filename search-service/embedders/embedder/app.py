import json
import logging
import threading
import time
from contextlib import asynccontextmanager

import orjson
import torch
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, field_validator
from sentence_transformers import SentenceTransformer

from config import (
    BATCH_PATHS,
    BATCH_SIZE,
    DEVICE,
    DOCUMENT_PREFIX,
    INFERENCE_BACKEND,
    MODEL_FILE_NAME,
    MODEL_ID,
    QUERY_PREFIX,
    QUERY_PROMPT_NAME,
    SUPPORTED_BACKENDS,
    TORCH_THREADS,
    TRUST_REMOTE_CODE,
    model_kwargs,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("embedder")

state: dict = {}
_inference_lock = threading.Lock()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if INFERENCE_BACKEND not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"Unsupported INFERENCE_BACKEND={INFERENCE_BACKEND!r}. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_BACKENDS))}"
        )

    if TORCH_THREADS > 0:
        torch.set_num_threads(TORCH_THREADS)
    if INFERENCE_BACKEND == "torch" and MODEL_FILE_NAME:
        log.warning("MODEL_FILE_NAME=%s is ignored for torch backend", MODEL_FILE_NAME)

    log.info(
        "Loading model %s backend=%s device=%s file_name=%s batch_size=%d",
        MODEL_ID,
        INFERENCE_BACKEND,
        DEVICE,
        MODEL_FILE_NAME or "-",
        BATCH_SIZE,
    )
    model = SentenceTransformer(
        MODEL_ID,
        backend=INFERENCE_BACKEND,
        device=DEVICE,
        model_kwargs=model_kwargs(),
        trust_remote_code=TRUST_REMOTE_CODE,
    )
    model.eval()

    dim = model.get_sentence_embedding_dimension()
    log.info(
        "Model loaded. embedding_dim=%d, max_seq_length=%d", dim, model.max_seq_length
    )

    with torch.inference_mode():
        model.encode(
            f"{QUERY_PREFIX}warmup",
            prompt_name=QUERY_PROMPT_NAME,
            normalize_embeddings=True,
        )
    log.info("Warmup done")

    state["model"] = model
    state["dim"] = dim
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


class EmbedRequest(BaseModel):
    input: str


class EmbedResponse(BaseModel):
    embedding: list[float]


def _with_prefix(text: str, prefix: str) -> str:
    known_prefixes = tuple(item for item in (QUERY_PREFIX, DOCUMENT_PREFIX) if item)
    if not prefix or (known_prefixes and text.startswith(known_prefixes)):
        return text
    return f"{prefix}{text}"


def _encode_one(text: str, prompt_name: str | None, prefix: str) -> list[float]:
    model: SentenceTransformer = state["model"]
    with _inference_lock, torch.inference_mode():
        vec = model.encode(
            _with_prefix(text, prefix),
            prompt_name=prompt_name,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
    return vec.tolist()


def _encode_many(texts: list[str], prompt_name: str | None, prefix: str):
    model: SentenceTransformer = state["model"]
    with _inference_lock, torch.inference_mode():
        return model.encode(
            [_with_prefix(text, prefix) for text in texts],
            prompt_name=prompt_name,
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
        )


def _embedding_response(mat) -> Response:
    return Response(
        content=orjson.dumps({"embeddings": mat}, option=orjson.OPT_SERIALIZE_NUMPY),
        media_type="application/json",
    )


class BatchEmbedRequest(BaseModel):
    inputs: list[str]

    @field_validator("inputs", mode="before")
    @classmethod
    def wrap_str_in_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v


@app.get("/health")
def health():
    return {
        "status": "ok" if "model" in state else "loading",
        "model": MODEL_ID,
        "backend": INFERENCE_BACKEND,
        "model_file_name": MODEL_FILE_NAME,
        "dim": state.get("dim"),
    }


@app.post("/embed/query", response_model=EmbedResponse)
def embed_query(req: EmbedRequest):
    return {"embedding": _encode_one(req.input, QUERY_PROMPT_NAME, QUERY_PREFIX)}


@app.post("/embed/document", response_model=EmbedResponse)
def embed_document(req: EmbedRequest):
    return {"embedding": _encode_one(req.input, None, DOCUMENT_PREFIX)}


@app.post("/embed/queries")
def embed_queries(req: BatchEmbedRequest):
    return _embedding_response(
        _encode_many(req.inputs, QUERY_PROMPT_NAME, QUERY_PREFIX)
    )


@app.post("/embed/documents")
def embed_documents(req: BatchEmbedRequest):
    return _embedding_response(_encode_many(req.inputs, None, DOCUMENT_PREFIX))


@app.post("/embed/meilisearch")
def embed_meilisearch(req: BatchEmbedRequest):
    return _embedding_response(
        _encode_many(req.inputs, QUERY_PROMPT_NAME, QUERY_PREFIX)
    )
