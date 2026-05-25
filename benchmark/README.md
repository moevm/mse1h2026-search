# Benchmark Runner

## Запуск

```bash
cd benchmark
python3 -m venv .venv-runner
source .venv-runner/bin/activate
pip install -r requirements.txt
python runner.py data --engines-config config/engines.example.yaml --report-json reports/full_report.json
```

## Yandex Search API (`kind: yandex`)

1. Включите блок `yandex-default` в `config/engines.example.yaml`.
2. Укажите `params.folder_id`.
3. Укажите один из вариантов авторизации:
   - `params.iam_token` (предпочтительно);
   - `params.oauth_token` (движок сам обменяет на IAM token);
   - `params.api_key`.
4. Вместо полей в YAML можно использовать env:
   - `YANDEX_FOLDER_ID`
   - `YANDEX_IAM_TOKEN` или `YANDEX_OAUTH_TOKEN` или `YANDEX_API_KEY`
5. Для быстрого прогона используйте `config/engines.yandex.smoke.yaml`.

`YandexEngine` работает без индексации и использует Cloud Search API:
- `request_mode: sync` (быстрее): `POST https://searchapi.api.cloud.yandex.net/v2/web/search`
- `request_mode: async` (fallback): `POST .../searchAsync` + polling `GET .../operations/{operationId}`
