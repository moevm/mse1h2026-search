import logging
import os
import re
import sys
from contextlib import closing
from pathlib import Path

import pymysql
import pytest
from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
DB_COMPOSE_FILE = Path(__file__).resolve().parents[2] / "db" / "docker-compose.yml"
sys.path.insert(0, str(BACKEND_DIR))

from config import Settings
from indexer.cms_sync import (
    CMSExtractor,
    LANG_ROOTS,
    _get_language,
    _get_url_path,
)

logger = logging.getLogger(__name__)
TABLE_NAME = "modx_site_content"
SAMPLE_SIZE = int(os.getenv("INDEXING_CHECK_SAMPLE_SIZE", "10"))
LOG_SAMPLE_SIZE = min(SAMPLE_SIZE, 2)


@pytest.fixture(scope="session")
def backend_settings() -> Settings:
    env_values = dotenv_values(BACKEND_DIR / ".env")
    for key, value in env_values.items():
        if key in Settings.model_fields and value is not None:
            os.environ.setdefault(key, value)

    settings = Settings()
    if _is_running_on_host():
        db_host, db_port = _local_db_from_compose()
        settings = settings.model_copy(update={"DB_HOST": db_host, "DB_PORT": db_port})
    return settings


@pytest.fixture(scope="session")
def cms_extractor(backend_settings: Settings) -> CMSExtractor:
    return CMSExtractor(backend_settings)


@pytest.fixture(scope="session")
def db_connection(backend_settings: Settings):
    conn = pymysql.connect(
        host=backend_settings.DB_HOST,
        port=backend_settings.DB_PORT,
        user=backend_settings.DB_USER,
        password=backend_settings.DB_PASSWORD,
        database=backend_settings.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    with closing(conn) as active_conn:
        yield active_conn


@pytest.fixture(scope="session")
def hierarchy(cms_extractor: CMSExtractor, db_connection) -> dict:
    with db_connection.cursor() as cursor:
        parent_map, title_map, alias_map, alias_visible_map = cms_extractor._fetch_hierarchy(cursor)
    return {
        "parent_map": parent_map,
        "title_map": title_map,
        "alias_map": alias_map,
        "alias_visible_map": alias_visible_map,
    }


@pytest.fixture(scope="session")
def expected_state(db_connection, hierarchy: dict) -> dict:
    with db_connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, pagetitle, parent, alias, published, deleted, searchable
            FROM {TABLE_NAME}
            """
        )
        rows = cursor.fetchall()

    expected_valid_ids: set[int] = set()
    invalid_reasons: dict[int, list[str]] = {}

    for row in rows:
        doc_id = row["id"]
        reasons = []
        if int(row.get("published") or 0) != 1:
            reasons.append("published!=1")
        if int(row.get("deleted") or 0) == 1:
            reasons.append("deleted=1")
        if int(row.get("searchable") or 0) != 1:
            reasons.append("searchable!=1")
        if doc_id in LANG_ROOTS:
            reasons.append("language-root")
        if not reasons and _get_language(doc_id, hierarchy["parent_map"]) is None:
            reasons.append("no-language-root")

        if reasons:
            invalid_reasons[doc_id] = reasons
        else:
            expected_valid_ids.add(doc_id)

    return {
        "expected_valid_ids": expected_valid_ids,
        "invalid_reasons": invalid_reasons,
    }


@pytest.fixture(scope="session")
def extracted_documents(cms_extractor: CMSExtractor) -> list[dict]:
    documents = cms_extractor.extract_data()
    logger.info("извлечено документов для индексации: %d", len(documents))
    return documents


def test_invalid_records_are_filtered(
    extracted_documents: list[dict],
    expected_state: dict,
):
    extracted_ids = {doc["id"] for doc in extracted_documents}
    expected_valid_ids = expected_state["expected_valid_ids"]
    invalid_reasons = expected_state["invalid_reasons"]

    missing_valid = expected_valid_ids - extracted_ids
    leaked_invalid = extracted_ids & set(invalid_reasons)

    logger.info("ожидаемо валидных записей: %d", len(expected_valid_ids))
    logger.info("отфильтровано невалидных записей: %d", len(invalid_reasons))
    
    for doc_id, reasons in list(invalid_reasons.items())[:LOG_SAMPLE_SIZE]:
        logger.debug("невалидная запись отклонена: id=%s reasons=%s", doc_id, reasons)

    assert not missing_valid
    assert not leaked_invalid


def _full_url(site_url: str, url_path: str) -> str:
    return f"{site_url.rstrip('/')}/{url_path.lstrip('/')}"


def _is_running_on_host() -> bool:
    return not Path("/.dockerenv").exists()


def _local_db_from_compose() -> tuple[str, int]:
    compose_text = DB_COMPOSE_FILE.read_text(encoding="utf-8")
    match = re.search(r'["\']?(\d+):3306["\']?', compose_text)
    if not match:
        raise RuntimeError(f"MySQL port is not found in {DB_COMPOSE_FILE}")
    return "127.0.0.1", int(match.group(1))


def test_url_paths_are_built_from_hierarchy(
    extracted_documents: list[dict],
    hierarchy: dict,
    backend_settings: Settings,
):
    mismatches = []
    for doc in extracted_documents:
        expected_path = _get_url_path(
            doc["id"],
            hierarchy["parent_map"],
            hierarchy["alias_map"],
            hierarchy["alias_visible_map"],
        )
        if doc.get("url_path") != expected_path:
            mismatches.append((doc["id"], doc.get("url_path"), expected_path))

    logger.info("проверено URL: %d", len(extracted_documents))
    
    for doc in extracted_documents[:LOG_SAMPLE_SIZE]:
        logger.debug(
            "url построен: id=%s lang=%s title=%r url=%s",
            doc["id"],
            doc.get("lang"),
            doc.get("pagetitle"),
            _full_url(backend_settings.SITE_URL, doc["url_path"]),
        )

    assert not mismatches
