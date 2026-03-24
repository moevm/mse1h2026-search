# Meilisearch

Проект поднимает локальный инстанс Meilisearch, настраивает индексы для языковых разделов сайта и импортирует документы из MySQL в отдельные языковые индексы и общий индекс `site_content`.

## Что есть в проекте

- `docker-compose.yml` поднимает Meilisearch `v1.39` на `http://localhost:7700`
- `configure_meilisearch.py` создаёт и настраивает индексы `site_<lang>` и `site_content` общий
- `sync_data.py` читает данные из `modx_site_content` (поднятой локально базы данных), очищает HTML и загружает документы в Meilisearch
- `meilisearch_benchmark.py file.json` прогоняет бенчмарки по `json` файлам.

## Подготовка

1. Создать и активировать виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Создать `.env` на основе примера:

```bash
cp .env.example .env
```

## Запуск Meilisearch

Поднять контейнер:

```bash
docker compose up --build -d
```

Проверить, что сервис доступен:

```bash
curl http://127.0.0.1:7700/health
```

## Настройка индексов

После запуска Meilisearch применить настройки индексов:

```bash
python3 configure_meilisearch.py
```

Скрипт создаёт и настраивает:

- `site_ru`
- `site_en`
- `site_de`
- `site_sp`
- `site_pt`
- `site_fr`
- `site_vn`
- `site_ar`
- `site_cn`
- `site_content`

## Импорт данных

Загрузка данных из MySQL в Meilisearch:

```bash
python3 sync_data.py
```

Что делает импорт:

- читает опубликованные и доступные для поиска документы из `modx_site_content`
- определяет язык документа по корню дерева
- очищает `content`, `introtext` и `description` от HTML
- добавляет `parent_title`, `breadcrumbs`, `published_year`, `page_weight`
- загружает документы в языковые индексы `site_<lang>`
- параллельно собирает все документы в общий индекс `site_content`

## Бенчмарки

Запуск

```bash
python3 meilisearch_benchmark.py json.file
```

## Таблица по `res/bread_pgw_typos6_10.txt`

Последние полученные метрики для полнотекстового поиска (без векторного).

| Язык | Hit@1 | Hit@5 | Hit@10 | MRR | Запросов |
| --- | ---: | ---: | ---: | ---: | ---: |
| Русский | 18.6% | 28.9% | 33.1% | 0.2312 | 1355 |
| Английский | 33.8% | 54.7% | 59.0% | 0.4234 | 1493 |

Если учитывать режимы, максимальные значения получены на языковых индексах:

- `ru`: `site_ru`
- `en`: `site_en`

Русский и английский были получены агрегацией файлов русского и английского соответственно.
