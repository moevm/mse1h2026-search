import os
import torch


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def env_int_list(name: str, default: str) -> list[int]:
    raw = os.getenv(name, default)
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


MODEL_ID = os.getenv("MODEL_ID", "intfloat/multilingual-e5-small")
INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "torch").strip().lower()
MODEL_FILE_NAME = os.getenv("MODEL_FILE_NAME", "").strip() or None
TRUST_REMOTE_CODE = env_bool("TRUST_REMOTE_CODE")
QUERY_PROMPT_NAME = os.getenv("QUERY_PROMPT_NAME") or None
QUERY_PREFIX = os.getenv(
    "QUERY_PREFIX", "query: " if MODEL_ID == "intfloat/multilingual-e5-small" else ""
)
DOCUMENT_PREFIX = os.getenv(
    "DOCUMENT_PREFIX",
    "passage: " if MODEL_ID == "intfloat/multilingual-e5-small" else "",
)
DEVICE = os.getenv("DEVICE", "cpu")
TORCH_THREADS = env_int("TORCH_THREADS", 0)
BATCH_SIZE = env_int("BATCH_SIZE", 16)
BATCH_SIZE_CANDIDATES = env_int_list("BATCH_SIZE_CANDIDATES", "8,16,32,64")

SUPPORTED_BACKENDS = {"torch", "onnx", "openvino"}
BATCH_PATHS = {"/embed/documents", "/embed/queries", "/embed/meilisearch"}


def model_kwargs() -> dict:
    kwargs = {}
    if INFERENCE_BACKEND == "torch":
        kwargs["dtype"] = torch.float32
    elif MODEL_FILE_NAME:
        kwargs["file_name"] = MODEL_FILE_NAME
    return kwargs
