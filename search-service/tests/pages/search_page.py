from playwright.sync_api import Page, Locator
from .base_page import BasePage


class SearchPage(BasePage):
    def __init__(self, page: Page, base_url: str):
        super().__init__(page, base_url)

        # локаторы
        self.search_input: Locator = page.locator(".search-input")
        self.search_btn: Locator = page.locator(".btn-search")
        self.reset_btn: Locator = page.locator(".reset-btn")
        self.results: Locator = page.locator(".result-card")
        self.date_from_input: Locator = page.locator(
            "input[type='date']").first
        self.date_to_input: Locator = page.locator("input[type='date']").nth(1)

    def open(self, query: str = "", params: str = ""):
        """открывает страницу поиска с опциональными параметрами url"""
        url = self.base_url
        query_string = []
        if query:
            query_string.append(f"q={query}")
        if params:
            query_string.append(params)

        if query_string:
            url += "?" + "&".join(query_string)

        if query_string:
            self._do_with_search_wait(lambda: self.page.goto(url))
        else:
            self.page.goto(url)

    def search(self, text: str):
        """ввод текста и клик по кнопке поиска"""
        self.search_input.fill(text)
        self._do_with_search_wait(self.search_btn.click)

    def toggle_language(self, lang_code: str):
        """включает/выключает язык"""
        btn = self.page.locator("button.lang-btn", has_text=lang_code)
        self._do_with_search_wait(btn.click)

    def select_period(self, period_value: str):
        """выбирает период (month, year, 3years)"""
        radio = self.page.locator(f"input[value='{period_value}']")
        self._do_with_search_wait(radio.check)

    def fill_custom_dates(self, from_date: str, to_date: str = ""):
        """заполняет ручной диапазон дат"""
        if from_date:
            self._do_with_search_wait(
                lambda: self.date_from_input.fill(from_date))
        if to_date:
            self._do_with_search_wait(lambda: self.date_to_input.fill(to_date))

    def click_reset(self):
        """нажимает кнопку сброса фильтров"""
        self._do_with_search_wait(self.reset_btn.click)

    def get_language_btn(self, lang_code: str) -> Locator:
        return self.page.locator("button.lang-btn", has_text=lang_code)

    def get_period_radio(self, period_value: str) -> Locator:
        return self.page.locator(f"input[value='{period_value}']")
