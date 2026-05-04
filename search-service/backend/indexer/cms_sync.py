import logging
from contextlib import closing
from datetime import datetime

import pymysql
from bs4 import BeautifulSoup

from config import Settings

from .exceptions import DatabaseExtractionError
from .filters import filter_valid_documents

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

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

TV_IDS = {
    58: "tv_meta_description",
    59: "tv_meta_keywords",
    65: "tv_meta_title",
    66: "tv_persons",
    87: "tv_author",
    108: "tv_position",
}


def _clean_html(html: str | None) -> str:
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return html


def _parse_persons(raw: str | None) -> str:
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


def _get_language(doc_id: int, parent_map: dict) -> str | None:
    current_id = doc_id
    for _ in range(20):
        if current_id in LANG_ROOTS:
            return LANG_ROOTS[current_id]
        parent = parent_map.get(current_id)
        if parent is None or parent == 0:
            return None
        current_id = parent
    return None


def _get_breadcrumbs(doc_id: int, parent_map: dict, title_map: dict) -> list[str]:
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


def _get_url_path(doc_id: int, parent_map: dict, alias_map: dict) -> str:
    parts = []
    current_id = doc_id
    for _ in range(20):
        if not current_id or current_id == 0:
            break
        alias = alias_map.get(current_id, "")
        if alias:
            parts.append(alias)
        if current_id in LANG_ROOTS:
            break
        current_id = parent_map.get(current_id, 0)
    parts.reverse()
    return "/".join(parts) + "/"


class CMSExtractor:
    def __init__(self, settings: Settings, table_name: str = "modx_site_content"):
        self.db_config = {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD,
            "database": settings.DB_NAME,
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
        }
        self.table_name = table_name

    def extract_data(self) -> list[dict]:
        return self._extract()

    def extract_since(self, last_ts: int) -> list[dict]:
        return self._extract(since_ts=last_ts)

    def _extract(self, since_ts: int | None = None) -> list[dict]:
        logger.info("Connecting to database '%s'...", self.db_config["database"])
        try:
            with closing(pymysql.connect(**self.db_config)) as conn:
                with conn.cursor() as cursor:
                    parent_map, title_map, alias_map = self._fetch_hierarchy(cursor)
                    rows = self._fetch_content(cursor, since_ts)
                    tv_map = self._fetch_tv_values(cursor)

            return self._process(rows, parent_map, title_map, alias_map, tv_map)

        except pymysql.MySQLError as e:
            raise DatabaseExtractionError(
                f"Failed to extract data from {self.table_name}"
            ) from e

    def _fetch_hierarchy(self, cursor) -> tuple[dict, dict, dict]:
        cursor.execute(
            f"SELECT id, parent, pagetitle, alias FROM {self.table_name} "
            "WHERE deleted = 0 AND published = 1"
        )
        rows = cursor.fetchall()
        parent_map = {row["id"]: row["parent"] for row in rows}
        title_map = {row["id"]: row["pagetitle"] for row in rows}
        alias_map = {row["id"]: row["alias"] for row in rows}
        logger.info("Loaded hierarchy: %d documents.", len(rows))
        return parent_map, title_map, alias_map

    def _fetch_content(self, cursor, since_ts: int | None = None) -> list[dict]:
        where = "WHERE deleted = 0 AND published = 1 AND searchable = 1"
        params: list = []
        if since_ts is not None:
            where += " AND (editedon > %s OR createdon > %s)"
            params.extend([since_ts, since_ts])

        cursor.execute(
            f"""
            SELECT
                id, pagetitle, longtitle, description,
                introtext, content, alias, menutitle,
                published, deleted, parent, template,
                isfolder, searchable, hidemenu,
                publishedon, createdon, editedon, menuindex, hitcount
            FROM {self.table_name}
            {where}
            """,
            params or None,
        )
        rows = cursor.fetchall()
        logger.info("Fetched %d content rows.", len(rows))
        return rows

    def _fetch_tv_values(self, cursor) -> dict:
        placeholders = ",".join(["%s"] * len(TV_IDS))
        cursor.execute(
            f"""
            SELECT contentid, tmplvarid, value
            FROM modx_site_tmplvar_contentvalues
            WHERE tmplvarid IN ({placeholders})
              AND value IS NOT NULL AND value != ''
            """,
            list(TV_IDS.keys()),
        )
        tv_rows = cursor.fetchall()
        logger.info("Loaded %d TV values.", len(tv_rows))

        tv_map: dict = {}
        for row in tv_rows:
            field = TV_IDS.get(row["tmplvarid"])
            if not field:
                continue
            val = (
                _parse_persons(row["value"]) if field == "tv_persons" else row["value"]
            )
            if val:
                tv_map.setdefault(row["contentid"], {})[field] = val
        return tv_map

    def _process(
        self,
        rows: list[dict],
        parent_map: dict,
        title_map: dict,
        alias_map: dict,
        tv_map: dict,
    ) -> list[dict]:
        rows = filter_valid_documents(rows)
        result = []
        for row in rows:
            row["content"] = _clean_html(row["content"])
            row["introtext"] = _clean_html(row["introtext"])
            row["description"] = _clean_html(row["description"])

            row["parent_title"] = title_map.get(row["parent"], "")
            row["breadcrumbs"] = _get_breadcrumbs(row["id"], parent_map, title_map)
            row["breadcrumbs_str"] = " › ".join(row["breadcrumbs"])
            row["url_path"] = _get_url_path(row["id"], parent_map, alias_map)
            if row["id"] in LANG_ROOTS:
                continue
            lang = _get_language(row["id"], parent_map)
            if lang is None:
                continue
            row["lang"] = lang

            if row.get("publishedon"):
                row["published_year"] = str(
                    datetime.fromtimestamp(row["publishedon"]).year
                )
            elif row.get("createdon"):
                row["published_year"] = str(
                    datetime.fromtimestamp(row["createdon"]).year
                )
            else:
                row["published_year"] = ""

            tv_fields = tv_map.get(row["id"], {})
            for field in TV_IDS.values():
                row[field] = tv_fields.get(field, "")

            result.append(row)

        logger.info("Processed %d documents.", len(result))
        return result
