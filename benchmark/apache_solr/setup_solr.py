import pysolr
import requests
import csv
import sys
import html
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
from config import SOLR_URL

csv.field_size_limit(sys.maxsize)


def strip_html_and_images(raw: str | None) -> str:
    if not raw:
        return ""
    raw = re.sub(r'data:image/[^;]+;base64,[^"\' ]+', "", raw)
    text = BeautifulSoup(raw, "lxml").get_text(separator=" ")
    text = html.unescape(re.sub(r"\s+", " ", text).strip())
    return text[:30000]


def setup_schema():
    print("Настройка схемы Solr...")
    fields = [
        {"name": "pagetitle", "type": "text_general", "stored": True},
        {"name": "longtitle", "type": "text_general", "stored": True},
        {"name": "description", "type": "text_general", "stored": True},
        {"name": "introtext", "type": "text_general", "stored": True},
        {"name": "content", "type": "text_general", "stored": True},
        {"name": "alias", "type": "string", "stored": True},
        {"name": "parent", "type": "pint", "stored": True},
        {"name": "template", "type": "pint", "stored": True},
        {"name": "published", "type": "pint", "stored": True},
        {"name": "deleted", "type": "pint", "stored": True},
    ]
    for f in fields:
        requests.post(f"{SOLR_URL}/schema", json={"add-field": f})


def index_from_file():
    solr = pysolr.Solr(SOLR_URL, always_commit=True)
    solr.delete(q="*:*")
    setup_schema()

    encodings = ["utf-16", "utf-8", "cp1251"]
    file_encoding = "utf-8"
    for enc in encodings:
        try:
            with open("data.tsv", "r", encoding=enc) as f:
                f.read(1000)
                file_encoding = enc
                break
        except:
            continue
    print(f"Используем кодировку: {file_encoding}")

    with open("data.tsv", "r", encoding=file_encoding) as f:
        count = sum(1 for _ in f) - 1

    with open("data.tsv", "r", encoding=file_encoding) as f:
        fieldnames = [
            "id",
            "pagetitle",
            "longtitle",
            "description",
            "alias",
            "introtext",
            "content",
            "published",
            "deleted",
            "parent",
            "template",
        ]
        reader = csv.DictReader(f, delimiter="\t", fieldnames=fieldnames)
        next(reader)

        batch = []
        for row in tqdm(reader, total=count, desc="Indexing"):
            try:
                if not row["id"].isdigit():
                    continue

                doc = {
                    "id": row["id"],
                    "pagetitle": (row["pagetitle"] or "").strip(),
                    "longtitle": (row["longtitle"] or "").strip(),
                    "description": (row["description"] or "").strip(),
                    "introtext": strip_html_and_images(row.get("introtext")),
                    "content": strip_html_and_images(row.get("content")),
                    "alias": (row.get("alias") or "").strip(),
                    "parent": int(row.get("parent") or 0),
                    "template": int(row.get("template") or 0),
                    "published": int(row.get("published") or 1),
                    "deleted": int(row.get("deleted") or 0),
                }
                batch.append(doc)
                if len(batch) >= 100:
                    solr.add(batch)
                    batch = []
            except Exception:
                continue
        if batch:
            solr.add(batch)
    print("Готово!")


if __name__ == "__main__":
    index_from_file()
