# Проверка решения Manticore Search


## Что есть в проекте

- `docker-compose.yml` поднимает Manticore Search
- `Dockerfile` — образ для Manticore Search с настройками
- `scripts/index_data.py` создаёт и настраивает индекс `etu_pages`, выгружает данные из MySQL
- `scripts/manticore_benchmark.py` прогоняет бенчмарки по JSON-файлам с запросами
- `scripts/config.py` — основной файл настроек проекта (подключения, синонимы, стоп-слова и т.д.)
- `scripts/queries.py` — SQL-запросы и настройки ядра Manticore (морфология, спецсимволы)
- `wordforms.txt` — словарь строгих замен для Manticore

## Подготовка

Создать и активировать виртуальное окружение:

```bash
python -m venv venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск инфраструктуры

Поднять контейнеры Manticore Search:

```bash
docker-compose up -d
```

Проверить, что сервисы доступны (Manticore на `http://127.0.0.1:9308` и база данных). Настройки подключения к базе MySQL находятся в `scripts/config.py`.

## Индексация данных

Загрузка данных из MySQL в Manticore (флаг --recreate для переиндексации):

```bash
python scripts/index_data.py --recreate
```

Что делает индексация:

- Читает опубликованные документы из `modx_site_content`
- Очищает `content`, `pagetitle` и другие поля от HTML и системных тегов MODX
- Создаёт индекс `etu_pages` с морфологией
- Загружает документы в Manticore

## Бенчмарки

Запуск тестирования качества поиска:

```bash
python scripts/manticore_benchmark.py scripts/some_file.json
```

Скрипт:

- Прогоняет датасет запросов из JSON-файла
- Вычисляет метрики: Hit@1, Hit@5, Hit@10, MRR (можно настроить в `scripts/config.py`)
- Сохраняет логи неудачных запросов в `logs/`


## Метрики качества

Результаты бенчмарка:

| Язык | Hit@1 | Hit@5 | Hit@10 | MRR | Запросов |
| --- | ---: | ---: | ---: | ---: | ---: |
| Русский | 15.9% | 30.3% | 36.5% | 0.2196 | 1355 |
| Английский | 28.5% | 50.1% | 57.8% | 0.3760 | 1493 |


