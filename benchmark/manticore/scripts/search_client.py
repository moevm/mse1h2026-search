from queries import MANTICORE_SEARCH_QUERY, MANTICORE_CHECK_CONNECTION
from config import (
    MANTICORE_URL,
    MANTICORE_TABLE,
    SEARCH_PARAMS,
    logger,
    MANTICORE_ESCAPE_TABLE,
    EMBEDDER_MODEL_NAME,
    KNN_EF_SEARCH,
    RRF_K_CONSTANT,
    KNN_MAX_DISTANCE,
    MODEL_CACHE_DIR,
)
from fastembed import TextEmbedding
import requests
import re

REGEX = re.compile(r"[^\w\s\&\-\/№@\'`’\+#]")
_weights = SEARCH_PARAMS.get("field_weights", {})
WEIGHTS_STR = ", ".join(f"{k}={v}" for k, v in _weights.items())
RANKER = SEARCH_PARAMS.get("ranker", "bm25")

http_session = requests.Session()

logger.info(f"Загрузка модели {EMBEDDER_MODEL_NAME} для поисковых запросов...")
embedder = TextEmbedding(model_name=EMBEDDER_MODEL_NAME, cache_dir=MODEL_CACHE_DIR)


def _execute_lexical_search(
    match_query: str, limit: int, original_query: str
) -> list[int]:
    """Лексический поиск"""
    sql = MANTICORE_SEARCH_QUERY.format(
        table_name=MANTICORE_TABLE,
        query=match_query,
        limit=limit,
        weights=WEIGHTS_STR,
        ranker=RANKER,
    )

    try:
        # timeout=3
        response = http_session.post(
            f"{MANTICORE_URL}/sql", data={"mode": "raw", "query": sql}, timeout=3
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            if data[0].get("error"):
                logger.warning(
                    f"Ошибка синтаксиса: {data[0]['error']} (Запрос: {original_query})"
                )
                return []
            if "data" in data[0]:
                return [int(row["id"]) for row in data[0]["data"]]
    except Exception as e:
        logger.error(f"Ошибка при выполнении лексического запроса: {e}")
    return []


def _execute_vector_search(
    query_vector: list[float], limit: int
) -> list[tuple[int, float]]:
    """Векторный поиск"""
    payload = {
        "table": MANTICORE_TABLE,
        "knn": {
            "field": "content_vector",
            "query_vector": query_vector,
            "k": limit,
            "ef": KNN_EF_SEARCH,
        },
    }
    try:
        # timeout=3
        response = http_session.post(f"{MANTICORE_URL}/search", json=payload, timeout=3)
        response.raise_for_status()
        data = response.json()

        results = []
        if "hits" in data and "hits" in data["hits"]:
            for hit in data["hits"]["hits"]:
                doc_id = int(hit["_id"])
                knn_dist = float(hit["_knn_dist"])
                results.append((doc_id, knn_dist))
        return results
    except Exception as e:
        logger.error(f"Ошибка векторного запроса: {e}")
    return []


def get_vector_for_text(text: str) -> list[float]:
    e5_query = f"query: {text}"
    vector_generator = embedder.embed([e5_query])
    return list(vector_generator)[0].tolist()


def search(query: str, top_k: int) -> list[int]:
    if not query.strip():
        return []

    safe_query = REGEX.sub(" ", query)
    words = safe_query.split()
    if not words:
        return []

    clean_words = [w.translate(MANTICORE_ESCAPE_TABLE) for w in words]
    plain_query = " ".join(clean_words)

    search_limit = top_k * 2

    lexical_results = _execute_lexical_search(plain_query, search_limit, query)

    query_vector = get_vector_for_text(plain_query)
    vector_raw_results = _execute_vector_search(query_vector, search_limit)

    vector_results = []
    for doc_id, dist in vector_raw_results:
        if dist <= KNN_MAX_DISTANCE:
            vector_results.append(doc_id)
        else:
            break

    rrf_scores = {}

    for rank, doc_id in enumerate(lexical_results):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (
            1.0 / (RRF_K_CONSTANT + rank + 1)
        )

    for rank, doc_id in enumerate(vector_results):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (
            1.0 / (RRF_K_CONSTANT + rank + 1)
        )

    # сортируем документы по убыванию баллов
    sorted_docs = sorted(
        rrf_scores.keys(), key=lambda doc_id: rrf_scores[doc_id], reverse=True
    )

    return sorted_docs[:top_k]


def check_connection() -> bool:
    try:
        # timeout=1
        http_session.post(
            f"{MANTICORE_URL}/sql",
            data={"mode": "raw", "query": MANTICORE_CHECK_CONNECTION},
            timeout=1,
        )
        return True
    except requests.exceptions.RequestException:
        return False
