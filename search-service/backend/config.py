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

    # base for makeing urls
    SITE_URL: str = "https://etu.ru"

    MEILI_URL: str
    MEILI_API_KEY: str
    MEILI_INDEX: str
    MEILI_SEMANTIC_RATIO: float

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@cache
def get_settings() -> Settings:
    return Settings()
