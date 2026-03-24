import argparse
import html
import re
import sys
import time
import pymysql
import requests
import json
from typing import Dict, List, Any

from bs4 import BeautifulSoup
from tqdm import tqdm


from config import (
    MYSQL_CONFIG, MANTICORE_URL, MANTICORE_TABLE, CHUNK_SIZE, logger
)
from queries import (
    MANTICORE_CREATE_TABLE, MYSQL_SELECT_DOCUMENTS, MANTICORE_DROP_TABLE
)


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""

    raw = re.sub(r'\[\[.*?\]\]', ' ', raw, flags=re.DOTALL)
    raw = re.sub(r'\[\*.*?\*\]', ' ', raw, flags=re.DOTALL)
    raw = re.sub(r'\[\+.*?\+\]', ' ', raw, flags=re.DOTALL)

    if raw.startswith(('http://', 'https://')):
        return raw.strip()

    if '<' in raw:
        soup = BeautifulSoup(raw, "lxml")
        for tag in soup(['script', 'style', 'iframe', 'noscript']):
            tag.decompose()
        text = soup.get_text(separator=" ")
    else:
        text = raw

    text = text.replace("Ваш браузер не поддерживает iframe!", " ")

    clean_text = html.unescape(text)
    return re.sub(r"\s+", " ", clean_text).strip()


def truncate(text: str, max_chars: int = 50_000) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def build_url(doc_id: int, docs_dict: Dict[int, Any]) -> str:
    """Рекурсивно строит полный путь страницы (url)"""
    if doc_id == 0 or doc_id not in docs_dict:
        return ""

    doc = docs_dict[doc_id]
    parent_url = build_url(doc['parent'], docs_dict)

    if parent_url:
        return f"{parent_url}/{doc['alias']}"
    return doc['alias']


def determine_lang(url: str) -> str:
    """Определяет язык документа на основе языкового префикса в URL"""
    languages = ['ar', 'cn', 'de', 'en', 'fr', 'pt', 'ru', 'es', 'vn']
    for l in languages:
        if url.startswith(f"{l}/"):
            return l
    return 'ru'


def setup_manticore_table(recreate: bool) -> None:
    sql_url = f"{MANTICORE_URL}/sql"

    if recreate:
        logger.info(f"Удаляем таблицу '{MANTICORE_TABLE}' (--recreate)...")
        drop_sql = MANTICORE_DROP_TABLE.format(table_name=MANTICORE_TABLE)
        requests.post(
            sql_url, data={'mode': 'raw', 'query': drop_sql}
        )

    logger.info("Проверяем/создаем таблицу в Manticore Search...")
    create_sql = MANTICORE_CREATE_TABLE.format(table_name=MANTICORE_TABLE)

    response = requests.post(
        sql_url, data={'mode': 'raw', 'query': create_sql})
    if response.status_code != 200 and "already exists" not in response.text:
        logger.warning(f"Ответ при создании таблицы: {response.text}")

    try:
        data = response.json()
        if isinstance(data, list) and len(data) > 0 and data[0].get('error'):
            logger.error(
                f"Критическая ошибка создания таблицы: {data[0]['error']}")
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


def process_documents(all_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs_dict = {doc['id']: doc for doc in all_docs}
    documents_to_insert = []

    for doc in tqdm(all_docs, desc="Подготовка документов", unit="doc"):
        is_searchable = doc['searchable'] == 1 and doc['privateweb'] == 0
        if is_searchable and doc['type'] in ['document', 'reference']:
            full_path = build_url(doc['id'], docs_dict)
            full_url = f"https://etu.ru/{full_path}"
            lang = determine_lang(full_path)

            clean_intro = truncate(strip_html(doc.get('introtext')))
            clean_content = truncate(strip_html(doc.get('content')))

            manticore_doc = {
                "insert": {
                    "table": MANTICORE_TABLE,
                    "id": doc['id'],
                    "doc": {
                        "pagetitle": strip_html(doc.get('pagetitle')),
                        "longtitle": strip_html(doc.get('longtitle')),
                        "menutitle": strip_html(doc.get('menutitle')),
                        "description": strip_html(doc.get('description')),
                        "introtext": clean_intro,
                        "content": clean_content,
                        "url": full_url,
                        "lang": lang,
                        "alias": (doc.get('alias') or "").strip(),
                        "parent": int(doc.get('parent') or 0)
                    }
                }
            }
            documents_to_insert.append(manticore_doc)

    return documents_to_insert


def index_documents(documents: List[Dict[str, Any]]) -> None:
    """
    Отправляет документы в manticore
    """
    bulk_url = f"{MANTICORE_URL}/bulk"
    batches = [documents[i: i + CHUNK_SIZE]
               for i in range(0, len(documents), CHUNK_SIZE)]

    errors = 0
    with requests.Session() as session:
        for batch in tqdm(batches, desc="Импорт в Manticore", unit="батч"):
            bulk_data = "\n".join(json.dumps(item) for item in batch)
            response = session.post(
                bulk_url,
                data=bulk_data,
                headers={'Content-Type': 'application/x-ndjson'}
            )
            if response.status_code != 200 or '"errors":true' in response.text:
                errors += 1
                try:
                    resp_data = response.json()
                    if 'items' in resp_data:
                        err_msg = next((item['insert']['error'] for item in resp_data['items'] if 'error' in item.get(
                            'insert', {})), "Неизвестно")
                        logger.error(f"Ошибка вставки: {err_msg}")
                except Exception:
                    logger.error(
                        f"Сырой ответ Manticore: {response.text[:200]}")

    if errors > 0:
        logger.error(f"Произошли ошибки при импорте в {errors} батчах.")
    else:
        logger.info("Импорт завершён без ошибок.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recreate", action="store_true",
                        help="Удалить и создать таблицу заново")
    args = parser.parse_args()

    start_time = time.time()

    setup_manticore_table(recreate=args.recreate)

    rows = fetch_from_mysql()
    if not rows:
        logger.error("MySQL вернул 0 строк. Выход.")
        sys.exit(1)

    documents_to_insert = process_documents(rows)
    index_documents(documents_to_insert)

    logger.info(f"Готово за {time.time() - start_time:.1f} сек.")


if __name__ == "__main__":
    main()
