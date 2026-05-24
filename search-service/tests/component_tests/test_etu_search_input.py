import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, expect


ROOT = Path(__file__).resolve().parents[2]
COMPONENT_SOURCE = ROOT / "frontend/src/web-components/etu-search-input.js"


def open_component_page(page: Page, attrs: str, form_action: str = "/rezultaty-poiska"):
    source = COMPONENT_SOURCE.read_text(encoding="utf-8")
    html = f"""
    <!doctype html>
    <html lang="ru">
      <head><meta charset="utf-8"><title>Component fixture</title></head>
      <body>
        <form id="search-form" action="{form_action}" method="GET">
          <etu-search-input {attrs}></etu-search-input>
          <button id="submit" type="submit">submit</button>
          <button id="reset" type="reset">reset</button>
        </form>
        <script type="module">{source}</script>
      </body>
    </html>
    """

    page.route(
        "https://component.test/demo",
        lambda route: route.fulfill(status=200, content_type="text/html", body=html),
    )
    page.context.route(
        "https://component.test/rezultaty-poiska**",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="<h1>Results</h1>",
        ),
    )
    page.goto("https://component.test/demo")
    page.wait_for_function("() => customElements.get('etu-search-input')")


def input_locator(page: Page):
    return page.locator("etu-search-input input[part='input']")


def component_locator(page: Page):
    return page.locator("etu-search-input")


def test_component_registers_and_participates_in_form_data(page: Page):
    open_component_page(page, 'name="search" submit-mode="event"')

    input_locator(page).fill("приемная комиссия")

    form_value = page.evaluate(
        """
        () => new FormData(document.querySelector('#search-form')).get('search')
        """
    )

    assert form_value == "приемная комиссия"


def test_event_mode_emits_submit_detail_without_navigation(page: Page):
    open_component_page(
        page,
        'name="search" query-param="q" submit-mode="event" '
        'results-url="https://etu.ru/rezultaty-poiska" languages="ru,en"',
    )

    page.evaluate(
        """
        () => {
          window.searchSubmitEvents = []
          document.querySelector('etu-search-input').addEventListener('search-submit', (event) => {
            window.searchSubmitEvents.push(event.detail)
          })
        }
        """
    )

    input_locator(page).fill("приемная комиссия")
    component_locator(page).get_by_role("button", name="Язык ru").click()
    component_locator(page).get_by_role("button", name="Язык en").click()
    page.locator("#submit").click()

    detail = page.evaluate("window.searchSubmitEvents[0]")
    parsed_url = urlparse(detail["url"])
    params = parse_qs(parsed_url.query)

    assert detail["query"] == "приемная комиссия"
    assert detail["lang"] == "ru"
    assert detail["langs"] == ["ru", "en"]
    assert detail["mode"] == "site"
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "etu.ru"
    assert parsed_url.path == "/rezultaty-poiska"
    assert params["q"] == ["приемная комиссия"]
    assert params["lang"] == ["ru", "en"]
    expect(page).to_have_url("https://component.test/demo")


def test_mode_specific_results_url_and_default_query_param(page: Page):
    modes = json.dumps(
        [
            {
                "id": "site",
                "label": "Сайт",
                "suggestPath": "/api/suggest",
                "resultsUrl": "/rezultaty-poiska",
            },
            {
                "id": "departments",
                "label": "Подразделения",
                "suggestPath": "/api/departments/suggest",
                "resultsUrl": "/departments/search",
            },
        ],
        ensure_ascii=False,
    )
    open_component_page(
        page,
        f"name=\"search\" submit-mode=\"event\" results-url=\"https://etu.ru/rezultaty-poiska\" "
        f"languages=\"ru,en\" modes='{modes}'",
    )

    page.evaluate(
        """
        () => {
          window.searchSubmitEvents = []
          document.querySelector('etu-search-input').addEventListener('search-submit', (event) => {
            window.searchSubmitEvents.push(event.detail)
          })
        }
        """
    )

    component_locator(page).locator("select[part='mode-select']").select_option("departments")
    component_locator(page).get_by_role("button", name="Язык ru").click()
    input_locator(page).fill("кафедра")
    page.locator("#submit").click()

    detail = page.evaluate("window.searchSubmitEvents[0]")
    parsed_url = urlparse(detail["url"])
    params = parse_qs(parsed_url.query)

    assert detail["mode"] == "departments"
    assert parsed_url.netloc == "etu.ru"
    assert parsed_url.path == "/departments/search"
    assert params["search"] == ["кафедра"]
    assert params["lang"] == ["ru"]


def test_suggestions_use_active_mode_endpoint_and_can_be_selected(page: Page):
    modes = json.dumps(
        [
            {
                "id": "site",
                "label": "Сайт",
                "suggestPath": "/api/suggest",
                "resultsUrl": "/rezultaty-poiska",
            },
            {
                "id": "persons",
                "label": "Персоналии",
                "suggestPath": "/api/persons/suggest",
                "resultsUrl": "/persons/search",
            },
        ],
        ensure_ascii=False,
    )
    requested_urls = []

    page.route(
        "https://component.test/api/persons/suggest**",
        lambda route: (
            requested_urls.append(route.request.url),
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"suggestions": ["Петров Петр"]}, ensure_ascii=False),
            ),
        ),
    )
    open_component_page(page, f"submit-mode=\"event\" modes='{modes}'")

    component_locator(page).locator("select[part='mode-select']").select_option("persons")
    input_locator(page).fill("пет")
    expect(component_locator(page).get_by_role("option", name="Петров Петр")).to_be_visible()

    component_locator(page).get_by_role("option", name="Петров Петр").click()

    assert requested_urls
    assert "/api/persons/suggest" in requested_urls[0]
    expect(input_locator(page)).to_have_value("Петров Петр")


def test_default_navigate_opens_url_in_new_page(page: Page):
    open_component_page(
        page,
        'name="search" results-url="/rezultaty-poiska" languages="ru"',
    )

    input_locator(page).fill("дни открытых дверей")
    component_locator(page).get_by_role("button", name="Язык ru").click()

    with page.expect_popup() as popup_info:
        page.locator("#submit").click()

    popup = popup_info.value
    expect(popup).to_have_url(
        "https://component.test/rezultaty-poiska?search=%D0%B4%D0%BD%D0%B8+"
        "%D0%BE%D1%82%D0%BA%D1%80%D1%8B%D1%82%D1%8B%D1%85+"
        "%D0%B4%D0%B2%D0%B5%D1%80%D0%B5%D0%B9&lang=ru"
    )
