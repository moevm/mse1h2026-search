from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

SPACY_MODELS: dict[str, str] = {
    "ru": "ru_core_news_sm",
    "en": "en_core_web_sm",
    "de": "de_core_news_sm",
}

_nlp_cache: dict[str, object] = {}

_CYRILLIC = re.compile(r"[а-яёА-ЯЁ]")
_PRESERVE = re.compile(r"^(?:[A-ZА-ЯЁ\d]{2,}|\d[\d.,]*)$")


def _load_model(lang: str):
    if lang in _nlp_cache:
        return _nlp_cache[lang]

    model_name = SPACY_MODELS.get(lang)
    if not model_name:
        raise ValueError(f"Неизвестный язык: {lang!r}. Доступны: {list(SPACY_MODELS)}")

    try:
        import spacy

        nlp = spacy.load(model_name, disable=["parser", "ner"])
        nlp.max_length = 2_000_000
        _nlp_cache[lang] = nlp
        logger.info("Загружена spaCy-модель %s", model_name)
        return nlp
    except OSError as exc:
        raise RuntimeError(
            f"Модель spaCy '{model_name}' не найдена. "
            f"Установите её командой:\n"
            f"  python -m spacy download {model_name}"
        ) from exc


def detect_lang(text: str, alias: str = "") -> str:
    if not text:
        return "ru"

    if _CYRILLIC.search(text):
        return "ru"

    try:
        from langdetect import detect

        sample = text[:500].strip()
        if sample:
            lang = detect(sample)
            if lang in SPACY_MODELS:
                return lang
    except Exception:
        pass

    return "en"


def lemmatize(text: str, lang: str) -> str:
    if not text or not text.strip():
        return text

    try:
        nlp = _load_model(lang)
    except RuntimeError as exc:
        logger.warning("Лемматизация пропущена: %s", exc)
        return text

    try:
        doc = nlp(text)
        tokens: list[str] = []
        for token in doc:
            if token.is_space:
                continue
            raw = token.text
            # Сохраняем аббревиатуры и числа без изменений
            if _PRESERVE.match(raw):
                tokens.append(raw)
            else:
                lemma = token.lemma_.strip()
                tokens.append(lemma.lower() if lemma else raw.lower())
        return " ".join(tokens)
    except Exception as exc:
        logger.warning("Ошибка при лемматизации (%s): %s", lang, exc)
        return text


def lemmatize_document(
    pagetitle: str,
    longtitle: str,
    description: str,
    introtext: str,
    content: str,
    alias: str = "",
) -> dict[str, str]:
    sample = " ".join(
        filter(
            None,
            [
                pagetitle,
                longtitle,
                description,
                introtext[:300] if introtext else "",
            ],
        )
    )
    lang = detect_lang(sample, alias)

    return {
        "pagetitle_lemm": lemmatize(pagetitle, lang),
        "longtitle_lemm": lemmatize(longtitle, lang),
        "description_lemm": lemmatize(description, lang),
        "introtext_lemm": lemmatize(introtext, lang),
        "content_lemm": lemmatize(content, lang),
        "lang": lang,
    }


def lemmatize_query(query: str) -> str:
    lang = detect_lang(query)
    return lemmatize(query, lang)
