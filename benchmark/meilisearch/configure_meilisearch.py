import meilisearch
import os
from dotenv import load_dotenv

load_dotenv()

MEILI_URL = os.getenv("MEILI_URL", "http://localhost:7700")
MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

EMBEDDER_LANGS = {"ru", "en", "de"}
EMBEDDER_NAME = "e5-small"
EMBEDDER_CONFIG = {
    "source": "huggingFace",
    "model": "intfloat/multilingual-e5-small",
    "documentTemplate": (
        "passage: {{doc.pagetitle}}. "
        "{% if doc.parent_title %}Раздел: {{doc.parent_title}}. {% endif %}"
        "{% if doc.breadcrumbs_str %}Путь: {{doc.breadcrumbs_str}}. {% endif %}"
        "{% if doc.tv_meta_keywords %}Ключевые слова: {{doc.tv_meta_keywords}}. {% endif %}"
        "{% if doc.longtitle %}{{doc.longtitle}}. {% endif %}"
        "{% if doc.tv_persons %}Персоны: {{doc.tv_persons}}. {% endif %}"
        "{% if doc.description %}{{doc.description}} {% endif %}"
        "{{doc.introtext}}"
    ),
    "documentTemplateMaxBytes": 2500,
}

RU_SYNONYMS = {
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

LANGUAGES = {
    "ru": {
        "locale_code": "rus",
        "synonyms": RU_SYNONYMS,
        "stop_words": [
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
        ],
    },
    "en": {
        "locale_code": "eng",
        "stop_words": [
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
            "to",
            "of",
        ],
    },
    "de": {
        "locale_code": "deu",
        "stop_words": [
            "der",
            "die",
            "das",
            "ein",
            "eine",
            "und",
            "oder",
            "aber",
            "in",
            "auf",
            "zu",
        ],
    },
    "sp": {
        "locale_code": "spa",
        "stop_words": [
            "el",
            "la",
            "los",
            "las",
            "un",
            "una",
            "y",
            "o",
            "pero",
            "en",
            "a",
            "de",
        ],
    },
    "pt": {
        "locale_code": "por",
        "stop_words": [
            "o",
            "a",
            "os",
            "as",
            "um",
            "uma",
            "e",
            "ou",
            "mas",
            "em",
            "para",
            "de",
        ],
    },
    "fr": {
        "locale_code": "fra",
        "stop_words": [
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
        ],
    },
    "vn": {"locale_code": "vie", "stop_words": []},
    "ar": {"locale_code": "ara", "stop_words": []},
    "cn": {"locale_code": "zho", "stop_words": []},
}

client = meilisearch.Client(MEILI_URL, MEILI_MASTER_KEY if MEILI_MASTER_KEY else None)


def setup_indexes():

    for lang, config in LANGUAGES.items():
        configure_single_index(
            f"site_{lang}",
            config["stop_words"],
            config.get("locale_code"),
            config.get("synonyms"),
            with_embedder=lang in EMBEDDER_LANGS,
        )

    configure_single_index("site_content", [], None, RU_SYNONYMS, with_embedder=True)


def configure_single_index(
    index_name, stop_words, locale_code=None, synonyms=None, with_embedder=False
):
    print(f"Настройка индекса: {index_name}...")
    index = client.index(index_name)

    settings = {
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
        "localizedAttributes": [{"attributePatterns": ["*"], "locales": [locale_code]}]
        if locale_code
        else [],
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
            "page_weight",
        ],
        "sortableAttributes": [
            "publishedon",
            "createdon",
            "editedon",
            "menuindex",
            "hitcount",
            "published_year",
            "page_weight",
        ],
        "rankingRules": [
            "words",
            "typo",
            "exactness",
            "attribute",
            "proximity",
            "sort",
            "hitcount:desc",
            "publishedon:desc",
            "page_weight:desc",
        ],
        "stopWords": stop_words,
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
            "page_weight",
            "description",
            "alias",
        ],
    }

    if with_embedder:
        settings["embedders"] = {EMBEDDER_NAME: EMBEDDER_CONFIG}

    task = index.update_settings(settings)
    print(f"Обновление {index_name} запущено. Task UID: {task.task_uid}")


if __name__ == "__main__":
    setup_indexes()
