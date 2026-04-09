#!/usr/bin/env python3

import argparse
import html
import re
import sys
import time

import mysql.connector
import typesense
from bs4 import BeautifulSoup
from tqdm import tqdm

from config import (
    COLLECTION_SCHEMA,
    IMPORT_BATCH_SIZE,
    MYSQL_COLUMNS,
    MYSQL_CONFIG,
    MYSQL_TABLE,
    MYSQL_WHERE,
    TYPESENSE_COLLECTION,
    TYPESENSE_CONFIG,
)
from lemmatizer import lemmatize_document


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    text = BeautifulSoup(raw, "lxml").get_text(separator=" ")
    return html.unescape(re.sub(r"\s+", " ", text).strip())


def truncate(text: str, max_chars: int = 50_000) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def clean_document(row: dict) -> dict:
    # Оригинальные поля (для эмбеддингов)
    pagetitle = (row["pagetitle"] or "").strip()
    longtitle = (row["longtitle"] or "").strip()
    description = (row["description"] or "").strip()
    introtext = truncate(strip_html(row.get("introtext")))
    content = truncate(strip_html(row.get("content")))
    alias = (row.get("alias") or "").strip()

    # Лемматизированные поля
    lemm_fields = lemmatize_document(
        pagetitle=pagetitle,
        longtitle=longtitle,
        description=description,
        introtext=introtext,
        content=content,
        alias=alias,
    )
    # lemm_fields содержит:
    #   pagetitle_lemm, longtitle_lemm, description_lemm,
    #   introtext_lemm, content_lemm, lang

    doc = {
        "id": str(row["id"]),
        "pagetitle": pagetitle,
        "longtitle": longtitle,
        "description": description,
        "introtext": introtext,
        "content": content,
        "alias": alias,
        "parent": int(row.get("parent") or 0),
        "template": int(row.get("template") or 0),
        "published": int(row.get("published") or 0),
        "deleted": int(row.get("deleted") or 0),
    }
    doc.update(lemm_fields)

    return doc


def fetch_from_mysql() -> list[dict]:
    print("Подключение к MySQL...")
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)
    columns = ", ".join(MYSQL_COLUMNS)
    query = f"SELECT {columns} FROM {MYSQL_TABLE} WHERE {MYSQL_WHERE}"
    print(f"SQL: {query}")
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    print(f"Получено строк: {len(rows)}")
    return rows


def get_client() -> typesense.Client:
    return typesense.Client(TYPESENSE_CONFIG)


def create_collection(client: typesense.Client, recreate: bool) -> None:
    try:
        client.collections[TYPESENSE_COLLECTION].retrieve()
        exists = True
    except typesense.exceptions.ObjectNotFound:
        exists = False

    if exists:
        if recreate:
            print(f"Удаляем коллекцию '{TYPESENSE_COLLECTION}'...")
            client.collections[TYPESENSE_COLLECTION].delete()
        else:
            print(f"Коллекция '{TYPESENSE_COLLECTION}' уже существует.")
            return

    print(f"Создаём коллекцию '{TYPESENSE_COLLECTION}'...")
    client.collections.create(COLLECTION_SCHEMA)


def import_documents(client: typesense.Client, rows: list[dict]) -> None:
    print(f"\nПодготовка и лемматизация {len(rows)} документов...")
    print(
        "(spaCy загружает модели при первом вызове — это может занять несколько секунд)\n"
    )

    documents = []
    for row in tqdm(rows, desc="Лемматизация", unit="doc"):
        documents.append(clean_document(row))

    # Статистика по языкам
    lang_counts: dict[str, int] = {}
    for doc in documents:
        lang = doc.get("lang", "?")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    print(f"\nОпределённые языки: { {k: v for k, v in sorted(lang_counts.items())} }")

    errors = []
    batches = [
        documents[i : i + IMPORT_BATCH_SIZE]
        for i in range(0, len(documents), IMPORT_BATCH_SIZE)
    ]

    for batch in tqdm(batches, desc="Импорт в Typesense", unit="батч"):
        results = client.collections[TYPESENSE_COLLECTION].documents.import_(
            batch, {"action": "upsert"}
        )
        for item in results:
            if not item.get("success"):
                errors.append(item)

    if errors:
        print(f"Ошибок при импорте: {len(errors)}")
        for e in errors[:5]:
            print(f"  {e}")
    else:
        print("Импорт завершён без ошибок.")


def main():
    parser = argparse.ArgumentParser(
        description="Создаёт коллекцию Typesense и импортирует документы из MySQL."
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Удалить существующую коллекцию и создать заново.",
    )
    args = parser.parse_args()

    start = time.time()

    rows = fetch_from_mysql()
    if not rows:
        print("MySQL вернул 0 строк.")
        sys.exit(1)

    client = get_client()
    create_collection(client, recreate=args.recreate)
    import_documents(client, rows)

    print(f"\nГотово за {time.time() - start:.1f} сек.")


if __name__ == "__main__":
    main()
