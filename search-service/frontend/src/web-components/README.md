# `<etu-search-input>`

Нативный веб-компонент поискового поля ETU.

Компонент содержит только само поле: input, подсказки, фильтр языка и
опциональный выбор типа поиска. Кнопка-лупа, показ/скрытие поля в шапке,
внешний layout и страница результатов остаются на стороне сайта, который
встраивает компонент.

## Сборка

```bash
cd frontend
npm run build:component
```

Готовый файл: `frontend/dist/etu-search-input.js`.

В Docker-сборке фронтенда компонент собирается вместе с Vue-приложением.
Демо-страница после `docker compose up --build`:

```text
http://localhost:6767/etu-search-input-demo.html
```

## Быстрое подключение

```html
<script src="/path/to/etu-search-input.js"></script>

<form action="/rezultaty-poiska" method="GET">
  <etu-search-input
    name="search"
    query-param="q"
    api-base="https://search.etu.ru"
    results-url="https://etu.ru/rezultaty-poiska"
    languages="RU,EN,DE,SP,VN,CN,AR,PT,FR"
  ></etu-search-input>
  <button type="submit" aria-label="Найти">Найти</button>
</form>
```

`<etu-search-input>` является form-associated custom element. Значение поля
попадает в `FormData` формы под именем из `name`.

Если компонент вставляется на другой домен, endpoint подсказок должен быть
доступен по CORS или через proxy на стороне сайта.

## Атрибуты

| Атрибут | По умолчанию | Что делает |
| --- | --- | --- |
| `name` | `search` | Имя поля в форме. |
| `value` | пусто | Начальное значение. Также доступно как `element.value`. |
| `placeholder` | `Поиск по сайту` | Placeholder input'а. |
| `api-base` | текущий origin | База для запросов подсказок. |
| `suggest-path` | `/api/suggest` | Endpoint подсказок для базового режима. |
| `results-url` | `form.action` или текущий path | Страница результатов. |
| `query-param` | значение `name` | Query-параметр поисковой строки. Для текущей Vue-страницы используйте `q`. |
| `languages` | пусто | Список языков через запятую. Если пусто, языковой фильтр скрыт. |
| `submit-mode` | `navigate` | `navigate` открывает URL, `event` только отдает его наружу. |
| `target` | `_blank` | Цель навигации. Для текущей вкладки используйте `_self`. |
| `modes` | `site` | JSON-массив типов поиска. |

## Отправка поиска

По умолчанию компонент собирает URL результатов и открывает его в новой вкладке.

```html
<etu-search-input
  results-url="https://etu.ru/rezultaty-poiska"
></etu-search-input>
```

Чтобы открыть результат в текущей вкладке:

```html
<etu-search-input
  target="_self"
  results-url="https://etu.ru/rezultaty-poiska"
></etu-search-input>
```

Для CMS или iframe-интеграции можно не выполнять переход внутри компонента, а
получить готовый URL событием:

```html
<etu-search-input
  submit-mode="event"
  results-url="https://search.etu.ru/?embed=true"
></etu-search-input>

<iframe id="search-results" title="Результаты поиска"></iframe>

<script>
  const input = document.querySelector('etu-search-input')
  const frame = document.querySelector('#search-results')

  input.addEventListener('search-submit', (event) => {
    frame.src = event.detail.url
  })
</script>
```

`event.detail`:

```js
{
  query: 'приемная комиссия',
  lang: 'RU',
  langs: ['RU', 'EN'],
  mode: 'site',
  url: 'https://etu.ru/rezultaty-poiska?q=...&lang=RU&lang=EN',
}
```

`lang` оставлен для простого случая с одним языком. Полный список выбранных
языков лежит в `langs`; в URL они добавляются повторяющимися параметрами
`lang`.

Разрешение на встраивание страницы результатов в `iframe` задается не здесь, а
заголовками самой страницы результатов, например через
`Content-Security-Policy: frame-ancestors ...`.

## Типы поиска

`modes` позволяет заранее показать переключатель "Сайт / Подразделения /
Персоналии". API для подразделений и персоналий сейчас нет в этом сервисе, но
его можно подключить позже через `suggestPath` и `resultsUrl`.

```html
<etu-search-input
  modes='[
    {
      "id": "site",
      "label": "Сайт",
      "suggestPath": "/api/suggest",
      "resultsUrl": "/rezultaty-poiska"
    },
    {
      "id": "departments",
      "label": "Подразделения",
      "suggestPath": "/api/departments/suggest",
      "resultsUrl": "/departments/search"
    },
    {
      "id": "persons",
      "label": "Персоналии",
      "suggestPath": "/api/persons/suggest",
      "resultsUrl": "/persons/search"
    }
  ]'
></etu-search-input>
```

Поля режима:

- `id` - технический идентификатор, попадает в `event.detail.mode`;
- `label` - текст в селекторе;
- `suggestPath` - endpoint подсказок для этого режима;
- `resultsUrl` - страница результатов для этого режима.

## Подсказки

Компонент запрашивает подсказки так:

```text
GET {api-base}{suggest-path}?q={query}
```

Текущий endpoint сервиса:

```text
GET /api/suggest?q=прием
```

Поддерживаемые ответы:

```json
{
  "suggestions": ["приемная комиссия", "правила приема"]
}
```

```json
["приемная комиссия", "правила приема"]
```

Если endpoint будущего режима вернет массив объектов, компонент возьмет текст
из первого найденного поля: `value`, `label`, `title`, `name`, `query`.

## Стилизация

Компонент использует Shadow DOM. Снаружи можно настраивать CSS custom properties
и `::part`.

```css
etu-search-input {
  --etu-search-bg: #fff;
  --etu-search-text: currentColor;
  --etu-search-muted: #667085;
  --etu-search-border: #d0d5dd;
  --etu-search-accent: #003087;
  --etu-search-accent-contrast: #fff;
  --etu-search-focus-ring: rgba(0, 48, 135, 0.14);
  --etu-search-hover-bg: #eef4ff;
  --etu-search-radius: 8px;
  --etu-search-shadow: 0 8px 20px rgba(15, 23, 42, 0.14);
  --etu-search-gap: 6px;
  --etu-search-min-height: 40px;
  --etu-search-dropdown-z-index: 1000;
}

etu-search-input::part(field) {
  min-width: 280px;
}

etu-search-input::part(mode-select) {
  width: 150px;
}
```

Доступные parts: `root`, `field`, `input`, `languages`, `language`,
`mode-select`, `suggestions`, `suggestion`.

## Клавиатура

- `ArrowDown` / `ArrowUp` переключают подсказки.
- `Enter` выбирает активную подсказку или отправляет поиск.
- `Escape` закрывает подсказки.
