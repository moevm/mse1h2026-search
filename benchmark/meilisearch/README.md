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

1. Создать `.env` на основе примера:

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

## Результаты векторного поиска

Сравнение embedding-моделей для гибридного поиска (текст + вектор).

### Сравнение моделей (RU-запросы, индекс site_ru, 1355 запросов)

| Модель | Hit@1 | Hit@5 | Hit@10 | MRR |
|--------|------:|------:|-------:|----:|
| [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) | 26.4% | 38.7% | 43.5% | 0.3156 |
| [snowflake-arctic-embed-l-v2.0](https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0) | 26.0% | 39.3% | 46.2% | 0.3173 |

> Arctic незначительно лучше по Hit@5, Hit@10 и MRR; по Hit@1 модели эквивалентны.

### multilingual-e5-small — Полные результаты

**RU-запросы (1355 запросов)**

| Индекс | Hit@1 | Hit@5 | Hit@10 | MRR |
|--------|------:|------:|-------:|----:|
| site_content | 24.9% | 37.5% | 42.5% | 0.3023 |
| site_ru | 26.4% | 38.7% | 43.5% | 0.3156 |
| multi-index (federated) | 24.1% | 35.6% | 40.2% | 0.2895 |

**EN-запросы (1493 запроса)**

| Индекс | Hit@1 | Hit@5 | Hit@10 | MRR |
|--------|------:|------:|-------:|----:|
| site_content | 41.3% | 61.3% | 67.8% | 0.4959 |
| site_en | 43.1% | 64.7% | 70.5% | 0.5213 |
| multi-index (federated) | 33.5% | 55.1% | 63.3% | 0.4261 |

**Combined (5425 запросов)**

| Индекс | Hit@1 | Hit@5 | Hit@10 | MRR |
|--------|------:|------:|-------:|----:|
| site_content | 38.5% | 59.0% | 66.5% | 0.4719 |
| multi-index (federated) | 31.9% | 48.2% | 53.8% | 0.3883 |

Помимо этих моделей были произведены тесты bge3 (очень долгая индексация), как и с snowflake-arctic-embed-l-v2.
Среди всех моделей лучшая по соотношению качества/скорости оказалась multilingual-e5-small.

Основную проблематику составляет разные способы хранения моделей будто ONNX или другие, т.к. meilisearch использует инференс с помощью Candle не все модели можно было удобно протестировать,  в связи с чем были попытки использовать infinity или fastembedder для других моделей, однако очень сложно интегрировать с meilisearch чтобы это работало без ошибок. Также этот процесс занимает довольно продолжительное время.

Основной вектор следующего развития это использовать fastembedder и модель [harrier 270m](https://huggingface.co/microsoft/harrier-oss-v1-270m), которая показывает очень хорошие результаты в бенчмарке [HF MTEB](https://huggingface.co/spaces/mteb/leaderboard). потенциально эта модель может дать неплохой прирост.
