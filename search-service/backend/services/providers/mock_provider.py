import json
from datetime import datetime, timedelta
from pathlib import Path

from models.schemas import ArticleResult, SearchResponse
from services.exceptions import InvalidParameterError
from services.providers.base import BaseSearchProvider

DATA_FILE = Path(__file__).parent.parent.parent / "data" / "articles.json"


class MockProvider(BaseSearchProvider):
    def __init__(self) -> None:
        self.articles: list[dict] = []
        if DATA_FILE.exists():
            with open(DATA_FILE, encoding="utf-8") as f:
                self.articles = json.load(f)

    def _score_article(self, article: dict, query: str) -> int:
        query_lower = query.lower()
        score = 0

        title = article.get("title", "").lower()
        if query_lower in title:
            score += 3

        for keyword in article.get("keywords", []):
            if query_lower in keyword.lower():
                score += 2
                break

        abstract = article.get("abstract", "").lower()
        if query_lower in abstract:
            score += 1

        return score

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        lang: list[str] | None = None,
        sort_by: str = "relevance",
        date_filter: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> SearchResponse:
        filtered_articles = []
        for article in self.articles:
            if lang and article.get("lang") not in lang:
                continue

            try:
                article_date = datetime.strptime(
                    article.get("date", "01-01-2000"), "%d-%m-%Y"
                ).date()
            except ValueError:
                article_date = datetime.min.date()

            # Fixed period filters
            if date_filter:
                today = datetime.now().date()
                if date_filter == "month":
                    start_date = today - timedelta(days=30)
                elif date_filter == "year":
                    start_date = today - timedelta(days=365)
                elif date_filter == "3years":
                    start_date = today - timedelta(days=365 * 3)
                else:
                    start_date = datetime.min.date()

                if article_date < start_date:
                    continue

            # Custom date range
            if from_date:
                try:
                    f_date = datetime.strptime(from_date, "%d-%m-%Y").date()
                    if article_date < f_date:
                        continue
                except ValueError as e:
                    msg = f"Invalid from_date format: {from_date or 'null'}. Expected DD-MM-YYYY."
                    raise InvalidParameterError(msg) from e

            if to_date:
                try:
                    t_date = datetime.strptime(to_date, "%d-%m-%Y").date()
                    if article_date > t_date:
                        continue
                except ValueError as e:
                    msg = f"Invalid to_date format: {to_date or 'null'}. Expected DD-MM-YYYY."
                    raise InvalidParameterError(msg) from e

            score = 1
            if query:
                score = self._score_article(article, query)
                if score <= 0:
                    continue

            filtered_articles.append((article, score))

        if sort_by == "date":
            def get_date(item):
                try:
                    return datetime.strptime(
                        item[0].get("date", "01-01-2000"), "%d-%m-%Y"
                    )
                except ValueError:
                    return datetime.min

            filtered_articles.sort(key=get_date, reverse=True)
        else:
            filtered_articles.sort(key=lambda x: x[1], reverse=True)

        total = len(filtered_articles)

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered_articles[start_idx:end_idx]

        article_results = [
            ArticleResult(
                id=str(item[0].get("id", "")),
                title=item[0].get("title", ""),
                authors=item[0].get("authors", []),
                abstract=item[0].get("abstract", ""),
                keywords=item[0].get("keywords", []),
                date=item[0].get("date", "01-01-2000"),
                lang=item[0].get("lang", "RU"),
                url=item[0].get("url", ""),
            )
            for item in paginated
        ]

        return SearchResponse(
            total=total,
            page=page,
            page_size=page_size,
            query=query,
            results=article_results,
        )

    async def suggest(self, query: str) -> list[str]:
        if not query:
            return []

        suggestions = {}
        query_lower = query.lower()

        for article in self.articles:
            if len(suggestions) >= 5:
                break

            title = article.get("title", "")
            if query_lower in title.lower():
                suggestions[title] = None

            for keyword in article.get("keywords", []):
                if query_lower in keyword.lower():
                    suggestions[keyword] = None
                if len(suggestions) >= 5:
                    break

        return list(suggestions.keys())[:5]
