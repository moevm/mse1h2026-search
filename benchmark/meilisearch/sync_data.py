import pymysql
import meilisearch
import os
import json
import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from tqdm import tqdm

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root_password"),
    "database": os.getenv("DB_NAME", "unidb"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

MEILI_URL = os.getenv("MEILI_URL", "http://localhost:7700")
MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

LANG_ROOTS = {
    1: "ru",
    4020: "en",
    10686: "de",
    12119: "sp",
    13181: "pt",
    13687: "fr",
    14296: "vn",
    14602: "ar",
    14809: "cn",
}


def clean_html(html_content):
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text
    except Exception:
        return html_content


def get_language(doc_id, parent_map):
    """Определяет код языка по дереву родителей"""
    current_id = doc_id
    for _ in range(20):
        if current_id in LANG_ROOTS:
            return LANG_ROOTS[current_id]

        parent = parent_map.get(current_id)
        if parent is None or parent == 0:
            return None
        current_id = parent
    return None


def get_breadcrumbs(doc_id, parent_map, title_map):
    breadcrumbs = []
    current_id = parent_map.get(doc_id)
    for _ in range(20):
        if not current_id or current_id == 0:
            break
        if current_id not in LANG_ROOTS:
            title = title_map.get(current_id)
            if title:
                breadcrumbs.append(title)
        current_id = parent_map.get(current_id)
    return breadcrumbs[::-1]


TV_IDS = {
    58: "tv_meta_description",
    59: "tv_meta_keywords",
    65: "tv_meta_title",
    66: "tv_persons",
    87: "tv_author",
    108: "tv_position",
}


def parse_persons(raw):
    """persons TV: записи через '||', поля внутри через '::' (img, name, position, degree, phone, email, room, _, id)"""
    if not raw:
        return ""
    parts = []
    for entry in raw.split("||"):
        fields = entry.split("::")
        name = fields[1].strip() if len(fields) > 1 else ""
        position = fields[2].strip() if len(fields) > 2 else ""
        degree = fields[3].strip() if len(fields) > 3 else ""
        chunk = " ".join(x for x in (name, position, degree) if x)
        if chunk:
            parts.append(chunk)
    return " | ".join(parts)


def fetch_tv_values(cursor, content_ids):
    """Возвращает {content_id: {tv_field_name: value}} для заданных TV"""
    if not content_ids:
        return {}
    tv_ids_placeholder = ",".join(str(i) for i in TV_IDS.keys())
    cursor.execute(f"""
        SELECT contentid, tmplvarid, value
        FROM modx_site_tmplvar_contentvalues
        WHERE tmplvarid IN ({tv_ids_placeholder})
          AND value IS NOT NULL AND value != ''
    """)
    tv_rows = cursor.fetchall()
    print(f"Загружено TV значений: {len(tv_rows)}")

    tv_map = {}
    for row in tv_rows:
        cid = row["contentid"]
        field = TV_IDS.get(row["tmplvarid"])
        if not field:
            continue
        val = row["value"]
        if field == "tv_persons":
            val = parse_persons(val)
        if not val:
            continue
        tv_map.setdefault(cid, {})[field] = val
    return tv_map


# экспериментально
def get_page_weight(template_id):
    """Определяет вес страницы для бустинга в поиске на основе шаблона MODX"""
    if template_id in [301, 302, 303]:
        return 10
    elif template_id in [261, 306, 307]:
        return 8
    elif template_id == 304:
        return 3
    elif template_id == 305:
        return 1
    return 1


def fetch_data_from_mysql():
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            print("Загрузка иерархии документов...")
            cursor.execute(
                "SELECT id, parent, pagetitle FROM modx_site_content WHERE deleted = 0 AND published = 1 AND searchable = 1"
            )
            hierarchy = cursor.fetchall()
            parent_map = {row["id"]: row["parent"] for row in hierarchy}
            title_map = {row["id"]: row["pagetitle"] for row in hierarchy}

            sql = """
            SELECT 
                id, pagetitle, longtitle, description, 
                introtext, content, alias, menutitle,
                published, deleted, parent, template, 
                isfolder, searchable, hidemenu,
                publishedon, createdon, editedon, menuindex,
                hitcount
            FROM modx_site_content
            WHERE deleted = 0 AND published = 1 AND searchable = 1
            """
            print("Извлечение основного контента...")
            cursor.execute(sql)
            rows = cursor.fetchall()
            print(f"Всего строк: {len(rows)}")

            print("Загрузка TV значений...")
            tv_map = fetch_tv_values(cursor, [row["id"] for row in rows])

            lang_data = {lang: [] for lang in LANG_ROOTS.values()}
            lang_data["other"] = []

            print("Обработка и распределение по языкам...")
            for row in tqdm(rows):
                lang = get_language(row["id"], parent_map)

                # Очистка контента
                row["content"] = clean_html(row["content"])
                row["introtext"] = clean_html(row["introtext"])
                row["description"] = clean_html(row["description"])
                row["pagetitle"] = clean_html(row["pagetitle"])
                row["longtitle"] = clean_html(row["longtitle"])
                row["menutitle"] = clean_html(row["menutitle"])

                # название родителя для контекста (например: Контакты -> Кафедра физики)
                parent_id = row["parent"]
                row["parent_title"] = title_map.get(parent_id, "")

                # хлебные крошки (массив названий всех предков)
                row["breadcrumbs"] = get_breadcrumbs(row["id"], parent_map, title_map)
                row["breadcrumbs_str"] = " › ".join(row["breadcrumbs"])

                # сезонность / год
                if row["publishedon"]:
                    row["published_year"] = str(
                        datetime.datetime.fromtimestamp(row["publishedon"]).year
                    )
                elif row["createdon"]:
                    row["published_year"] = str(
                        datetime.datetime.fromtimestamp(row["createdon"]).year
                    )
                else:
                    row["published_year"] = ""

                # вес страницы на основе шаблона
                row["page_weight"] = get_page_weight(row["template"])

                # поля из Template Variables
                tv_fields = tv_map.get(row["id"], {})
                for field in TV_IDS.values():
                    val = tv_fields.get(field, "")
                    if field == "tv_meta_title":
                        val = clean_html(val)
                    row[field] = val

                if lang:
                    lang_data[lang].append(row)
                else:
                    lang_data["other"].append(row)

            return lang_data
    finally:
        connection.close()


def sync_to_meilisearch(lang_data):
    key = MEILI_MASTER_KEY if MEILI_MASTER_KEY else None
    client = meilisearch.Client(MEILI_URL, key)

    general_index_name = "site_content"
    general_index = client.index(general_index_name)

    all_docs = []

    for lang, docs in lang_data.items():
        if not docs or lang == "other":
            if docs:
                all_docs.extend(docs)
            continue

        index_name = f"site_{lang}"
        index = client.index(index_name)

        print(f"Синхронизация {index_name} ({len(docs)} док.)...")

        batch_size = 5000
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            index.add_documents(batch)
            print(f"  [{lang}] Отправлена пачка {i} - {i + len(batch)}")

        all_docs.extend(docs)

    if all_docs:
        print(
            f"\nСинхронизация общего индекса {general_index_name} ({len(all_docs)} док.)..."
        )
        batch_size = 5000
        for i in range(0, len(all_docs), batch_size):
            batch = all_docs[i : i + batch_size]
            general_index.add_documents(batch)
            print(f"  [general] Отправлена пачка {i} - {i + len(batch)}")

    print("\nСинхронизация всех индексов завершена!")


if __name__ == "__main__":
    try:
        data_by_lang = fetch_data_from_mysql()
        if data_by_lang:
            sync_to_meilisearch(data_by_lang)
    except Exception as e:
        print(f"Ошибка: {e}")
