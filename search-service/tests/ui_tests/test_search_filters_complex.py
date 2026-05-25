import re
from datetime import datetime
from playwright.sync_api import expect
from pages.search_page import SearchPage


def test_filters_language_combinations_and_reset(search_page: SearchPage, page):
    """сценарий 1: комплексная работа с языками"""

    search_page.open(query="教育")
    search_page.toggle_language("CN")

    expect(page).to_have_url(re.compile(r"lang=CN"))
    expect(search_page.get_language_btn("CN")
           ).to_have_class(re.compile(r"active"))

    search_page.search("нейросети")
    search_page.click_reset()

    expect(page).not_to_have_url(re.compile(r"lang="))
    expect(search_page.get_language_btn("CN")
           ).not_to_have_class(re.compile(r"active"))

    search_page.toggle_language("EN")
    search_page.toggle_language("RU")

    expect(page).to_have_url(re.compile(r"lang=EN"))
    expect(page).to_have_url(re.compile(r"lang=RU"))

    search_page.click_reset()
    search_page.search("o")

    search_page.toggle_language("DE")
    search_page.toggle_language("FR")

    expect(page).to_have_url(re.compile(r"lang=DE"))
    expect(page).to_have_url(re.compile(r"lang=FR"))


def test_filters_date_periods_and_custom_ranges(search_page: SearchPage, page):
    """сценарий 2: комплексная работа с датами"""

    search_page.open(query="алгоритмы")

    periods = ["month", "year", "3years"]
    for period in periods:
        search_page.select_period(period)
        expect(page).to_have_url(re.compile(f"date_filter={period}"))
        expect(search_page.get_period_radio(period)).to_be_checked()

    date_from = "2024-01-01"
    date_to = datetime.today().strftime('%Y-%m-%d')

    search_page.fill_custom_dates(from_date=date_from, to_date=date_to)

    expect(search_page.get_period_radio("3years")).not_to_be_checked()

    expect(page).not_to_have_url(re.compile(r"date_filter="))
    expect(page).to_have_url(re.compile(f"from_date={date_from}"))
    expect(page).to_have_url(re.compile(f"to_date={date_to}"))


def test_filters_cross_compatibility_languages_and_dates(search_page: SearchPage, page):
    """
    сценарий 3: совместимость фильтров дат и языков
    проверка того, что применение одних фильтров не сбрасывает другие,
    а кнопка сброса очищает все фильтры сразу
    """
    search_page.open(query="machine learning")

    search_page.toggle_language("EN")
    search_page.select_period("year")

    expect(page).to_have_url(re.compile(r"lang=EN"))
    expect(page).to_have_url(re.compile(r"date_filter=year"))
    expect(search_page.get_language_btn("EN")
           ).to_have_class(re.compile(r"active"))
    expect(search_page.get_period_radio("year")).to_be_checked()

    date_from = "2023-01-01"
    search_page.fill_custom_dates(from_date=date_from)

    expect(search_page.get_period_radio("year")).not_to_be_checked()
    expect(page).not_to_have_url(re.compile(r"date_filter="))
    expect(page).to_have_url(re.compile(f"from_date={date_from}"))

    expect(page).to_have_url(re.compile(r"lang=EN"))
    expect(search_page.get_language_btn("EN")
           ).to_have_class(re.compile(r"active"))

    search_page.toggle_language("DE")

    expect(page).to_have_url(re.compile(r"lang=EN"))
    expect(page).to_have_url(re.compile(r"lang=DE"))
    expect(page).to_have_url(re.compile(f"from_date={date_from}"))

    search_page.click_reset()

    expect(page).not_to_have_url(re.compile(r"lang="))
    expect(page).not_to_have_url(re.compile(r"from_date="))
    expect(search_page.get_language_btn("EN")
           ).not_to_have_class(re.compile(r"active"))
    expect(search_page.get_language_btn("DE")
           ).not_to_have_class(re.compile(r"active"))
    expect(search_page.reset_btn).not_to_be_attached()
