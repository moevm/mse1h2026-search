import os


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


MODEL_ID = os.getenv("MODEL_ID", "onnx-community/harrier-oss-v1-270m-ONNX")
MODEL_FILE_NAME = os.getenv("MODEL_FILE_NAME", "onnx/model_quantized.onnx").strip()
TRUST_REMOTE_CODE = env_bool("TRUST_REMOTE_CODE")
QUERY_PREFIX = os.getenv("QUERY_PREFIX", "")
DOCUMENT_PREFIX = os.getenv("DOCUMENT_PREFIX", "")
QUERY_PROMPT_NAME = os.getenv("QUERY_PROMPT_NAME") or None
DEVICE = os.getenv("DEVICE", "cpu").strip().lower()
TORCH_THREADS = env_int("TORCH_THREADS", 0)
OMP_NUM_THREADS = env_int("OMP_NUM_THREADS", 0)
MKL_NUM_THREADS = env_int("MKL_NUM_THREADS", 0)
ORT_INTRA_OP_NUM_THREADS = env_int("ORT_INTRA_OP_NUM_THREADS", TORCH_THREADS)
ORT_INTER_OP_NUM_THREADS = env_int("ORT_INTER_OP_NUM_THREADS", 0)
BATCH_SIZE = env_int("BATCH_SIZE", 16)
MAX_LENGTH = env_int("MAX_LENGTH", 0)
EMBEDDING_OUTPUT_NAME = os.getenv("EMBEDDING_OUTPUT_NAME", "sentence_embedding").strip()

BATCH_PATHS = {"/embed/documents", "/embed/queries", "/embed/meilisearch"}
