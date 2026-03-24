# mse-template

## Установка и запуск
Инструкции по установке и запуску проекта.

```bash
cd search-service
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

После запуска сервисы будут доступны по адресам(при конфиге из `.env.example`):

- Frontend: `http://localhost`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

## Проверка работоспособности
Инструкции по проверке работоспособности проекта (основной функциональности и результатов).

Для проверки `search-service`:

- Откройте `http://localhost`, должна появиться поисковая страница с mock данными.
- Проверьте `http://localhost:8000/api/health`, должен быть ответ `{"status":"ok"}`

## Дополнительная информация
Любая информация, которую комакнда посчитает нужной разместить
