def is_valid_document(article: dict) -> bool:
    try:
        is_published = int(article.get("published", 1)) == 1
        is_deleted = int(article.get("deleted", 0)) == 1
        is_searchable = int(article.get("searchable", 1)) == 1

        return is_published and not is_deleted and is_searchable
    except (ValueError, TypeError):
        return False


def filter_valid_documents(articles: list[dict]) -> list[dict]:
    return [article for article in articles if is_valid_document(article)]