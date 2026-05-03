from fastembed.common.model_description import PoolingType, ModelSource
from fastembed import TextEmbedding
import warnings
import logging
import pymysql
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_OFFLINE"] = "0"


# логирование
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("etu_search")
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", module="huggingface_hub")

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# настройки подключения к бд
MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "user",
    "password": "password",
    "db": "db",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

MANTICORE_URL = "http://127.0.0.1:9308"
MANTICORE_TABLE = "etu_pages"
CHUNK_SIZE = 1000

PATHS = {
    "dataset": "../data/information/ru/information_ru.json",
    "no_results_log": "logs/no_results.log",
    "bad_results_log": "logs/bad_results.log",
}

MANTICORE_ESCAPE_TABLE = str.maketrans({c: f"\\{c}" for c in "&'-/@+"})

METRICS_K_VALUES = [1, 3, 5, 10]
BAD_RESULTS_METRIC_K = 3

SEARCH_PARAMS = {
    "ranker": "sph04",
    "field_weights": {
        "pagetitle": 100,
        "longtitle": 50,
        "menutitle": 50,
        "alias": 25,
        "description": 15,
        "introtext": 10,
        "content": 5,
    },
}

# параметры ml
MODEL_CACHE_DIR = str(BASE_DIR / "models_cache")
EMBEDDER_MODEL_NAME = "intfloat/multilingual-e5-small"
KNN_EF_SEARCH = 400
RRF_K_CONSTANT = 60
KNN_MAX_DISTANCE = 0.25

# регистрация модели
try:
    TextEmbedding.add_custom_model(
        model=EMBEDDER_MODEL_NAME,
        pooling=PoolingType.MEAN,
        normalization=True,
        sources=ModelSource(hf=EMBEDDER_MODEL_NAME),
        dim=384,
        model_file="onnx/model.onnx",
    )
except ValueError:
    pass
