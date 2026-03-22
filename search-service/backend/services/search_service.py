import functools

from fastapi import Depends

from config import Settings, get_settings
from services.providers.base import BaseSearchProvider
from services.providers.mock_provider import MockProvider


@functools.cache
def _get_cached_provider(provider_type: str) -> BaseSearchProvider:
    match provider_type:
        case "mock":
            return MockProvider()
        case _:
            raise ValueError(
                f"Unknown SEARCH_PROVIDER: {provider_type!r}. Expected: 'mock'"
            )


def get_provider(settings: Settings = Depends(get_settings)) -> BaseSearchProvider:
    return _get_cached_provider(settings.SEARCH_PROVIDER)
