import pytest
from playwright.sync_api import Page
from pages.search_page import SearchPage

BASE_URL = "http://localhost:6767"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """настройки браузера"""
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        },
        "record_video_size": {
            "width": 1920,
            "height": 1080,
        },
        "device_scale_factor": 2,
    }


@pytest.fixture
def search_page(page: Page) -> SearchPage:
    """фикстура для инициализации страницы поиска"""
    return SearchPage(page, BASE_URL)
