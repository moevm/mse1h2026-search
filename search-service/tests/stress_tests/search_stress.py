import time
import os
import random
import logging
import itertools
import requests
from locust import FastHttpUser, task, between, events


MIN_WAIT = float(os.getenv("LOCUST_MIN_WAIT", "1"))
MAX_WAIT = float(os.getenv("LOCUST_MAX_WAIT", "1"))
API_ENDPOINT = os.getenv("LOCUST_API_ENDPOINT", "/api/search")
TERMS_FILE = os.getenv("LOCUST_TERMS_FILE", "search_terms.txt")

RUN_SYNC = os.getenv("LOCUST_RUN_SYNC", "false").lower() == "true"
INDEXER_TOKEN = os.getenv("INDEXER_TOKEN", "")
SYNC_ENDPOINT = "/api/indexer/sync/full"

WORDS_CACHE: list[str] = []
RUN_ID = int(time.time())
query_counter = itertools.count(1)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global WORDS_CACHE

    try:
        with open(TERMS_FILE, "r", encoding="utf-8") as f:
            WORDS_CACHE = [line.strip() for line in f if line.strip()]
        logging.info(
            f"Успешно загружено {len(WORDS_CACHE)} слов из {TERMS_FILE}")
    except FileNotFoundError:
        logging.warning(
            f"Файл {TERMS_FILE} не найден. Используется резервное слово 'test'")
        WORDS_CACHE = ["test"]

    if RUN_SYNC:
        if not INDEXER_TOKEN:
            logging.error(
                "Флаг RUN_SYNC активирован, но INDEXER_TOKEN не передан. Индексация не запущена.")
            return

        host = environment.host.rstrip(
            "/") if environment.host else "http://localhost:8000"
        url = f"{host}{SYNC_ENDPOINT}"
        headers = {"Authorization": f"Bearer {INDEXER_TOKEN}"}

        logging.info(f"Инициирование фоновой переиндексации через {url}...")
        try:
            response = requests.post(url, headers=headers, timeout=10)
            if response.status_code == 200:
                logging.info(
                    "Переиндексация успешно запущена. Переход к стресс-тесту.")
            elif response.status_code == 409:
                logging.warning(
                    "Переиндексация уже выполняется на сервере. Тест продолжится в смешанном режиме.")
            elif response.status_code == 401:
                logging.error(
                    "Ошибка авторизации (401). Неверный INDEXER_TOKEN.")
            else:
                logging.error(
                    f"Ошибка запуска индексации: HTTP {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(
                f"Сетевая ошибка при попытке запустить индексацию: {e}")


def generate_uncached_query(base_terms: list[str]) -> str:
    term = random.choice(base_terms) if base_terms else "test"
    unique_id = next(query_counter)
    return f"{term} {RUN_ID}-{unique_id}"


class SearchStressUser(FastHttpUser):
    wait_time = between(MIN_WAIT, MAX_WAIT)

    @task
    def stress_search_api(self):
        query = generate_uncached_query(WORDS_CACHE)
        request_params = {"q": query}

        browser_headers = {
            "Host": "etu.ru",
            "Accept": "application/json",
            "Referer": "https://etu.ru/search"
        }

        with self.client.get(
            API_ENDPOINT,
            params=request_params,
            headers=browser_headers,
            name=f"{API_ENDPOINT}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate Limit")
            elif response.status_code == 404:
                response.failure(
                    f"Not Found: Неверный URL API ({API_ENDPOINT})")
            elif response.status_code >= 500:
                response.failure(
                    f"Server Error: Бэкенд упал ({response.status_code})")
            else:
                response.failure(f"Неожиданный статус: {response.status_code}")
