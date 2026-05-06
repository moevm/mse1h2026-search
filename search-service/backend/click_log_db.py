from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

import psycopg

from config import Settings


class ClickLogRepository:
    def __init__(self, settings: Settings) -> None:
        self._conninfo = (
            f"host={settings.CLICK_DB_HOST} "
            f"port={settings.CLICK_DB_PORT} "
            f"dbname={settings.CLICK_DB_NAME} "
            f"user={settings.CLICK_DB_USER} "
            f"password={settings.CLICK_DB_PASSWORD}"
        )

    def init_schema(self) -> None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS click_log (
                        record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        query TEXT NOT NULL,
                        position INTEGER NOT NULL,
                        link TEXT NOT NULL
                    )
                    """
                )
            conn.commit()

    def save_click(self, query: str, position: int, link: str) -> None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO click_log (timestamp, query, position, link)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (datetime.now(UTC), query, position, link),
                )
            conn.commit()


def is_allowed_redirect_target(link: str) -> bool:
    parsed = urlparse(link)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
