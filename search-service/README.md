# Search Service

Прототип поискового сервиса для etu.ru. Два независимых сервиса: **backend** (FastAPI) и **frontend** (Vue 3 + Nginx).

## Структура

```
search-service/
├── backend/            — FastAPI, Uvicorn, Pydantic, uv
├── frontend/           — Vue 3 (CDN), Nginx
└── docker-compose.yml
```

---

## Запуск через Docker Compose

```bash
docker compose up --build
```

Конфигурация берётся из `backend/.env` и `frontend/.env`.

- Frontend: `http://localhost:6767`
- Backend API: `http://localhost:6767/api`
- Swagger UI: `http://localhost:6767/docs`

---

## Локальная разработка

### Backend

Требуется [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run uvicorn main:app --reload  # --reload для авторестарта при изменении файлов
```

#### Конфигурация (`backend/.env`)

| Переменная        | По умолчанию                | Описание                                                |
|-------------------|-----------------------------|---------------------------------------------------------|
| `HOST`            | `0.0.0.0`                   | Адрес сервера                                           |
| `PORT`            | `8000`                      | Порт                                                    |
| `SEARCH_PROVIDER` | `mock`                      | Провайдер: `mock`, `meilisearch`, `typesense`           |
| `CORS_ORIGINS`    | `["http://localhost:3000"]` | Разрешённые origins для CORS                            |

#### Линтинг и форматирование

```bash
uv run ruff check .
uv run ruff format .
```

### Frontend

```bash
cd frontend/static
python -m http.server 3000
```

#### Конфигурация (`frontend/.env`)

| Переменная     | По умолчанию | Описание                   |
|----------------|--------------|----------------------------|
| `BACKEND_HOST` | `backend`    | Хост бэкенда               |
| `BACKEND_PORT` | `8000`       | Порт бэкенда               |

---

## API

| Метод | Путь           | Описание                                            |
|-------|----------------|-----------------------------------------------------|
| GET   | `/api/search`  | Поиск: `?q=...&page=1&page_size=10`                 |
| GET   | `/api/suggest` | Подсказки: `?q=...`                                 |
| GET   | `/api/health`  | Health-check                                        |
| GET   | `/docs`        | Swagger UI                                          |

Дополнительные параметры `/api/search`: `lang`, `sort_by` (`relevance`/`date`), `date_filter` (`month`/`year`/`3years`), `from_date`/`to_date` (формат `DD-MM-YYYY`). В будущем могут меняться в соответствии с требованиями.

---

## Embed-режим

Добавьте `?embed=true` к URL — пока скрывается только шапка, данный пункт все еще на уточнении.

---

## Архитектура провайдеров

Поисковый движок подключается через абстракцию `BaseSearchProvider` (Ports & Adapters):

```env
SEARCH_PROVIDER=mock        # встроенный поиск по JSON-данным
SEARCH_PROVIDER=meilisearch # (не реализован)
SEARCH_PROVIDER=typesense   # (не реализован)
```
