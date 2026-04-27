import logging
from contextlib import closing

import pymysql
from config import Settings

from .exceptions import DatabaseExtractionError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CMSExtractor:
    def __init__(
        self,
        settings: Settings,
        table_name: str = "modx_site_content",
        fields: list[str] | None = None
    ):
        self.db_config = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'database': settings.DB_NAME,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }

        self.table_name = table_name
        self.fields = fields or [
            "id", "pagetitle", "longtitle", "description",
            "introtext", "content", "alias", "menutitle",
            "published", "deleted", "parent", "template",
            "isfolder", "searchable", "hidemenu",
            "publishedon", "createdon", "editedon", "menuindex",
            "hitcount"
        ]

    def _build_extract_query(self) -> str:
        fields_str = ", ".join(self.fields)
        return f"SELECT {fields_str} FROM {self.table_name}"

    def extract_data(self) -> list[dict]:
        db_name = self.db_config['database']
        db_host = self.db_config['host']
        logger.info("Connecting to database '%s' at %s...", db_name, db_host)

        try:
            with closing(pymysql.connect(**self.db_config)) as connection:
                with connection.cursor() as cursor:
                    query = self._build_extract_query()

                    logger.info(
                        f"Executing extraction from '{self.table_name}'...")
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    logger.info(f"Successfully extracted {len(rows)} rows.")
                    return rows

        except pymysql.MySQLError as e:
            raise DatabaseExtractionError(
                f"Failed to extract data from {self.table_name}") from e
