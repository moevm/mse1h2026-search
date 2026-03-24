import requests
import re

from config import (
    MANTICORE_URL, MANTICORE_TABLE, SEARCH_PARAMS, logger,
    EN_KBD, RU_KBD, TRANS_EN_TO_RU, TRANS_RU_TO_EN, TRANSLIT_RU_TO_EN,
    STOP_WORDS, MANTICORE_ESCAPE_TABLE, SYNONYMS
)
from queries import MANTICORE_SEARCH_QUERY, MANTICORE_CHECK_CONNECTION


REGEX = re.compile(r'[^\w\s\&\-\/№@\'`’\+#]')
_weights = SEARCH_PARAMS.get('field_weights', {})
WEIGHTS_STR = ", ".join(f"{k}={v}" for k, v in _weights.items())
RANKER = SEARCH_PARAMS.get('ranker', 'bm25')

http_session = requests.Session()


def generate_fallbacks(query: str) -> list[str]:
    fallbacks = []
    q_lower = query.lower()

    allowed_chars = set(EN_KBD + RU_KBD + "ё`")
    if any(c not in allowed_chars for c in q_lower):
        return fallbacks

    ru_count = sum(1 for c in q_lower if c in RU_KBD)
    en_count = sum(1 for c in q_lower if c in EN_KBD)
    if ru_count > en_count:
        fallbacks.append(q_lower.translate(TRANS_RU_TO_EN))
        translit = "".join(TRANSLIT_RU_TO_EN.get(c, c) for c in q_lower)
        if translit != q_lower:
            fallbacks.append(translit)
    else:
        fallbacks.append(q_lower.translate(TRANS_EN_TO_RU))
    return fallbacks


def _execute_manticore_sql(match_query: str, limit: int, original_query: str) -> list[int]:
    sql = MANTICORE_SEARCH_QUERY.format(
        table_name=MANTICORE_TABLE,
        query=match_query,
        limit=limit,
        weights=WEIGHTS_STR,
        ranker=RANKER
    )

    try:
        response = http_session.post(
            f"{MANTICORE_URL}/sql", data={'mode': 'raw', 'query': sql})

        if response.status_code >= 400:
            logger.error(
                f"Сырой ответ Manticore (HTTP {response.status_code}): {response.text}")

        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            if data[0].get('error'):
                err_msg = data[0]['error']
                logger.warning(
                    f"Ошибка синтаксиса: {err_msg} (Запрос: {original_query})"
                )
                return []
            if 'data' in data[0]:
                return [int(row['id']) for row in data[0]['data']]
        return []
    except Exception as e:
        logger.error(f"Ошибка при выполнении поискового запроса: {e}")
        return []


def search(query: str, top_k: int) -> list[int]:
    if not query.strip():
        return []

    safe_query = REGEX.sub(' ', query)
    words = [w for w in safe_query.split() if w.lower() not in STOP_WORDS]
    if not words:
        return []

    clean_words = [w.translate(MANTICORE_ESCAPE_TABLE) for w in words]
    plain_query = " ".join(clean_words)

    strict_expanded = []
    prefix_expanded = []

    for w in clean_words:
        w_lower = w.lower()
        w_prefix = f"{w}*" if len(w) >= 3 else w

        if w_lower in SYNONYMS:
            syn_str = " | ".join(SYNONYMS[w_lower])
            strict_expanded.append(f"({w} | {syn_str})")
            prefix_expanded.append(f"({w_prefix} | {syn_str})")
        else:
            strict_expanded.append(w)
            prefix_expanded.append(w_prefix)

    strict_query = " ".join(strict_expanded)
    prefix_query = " ".join(prefix_expanded)

    seen = set()
    results = []

    strict_results = _execute_manticore_sql(strict_query, top_k, query)
    if strict_results:
        results.extend(strict_results)
        seen.update(strict_results)

    if len(results) < top_k and len(clean_words) > 0:
        if prefix_query != strict_query:
            prefix_results = _execute_manticore_sql(
                prefix_query, top_k * 2, query)
            for doc_id in prefix_results:
                if doc_id not in seen:
                    seen.add(doc_id)
                    results.append(doc_id)
                    if len(results) >= top_k:
                        break

    if len(results) < top_k and len(clean_words) > 1:
        quorum_count = len(clean_words) // 2 + (len(clean_words) % 2)
        quorum_query = f'"{plain_query}"/{quorum_count}'

        if quorum_count < len(clean_words):
            quorum_results = _execute_manticore_sql(
                quorum_query, top_k * 2, query)
            for doc_id in quorum_results:
                if doc_id not in seen:
                    seen.add(doc_id)
                    results.append(doc_id)
                    if len(results) >= top_k:
                        break

    if not results:
        for fb_query in generate_fallbacks(plain_query):
            fb_results = _execute_manticore_sql(fb_query, top_k, fb_query)
            for doc_id in fb_results:
                if doc_id not in seen:
                    seen.add(doc_id)
                    results.append(doc_id)
                    if len(results) >= top_k:
                        break
            if results:
                break

    return results[:top_k]


def check_connection() -> bool:
    try:
        http_session.post(
            f"{MANTICORE_URL}/sql",
            data={'mode': 'raw', 'query': MANTICORE_CHECK_CONNECTION}
        )
        return True
    except requests.exceptions.ConnectionError:
        return False
