from functools import cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SEARCH_PROVIDER: str = "mock"

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    CLICK_DB_HOST: str = "127.0.0.1"
    CLICK_DB_PORT: int = 5432
    CLICK_DB_USER: str
    CLICK_DB_PASSWORD: str
    CLICK_DB_NAME: str

    SITE_URL: str = "https://etu.ru"

    SYNC_CRON_INCREMENTAL: str = "0 * * * *"
    SYNC_CRON_FULL: str = "0 3 * * 0"

    DB_QUERY_HIERARCHY: str = "SELECT id AS id, parent AS parent, pagetitle AS pagetitle, alias AS alias, alias_visible AS alias_visible FROM modx_site_content WHERE deleted = 0 AND published = 1"
    DB_QUERY_CONTENT: str = "SELECT id AS id, pagetitle AS pagetitle, longtitle AS longtitle, description AS description, introtext AS introtext, content AS content, alias AS alias, menutitle AS menutitle, published AS published, deleted AS deleted, parent AS parent, template AS template, isfolder AS isfolder, searchable AS searchable, hidemenu AS hidemenu, publishedon AS publishedon, createdon AS createdon, editedon AS editedon, menuindex AS menuindex, hitcount AS hitcount FROM modx_site_content WHERE deleted = 0 AND published = 1 AND searchable = 1"
    DB_QUERY_CONTENT_INC: str = "SELECT id AS id, pagetitle AS pagetitle, longtitle AS longtitle, description AS description, introtext AS introtext, content AS content, alias AS alias, menutitle AS menutitle, published AS published, deleted AS deleted, parent AS parent, template AS template, isfolder AS isfolder, searchable AS searchable, hidemenu AS hidemenu, publishedon AS publishedon, createdon AS createdon, editedon AS editedon, menuindex AS menuindex, hitcount AS hitcount FROM modx_site_content WHERE deleted = 0 AND published = 1 AND searchable = 1 AND (editedon > %s OR createdon > %s)"
    DB_QUERY_TVS: str = "SELECT contentid AS id, tmplvarid AS tv_id, value AS tv_value FROM modx_site_tmplvar_contentvalues WHERE tmplvarid IN ({placeholders}) AND value IS NOT NULL AND value != ''"

    MEILI_URL: str
    MEILI_API_KEY: str
    MEILI_INDEX: str
    MEILI_SEMANTIC_RATIO: float
    MEILI_TASK_TIMEOUT_MS: int = 14_400_000
    MEILI_TASK_INTERVAL_MS: int = 1000
    MEILI_SETTINGS_TIMEOUT_MS: int = 600_000
    MEILI_EMBEDDER_TYPE: str
    MEILI_EMBEDDER_URL: str
    MEILI_EMBEDDER_MODEL: str
    MEILI_EMBEDDER_PREFIX: str = ""
    MEILI_EMBEDDER_MAX_BYTES: int = 2500
    MEILI_EMBEDDER_DIMENSIONS: int

    SYNC_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@cache
def get_settings() -> Settings:
    return Settings()
