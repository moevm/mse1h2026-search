import re
from playwright.sync_api import expect
from pages.search_page import SearchPage


def test_default_search_state(search_page: SearchPage, page):
    """проверка дефолтного состояния"""

    search_page.open(query="чистый поиск")

    # url без фильтров
    expect(page).not_to_have_url(re.compile(r"lang="))
    expect(page).not_to_have_url(re.compile(r"date_filter="))
    expect(page).not_to_have_url(re.compile(r"from_date="))

    # кнопка сброса отсутствует
    expect(search_page.reset_btn).not_to_be_attached()

    # языки не активны
    expect(page.locator("button.lang-btn.active")).to_have_count(0)


def test_deep_linking_initialization(search_page: SearchPage, page):
    """проверка открытия страницы по прямой ссылке с фильтрами"""

    search_page.open(query="тест", params="lang=CN&lang=SP&date_filter=year")

    # проверяем активность фильтров
    expect(search_page.get_language_btn("CN")
           ).to_have_class(re.compile(r"active"))
    expect(search_page.get_language_btn("SP")
           ).to_have_class(re.compile(r"active"))

    expect(search_page.get_period_radio("year")).to_be_checked()

    expect(search_page.reset_btn).to_be_visible()


def test_deep_linking_custom_dates(search_page: SearchPage, page):
    """проверка прямых ссылок с кастомными датами"""

    search_page.open(
        query="тест", params="from_date=2023-05-10&to_date=2024-05-10")
    expect(search_page.date_from_input).to_have_value("2023-05-10")
    expect(search_page.date_to_input).to_have_value("2024-05-10")

    expect(page.locator("input[type='radio']:checked")).to_have_count(0)
