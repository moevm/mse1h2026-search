import asyncio
from datetime import date, datetime, time, timedelta

import meilisearch
from meilisearch.errors import MeilisearchError

from config import get_settings
from models.schemas import ArticleResult, SearchResponse
from services.exceptions import InvalidParameterError, SearchProviderError
from services.providers.base import BaseSearchProvider


def _to_ts(d: date) -> int:
    return int(datetime.combine(d, time.min).timestamp())


def _ts_to_date_str(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d-%m-%Y")


def _build_date_filter(
    date_filter: str | None,
    from_date: str | None,
    to_date: str | None,
) -> str | None:
    parts: list[str] = []
    today = datetime.now().date()

    if date_filter:
        delta = {"month": 30, "year": 365, "3years": 1095}[date_filter]
        parts.append(f"publishedon >= {_to_ts(today - timedelta(days=delta))}")

    if from_date:
        try:
            d = datetime.strptime(from_date, "%d-%m-%Y").date()
        except ValueError as e:
            raise InvalidParameterError(
                f"Invalid from_date format: {from_date!r}. Expected DD-MM-YYYY."
            ) from e
        parts.append(f"publishedon >= {_to_ts(d)}")

    if to_date:
        try:
            d = datetime.strptime(to_date, "%d-%m-%Y").date()
        except ValueError as e:
            raise InvalidParameterError(
                f"Invalid to_date format: {to_date!r}. Expected DD-MM-YYYY."
            ) from e
        parts.append(f"publishedon <= {_to_ts(d) + 86399}")

    return " AND ".join(parts) if parts else None


def _build_lang_filter(lang: list[str] | None) -> str | None:
    if not lang:
        return None
    return " OR ".join(f'lang = "{ln}"' for ln in lang)


def _combine_filters(*parts: str | None) -> str | None:
    active = [p for p in parts if p]
    if not active:
        return None
    return " AND ".join(f"({p})" for p in active)


_EMBEDDER_NAME = "e5-small"

_RU_SYNONYMS = {
    "лэти": ["спбгэту", "электротехнический университет"],
    "спбгэту": ["лэти", "электротехнический университет"],
    "вуз": ["университет"],
    "университет": ["вуз"],
    "о нас": ["об университете", "общие сведения"],
    "об университете": ["о нас", "общие сведения"],
    "поступление": ["приём", "прием", "поступить"],
    "приём": ["поступление", "прием", "поступить"],
    "абитуриент": ["поступающий", "поступление"],
    "контакты": ["телефоны", "адрес"],
    "эндаумент": ["фонд развития", "эндаумент-фонд"],
}

_STOP_WORDS = (
    [
        "и",
        "в",
        "во",
        "не",
        "что",
        "он",
        "на",
        "я",
        "с",
        "со",
        "как",
        "а",
        "то",
        "все",
        "она",
        "так",
        "его",
        "но",
        "да",
        "ты",
        "к",
        "у",
        "же",
        "вы",
        "за",
        "бы",
        "по",
        "только",
        "ее",
        "мне",
        "было",
        "вот",
        "от",
        "меня",
        "еще",
        "нет",
        "из",
        "ему",
        "теперь",
        "даже",
        "ну",
        "вдруг",
        "ли",
        "если",
        "уже",
        "или",
        "ни",
        "был",
        "него",
        "до",
        "вас",
        "нибудь",
        "опять",
        "уж",
        "вам",
        "ведь",
        "там",
        "потом",
        "себя",
        "ничего",
        "ей",
        "они",
        "тут",
        "ней",
        "для",
        "мы",
        "тебя",
        "их",
        "чем",
        "была",
        "сам",
        "чтоб",
        "без",
        "будто",
        "чего",
        "раз",
        "тоже",
        "себе",
        "под",
        "ж",
        "тогда",
        "этот",
        "того",
        "потому",
        "этого",
        "какой",
        "совсем",
        "ним",
        "здесь",
        "этом",
        "один",
        "почти",
        "мой",
        "тем",
        "чтобы",
        "нее",
        "сейчас",
        "были",
        "всех",
        "никогда",
        "можно",
        "при",
        "наконец",
        "два",
        "другой",
        "хоть",
        "после",
        "над",
        "больше",
        "тот",
        "через",
        "эти",
        "про",
        "всего",
        "них",
        "какая",
        "много",
        "разве",
        "три",
        "эту",
        "моя",
        "впрочем",
        "хорошо",
        "свою",
        "этой",
        "перед",
        "иногда",
        "лучше",
        "чуть",
        "том",
        "нельзя",
        "такой",
        "им",
        "более",
        "всегда",
        "конечно",
        "всю",
        "между",
    ]
    + [
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "about",
        "is",
        "it",
    ]
    + ["der", "die", "das", "ein", "eine", "und", "oder", "aber", "auf", "zu"]
    + [
        "le",
        "la",
        "les",
        "un",
        "une",
        "et",
        "ou",
        "mais",
        "dans",
        "sur",
        "à",
        "pour",
        "de",
    ]
)

_INDEX_SETTINGS = {
    "searchableAttributes": [
        "pagetitle",
        "tv_meta_title",
        "parent_title",
        "longtitle",
        "menutitle",
        "tv_meta_keywords",
        "introtext",
        "tv_meta_description",
        "description",
        "breadcrumbs",
        "tv_persons",
        "tv_author",
        "tv_position",
        "content",
    ],
    "filterableAttributes": [
        "id",
        "published",
        "deleted",
        "parent",
        "template",
        "isfolder",
        "searchable",
        "hidemenu",
        "published_year",
        "publishedon",
        "lang",
    ],
    "sortableAttributes": [
        "menuindex",
        "hitcount",
        "published_year",
    ],
    "rankingRules": [
        "words",
        "typo",
        "exactness",
        "attribute",
        "proximity",
        "hitcount:desc",
    ],
    "stopWords": _STOP_WORDS,
    "synonyms": _RU_SYNONYMS,
    "typoTolerance": {
        "enabled": True,
        "disableOnAttributes": ["alias", "id"],
        "minWordSizeForTypos": {"oneTypo": 5, "twoTypos": 9},
    },
    "displayedAttributes": [
        "id",
        "pagetitle",
        "parent_title",
        "breadcrumbs",
        "published_year",
        "description",
        "introtext",
        "alias",
        "url_path",
        "publishedon",
        "lang",
    ],
}

def apply_index_settings(
    meili_url: str,
    meili_api_key: str,
    meili_index: str,
    timeout_ms: int = 600_000,
    interval_ms: int = 1000,
) -> None:
    settings = get_settings()
    document_template = (
        f"{settings.MEILI_EMBEDDER_PREFIX}{{doc.pagetitle}}. "
        "{% if doc.parent_title %}Раздел: {{doc.parent_title}}. {% endif %}"
        "{% if doc.breadcrumbs_str %}Путь: {{doc.breadcrumbs_str}}. {% endif %}"
        "{% if doc.tv_meta_keywords %}"
        "Ключевые слова: {{doc.tv_meta_keywords}}. "
        "{% endif %}"
        "{% if doc.longtitle %}{{doc.longtitle}}. {% endif %}"
        "{% if doc.tv_persons %}Персоны: {{doc.tv_persons}}. {% endif %}"
        "{% if doc.description %}{{doc.description}} {% endif %}"
        "{{doc.introtext}}"
    )

    if settings.MEILI_EMBEDDER_TYPE == "huggingface":
        embedder_config = {
            "source": "huggingFace",
            "model": settings.MEILI_EMBEDDER_MODEL,
            "documentTemplate": document_template,
            "documentTemplateMaxBytes": settings.MEILI_EMBEDDER_MAX_BYTES,
        }
    elif settings.MEILI_EMBEDDER_TYPE == "rest":
        embedder_config = {
            "source": "rest",
            "url": settings.MEILI_EMBEDDER_URL,
            "dimensions": settings.MEILI_EMBEDDER_DIMENSIONS,
            "request": {
                "inputs": ["{{text}}", "{{..}}"]
            },
            "response": {
                "embeddings": ["{{embedding}}", "{{..}}"]
            },
            "documentTemplate": document_template,
            "documentTemplateMaxBytes": settings.MEILI_EMBEDDER_MAX_BYTES,
        }
    else:
        raise ValueError(f"Unknown MEILI_EMBEDDER_TYPE: {settings.MEILI_EMBEDDER_TYPE}")

    index_settings = _INDEX_SETTINGS.copy()
    index_settings["embedders"] = {_EMBEDDER_NAME: embedder_config}

    client = meilisearch.Client(meili_url, meili_api_key or None)
    index = client.index(meili_index)
    task = index.update_settings(index_settings)
    client.wait_for_task(task.task_uid, timeout_in_ms=timeout_ms, interval_in_ms=interval_ms)


class MeilisearchProvider(BaseSearchProvider):
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = meilisearch.Client(
            self._settings.MEILI_URL,
            self._settings.MEILI_API_KEY or None,
        )
        self._index = self._client.index(self._settings.MEILI_INDEX)

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        lang: list[str] | None = None,
        date_filter: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> SearchResponse:
        date_f = _build_date_filter(date_filter, from_date, to_date)
        lang_f = _build_lang_filter(lang)
        combined = _combine_filters(date_f, lang_f)

        opt_params: dict = {
            "offset": (page - 1) * page_size,
            "limit": page_size,
            "matchingStrategy": "frequency",
            "hybrid": {
                "embedder": _EMBEDDER_NAME,
                "semanticRatio": self._settings.MEILI_SEMANTIC_RATIO,
            },
        }
        if combined:
            opt_params["filter"] = combined

        normalized_query = (query or "").strip().lower()

        try:
            result = await asyncio.to_thread(
                self._index.search, normalized_query, opt_params
            )
        except MeilisearchError as e:
            raise SearchProviderError(str(e)) from e

        hits = result["hits"]
        total = result.get("estimatedTotalHits", len(hits))

        return SearchResponse(
            total=total,
            page=page,
            page_size=page_size,
            query=query,
            results=[
                ArticleResult(
                    id=str(h["id"]),
                    title=h.get("pagetitle", ""),
                    authors=[],
                    abstract=h.get("introtext") or h.get("description", ""),
                    keywords=[],
                    date=_ts_to_date_str(h["publishedon"]) if h.get("publishedon") else None,
                    lang=h.get("lang") or "RU",
                    url=f"{self._settings.SITE_URL}/{h.get('url_path') or h.get('alias', h['id'])}",
                )
                for h in hits
            ],
        )

    async def suggest(self, query: str) -> list[str]:
        if not query:
            return []

        normalized_query = query.strip().lower()

        try:
            result = await asyncio.to_thread(
                self._index.search,
                normalized_query,
                {"limit": 5, "attributesToRetrieve": ["pagetitle"]},
            )
        except MeilisearchError as e:
            raise SearchProviderError(str(e)) from e

        suggestions: dict[str, None] = {}
        for hit in result["hits"]:
            if len(suggestions) >= 5:
                break
            if title := hit.get("pagetitle"):
                suggestions[title] = None

        return list(suggestions)[:5]
