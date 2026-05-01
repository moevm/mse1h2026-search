import argparse
import html
import re
import sys
import time
import json
import requests
import pymysql
from typing import Dict, List, Any, Set

from bs4 import BeautifulSoup
from tqdm import tqdm
from fastembed import TextEmbedding

from queries import MANTICORE_CREATE_TABLE, MYSQL_SELECT_DOCUMENTS, MANTICORE_DROP_TABLE
from config import (
    MYSQL_CONFIG,
    MANTICORE_URL,
    MANTICORE_TABLE,
    CHUNK_SIZE,
    logger,
    EMBEDDER_MODEL_NAME,
    MODEL_CACHE_DIR,
)


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""

    raw = re.sub(r"\[\[.*?\]\]", " ", raw, flags=re.DOTALL)
    raw = re.sub(r"\[\*.*?\*\]", " ", raw, flags=re.DOTALL)
    raw = re.sub(r"\[\+.*?\+\]", " ", raw, flags=re.DOTALL)

    if raw.startswith(("http://", "https://")):
        return raw.strip()

    if "<" in raw:
        soup = BeautifulSoup(raw, "lxml")
        for tag in soup(["script", "style", "iframe", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
    else:
        text = raw

    text = text.replace("Ваш браузер не поддерживает iframe!", " ")

    clean_text = html.unescape(text)
    return re.sub(r"\s+", " ", clean_text).strip()


def truncate(text: str, max_chars: int = 50_000) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def build_url(
    doc_id: int, docs_dict: Dict[int, Any], visited_ids: Set[int] = None
) -> str:
    """Рекурсивно строит полный путь страницы (url)"""
    if visited_ids is None:
        visited_ids = set()

    if doc_id == 0 or doc_id not in docs_dict or doc_id in visited_ids:
        return ""

    visited_ids.add(doc_id)
    doc = docs_dict[doc_id]

    parent_url = build_url(doc["parent"], docs_dict, visited_ids)

    if parent_url:
        return f"{parent_url}/{doc['alias']}"
    return doc["alias"]


def determine_lang(url: str) -> str:
    """Определяет язык документа на основе языкового префикса в URL"""
    languages = ["ar", "cn", "de", "en", "fr", "pt", "ru", "es", "vn"]
    for l in languages:
        if url.startswith(f"{l}/"):
            return l
    return "ru"


def setup_manticore_table(recreate: bool) -> None:
    sql_url = f"{MANTICORE_URL}/sql"

    if recreate:
        logger.info(f"Удаляем таблицу '{MANTICORE_TABLE}' (--recreate)...")
        drop_sql = MANTICORE_DROP_TABLE.format(table_name=MANTICORE_TABLE)
        requests.post(sql_url, data={"mode": "raw", "query": drop_sql})

    logger.info("Проверяем/создаем таблицу в Manticore Search...")
    create_sql = MANTICORE_CREATE_TABLE.format(table_name=MANTICORE_TABLE)

    response = requests.post(sql_url, data={"mode": "raw", "query": create_sql})

    if response.status_code != 200 and "already exists" not in response.text:
        logger.warning(f"Ответ при создании таблицы: {response.text}")

    try:
        data = response.json()
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            error_msg = data[0].get("error")
            if error_msg:
                logger.error(f"Критическая ошибка создания таблицы: {error_msg}")
                sys.exit(1)
    except Exception:
        pass


def fetch_from_mysql() -> List[Dict[str, Any]]:
    """Выполняет запрос к базе MySQL"""
    logger.info("Подключение к MySQL...")
    connection = pymysql.connect(**MYSQL_CONFIG)
    try:
        with connection.cursor() as cursor:
            cursor.execute(MYSQL_SELECT_DOCUMENTS)
            rows = cursor.fetchall()
            logger.info(f"Получено строк из MySQL: {len(rows)}")
            return rows
    finally:
        connection.close()


def _extract_semantic_text(
    pagetitle: str, description: str, intro: str, content: str
) -> str:
    """Сборка данных для нейросети."""
    parts = [pagetitle]
    if description:
        parts.append(description)
    if intro:
        parts.append(intro)
    elif content:
        parts.append(content[:400])

    semantic_text = ". ".join(parts)
    return f"passage: {semantic_text}"[:1000]


def _build_manticore_doc(doc: Dict[str, Any], vector: list[float]) -> Dict[str, Any]:
    """Формирует JSON-документ для Bulk-вставки в Manticore."""
    return {
        "insert": {
            "table": MANTICORE_TABLE,
            "id": doc["id"],
            "doc": {
                "pagetitle": doc["clean_pagetitle"],
                "longtitle": strip_html(doc.get("longtitle")),
                "menutitle": strip_html(doc.get("menutitle")),
                "description": strip_html(doc.get("description")),
                "introtext": doc["clean_intro"],
                "content": doc["clean_content"],
                "url": doc["full_url"],
                "lang": doc["lang"],
                "alias": str(doc.get("alias") or "").strip(),
                "parent": int(doc.get("parent") or 0),
                "content_vector": vector,
            },
        }
    }


def process_documents(all_docs: List[Dict[str, Any]], embedder) -> List[Dict[str, Any]]:
    docs_dict = {doc["id"]: doc for doc in all_docs}
    valid_docs = []
    texts_for_vector = []

    for doc in tqdm(all_docs, desc="1/3 Очистка HTML и сбор данных", unit="doc"):
        if not (
            doc["searchable"] == 1
            and doc["privateweb"] == 0
            and doc["type"] in ["document", "reference"]
        ):
            continue

        full_path = build_url(doc["id"], docs_dict)
        doc["full_url"] = f"https://etu.ru/{full_path}"
        doc["lang"] = determine_lang(full_path)

        pagetitle = strip_html(doc.get("pagetitle"))
        description = strip_html(doc.get("description"))
        clean_intro = truncate(strip_html(doc.get("introtext")))
        clean_content = truncate(strip_html(doc.get("content")))

        doc["clean_pagetitle"] = pagetitle
        doc["clean_intro"] = clean_intro
        doc["clean_content"] = clean_content

        text_for_vector = _extract_semantic_text(
            pagetitle, description, clean_intro, clean_content
        )

        valid_docs.append(doc)
        texts_for_vector.append(text_for_vector)

    if not valid_docs:
        return []

    logger.info(f"Начинаем векторизацию {len(valid_docs)} статей...")

    vectors_generator = embedder.embed(texts_for_vector, batch_size=32)

    documents_to_insert = [
        _build_manticore_doc(doc, vector.tolist())
        for doc, vector in zip(
            valid_docs,
            tqdm(
                vectors_generator,
                total=len(valid_docs),
                desc="2/3 Нейросетевая векторизация",
                unit="doc",
            ),
        )
    ]

    return documents_to_insert


def index_documents(documents: List[Dict[str, Any]]) -> None:
    """Отправляет документы в Manticore батчами"""
    bulk_url = f"{MANTICORE_URL}/bulk"
    batches = [
        documents[i : i + CHUNK_SIZE] for i in range(0, len(documents), CHUNK_SIZE)
    ]

    errors = 0
    with requests.Session() as session:
        for batch in tqdm(batches, desc="3/3 Импорт в Manticore", unit="батч"):
            bulk_data = "\n".join(json.dumps(item) for item in batch)
            response = session.post(
                bulk_url,
                data=bulk_data,
                headers={"Content-Type": "application/x-ndjson"},
            )

            if response.status_code != 200 or '"errors":true' in response.text:
                errors += 1
                try:
                    resp_data = response.json()
                    if "items" in resp_data:
                        err_msg = next(
                            (
                                item["insert"]["error"]
                                for item in resp_data["items"]
                                if "error" in item.get("insert", {})
                            ),
                            "Неизвестно",
                        )
                        logger.error(f"Ошибка вставки: {err_msg}")
                except Exception:
                    logger.error(f"Сырой ответ Manticore: {response.text[:200]}")

    if errors > 0:
        logger.error(f"Произошли ошибки при импорте в {errors} батчах.")
    else:
        logger.info("Импорт завершён без ошибок.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recreate", action="store_true", help="Удалить и создать таблицу заново"
    )
    args = parser.parse_args()

    start_time = time.time()
    logger.info(f"Загрузка модели {EMBEDDER_MODEL_NAME} ...")

    embedder = TextEmbedding(model_name=EMBEDDER_MODEL_NAME, cache_dir=MODEL_CACHE_DIR)

    setup_manticore_table(recreate=args.recreate)

    rows = fetch_from_mysql()
    if not rows:
        logger.error("MySQL вернул 0 строк. Выход.")
        sys.exit(1)

    documents_to_insert = process_documents(rows, embedder)

    if documents_to_insert:
        index_documents(documents_to_insert)

    logger.info(f"Готово за {time.time() - start_time:.1f} сек.")


if __name__ == "__main__":
    main()
