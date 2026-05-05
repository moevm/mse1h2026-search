from playwright.sync_api import Page
from typing import Callable


class BasePage:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def _do_with_search_wait(self, action: Callable):
        with self.page.expect_response("**/api/search**"):
            action()
