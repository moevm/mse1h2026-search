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
    MYSQL_CONFIG,
    MYSQL_TABLE,
    MYSQL_COLUMNS,
    MYSQL_WHERE,
    TYPESENSE_CONFIG,
    TYPESENSE_COLLECTION,
    COLLECTION_SCHEMA,
    IMPORT_BATCH_SIZE,
)


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    text = BeautifulSoup(raw, "lxml").get_text(separator=" ")
    return html.unescape(re.sub(r"\s+", " ", text).strip())


def truncate(text: str, max_chars: int = 50_000) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def clean_document(row: dict) -> dict:
    pagetitle = (row["pagetitle"] or "").strip()
    longtitle = (row["longtitle"] or "").strip()
    description = (row["description"] or "").strip()
    introtext = truncate(strip_html(row.get("introtext")))
    content = truncate(strip_html(row.get("content")))

    return {
        "id": str(row["id"]),
        "pagetitle": pagetitle,
        "longtitle": longtitle,
        "description": description,
        "introtext": introtext,
        "content": content,
        "alias": (row.get("alias") or "").strip(),
        "parent": int(row.get("parent") or 0),
        "template": int(row.get("template") or 0),
        "published": int(row.get("published") or 0),
        "deleted": int(row.get("deleted") or 0),
    }


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
    print(f"\nИндексируем {len(rows)} документов...")
    documents = [
        clean_document(row) for row in tqdm(rows, desc="Подготовка", unit="doc")
    ]

    errors = []
    batches = [
        documents[i : i + IMPORT_BATCH_SIZE]
        for i in range(0, len(documents), IMPORT_BATCH_SIZE)
    ]

    for batch in tqdm(batches, desc="Импорт", unit="батч"):
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--recreate", action="store_true")
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
