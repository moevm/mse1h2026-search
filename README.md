# mse-template

## Установка и запуск
Инструкции по установке и запуску проекта.

Разработка и тестирование проводились на `Docker version 29.4.0` и `Docker Compose version v5.1.2`. Сборка должна работать и на других версиях, но гарантируется совместимость с указанными.

Клонируем репозиторий:
```bash
git clone https://github.com/moevm/mse1h2026-search.git
```

Переходим в папку с поисковым сервисом:
```bash
cd mse1h2026-search/search-service/
```

Копируем конфиг из примера для backend:
```bash
cp backend/.env.example backend/.env
```

Копируем конфиг из примера для frontend:
```bash
cp frontend/.env.example frontend/.env
```

Копируем конфиг базы данных:
```bash
cp db/.env.example db/.env
```

Запускаем базу данных (при первом запуске автоматически скачивается дамп):
```bash
cd db && docker compose up -d && cd ..
```

Запускаем сервис через docker compose:
```bash
docker compose up --build -d
```

После запуска сервисы будут доступны по адресам (при конфиге из `.env.example`):

- Frontend: `http://localhost:6767`
- Backend API: `http://localhost:6767/api`
- Swagger UI: `http://localhost:6767/docs`

## Проверка работоспособности
Инструкции по проверке работоспособности проекта (основной функциональности и результатов).

Для проверки `search-service`:

- Откройте `http://localhost:6767`, должна появиться поисковая страница с mock данными.
- Проверьте `http://localhost:6767/api/health`, должен быть ответ `{"status":"ok"}`

## Дополнительная информация

Тестовый стенд https://search.etudevs.ru/
