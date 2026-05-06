from __future__ import annotations

import base64
import json
import os
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from core.engine_base import BaseSearchEngine
from core.types import SearchResult

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


class YandexEngine(BaseSearchEngine):
    def __init__(self, config):
        super().__init__(config)
        if requests is None:
            raise RuntimeError("requests package is not installed")
        self.session = requests.Session()

        params = self.config.params
        self.request_mode = str(params.get("request_mode", "sync")).strip().lower()
        self.base_url = str(params.get("base_url", "https://searchapi.api.cloud.yandex.net/v2/web/search")).strip()
        self.operations_base_url = str(
            params.get("operations_base_url", "https://operation.api.cloud.yandex.net/operations")
        ).rstrip("/")
        self.iam_token_url = str(params.get("iam_token_url", "https://iam.api.cloud.yandex.net/iam/v1/tokens")).strip()
        self.timeout_seconds = float(params.get("timeout_seconds", self.config.timeout_seconds))
        self.region = str(params.get("region", "225"))
        self.search_type = str(params.get("search_type", "SEARCH_TYPE_RU"))
        self.family_mode = str(params.get("family_mode", "FAMILY_MODE_MODERATE"))
        self.l10n = str(params.get("l10n", "LOCALIZATION_RU"))
        self.response_format = str(params.get("response_format", "FORMAT_XML"))
        self.group_mode = str(params.get("group_mode", "GROUP_MODE_FLAT"))
        self.docs_in_group = int(params.get("docs_in_group", 1))
        self.groups_on_page = int(params.get("groups_on_page", 10))
        self.max_poll_seconds = float(params.get("max_poll_seconds", 30.0))
        self.poll_interval_seconds = float(params.get("poll_interval_seconds", 1.0))
        self.sleep_seconds = float(params.get("sleep_seconds", 0.0))
        self.retry_backoff_seconds = float(params.get("retry_backoff_seconds", 1.0))
        self.rate_limit_backoff_seconds = float(params.get("rate_limit_backoff_seconds", 2.0))
        self.user_agent = str(params.get("user_agent", "")).strip()
        self.folder_id = self._pick_credential(
            params=params,
            param_names=("folder_id", "folderId"),
            env_names=("YANDEX_FOLDER_ID",),
        )

        self.iam_token = self._pick_credential(
            params=params,
            param_names=("iam_token", "iamToken"),
            env_names=("YANDEX_IAM_TOKEN",),
        )
        self.oauth_token = self._pick_credential(
            params=params,
            param_names=("oauth_token", "oauthToken"),
            env_names=("YANDEX_OAUTH_TOKEN",),
        )
        self.api_key = self._pick_credential(
            params=params,
            param_names=("api_key", "apiKey", "key"),
            env_names=("YANDEX_API_KEY",),
        )

        if not self.folder_id:
            raise RuntimeError(
                "Yandex Search API folder_id is missing. Set params.folder_id or env YANDEX_FOLDER_ID."
            )
        if not (self.iam_token or self.oauth_token or self.api_key):
            raise RuntimeError(
                "Yandex Search API credentials are missing. Set one of: "
                "params.iam_token, params.oauth_token, params.api_key (or env YANDEX_IAM_TOKEN / "
                "YANDEX_OAUTH_TOKEN / YANDEX_API_KEY)."
            )

        if not self.iam_token and self.oauth_token:
            self.iam_token = self._exchange_oauth_to_iam(self.oauth_token)

    def _pick_credential(
        self,
        params: dict[str, object],
        param_names: tuple[str, ...],
        env_names: tuple[str, ...],
    ) -> str:
        for name in param_names:
            value = str(params.get(name, "")).strip()
            if value:
                return value
        for env_name in env_names:
            value = os.getenv(env_name, "").strip()
            if value:
                return value
        return ""

    def _exchange_oauth_to_iam(self, oauth_token: str) -> str:
        response = self.session.post(
            self.iam_token_url,
            json={"yandexPassportOauthToken": oauth_token},
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Failed to exchange OAuth token to IAM token: HTTP {response.status_code}")
        payload = response.json()
        iam = str(payload.get("iamToken", "")).strip()
        if not iam:
            raise RuntimeError("IAM token exchange succeeded but iamToken is missing in response")
        return iam

    def _page_for_k(self, k: int) -> int:
        return max(1, min(self.groups_on_page, k))

    def _build_payload(self, query: str, k: int) -> dict[str, object]:
        page_docs = self._page_for_k(k)
        return {
            "query": {
                "searchType": self.search_type,
                "queryText": query,
                "familyMode": self.family_mode,
                "page": 0,
            },
            "groupSpec": {
                "groupMode": self.group_mode,
                "groupsOnPage": page_docs,
                "docsInGroup": self.docs_in_group,
            },
            "region": self.region,
            "l10N": self.l10n,
            "folderId": self.folder_id,
            "responseFormat": self.response_format,
        }

    def _extract_urls(self, xml_text: str, k: int) -> list[str]:
        root = ET.fromstring(xml_text)
        urls: list[str] = []
        seen: set[str] = set()
        for url_node in root.findall(".//doc/url"):
            url = (url_node.text or "").strip()
            if not url:
                continue
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                continue
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
            if len(urls) >= k:
                break
        return urls

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        if self.iam_token:
            headers["Authorization"] = f"Bearer {self.iam_token}"
            return headers
        if self.api_key:
            headers["Authorization"] = f"Api-Key {self.api_key}"
            return headers
        raise RuntimeError("No usable auth credential for Yandex Search API")

    def _request_search_operation(self, query: str, k: int) -> str:
        response = self.session.post(
            self.base_url,
            data=json.dumps(self._build_payload(query, k)),
            headers=self._build_headers(),
            timeout=self.timeout_seconds,
        )
        if response.status_code in {429, 500, 502, 503, 504}:
            raise RuntimeError(f"Yandex transient status {response.status_code}")
        if response.status_code >= 400:
            raise RuntimeError(f"Yandex API search request failed: HTTP {response.status_code}, body={response.text[:300]}")
        payload = response.json()
        operation_id = str(payload.get("id", "")).strip()
        if not operation_id:
            raise RuntimeError("Yandex API did not return operation id")
        return operation_id

    def _request_operation_status(self, operation_id: str) -> dict[str, object]:
        response = self.session.get(
            f"{self.operations_base_url}/{operation_id}",
            headers=self._build_headers(),
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Yandex operation status failed: HTTP {response.status_code}, body={response.text[:300]}"
            )
        return response.json()

    def _request_search(self, query: str, k: int) -> list[str]:
        if self.request_mode == "sync":
            response = self.session.post(
                self.base_url,
                data=json.dumps(self._build_payload(query, k)),
                headers=self._build_headers(),
                timeout=self.timeout_seconds,
            )
            if response.status_code in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"Yandex transient status {response.status_code}")
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Yandex API search request failed: HTTP {response.status_code}, body={response.text[:300]}"
                )
            payload = response.json()
            raw_data_base64 = str(payload.get("rawData", "")).strip()
            if not raw_data_base64:
                return []
            try:
                xml_text = base64.b64decode(raw_data_base64).decode("utf-8", errors="replace")
            except Exception as exc:
                raise RuntimeError(f"Failed to decode Yandex rawData: {exc}") from exc
            return self._extract_urls(xml_text, k)

        operation_id = self._request_search_operation(query, k)
        deadline = time.time() + self.max_poll_seconds
        while time.time() <= deadline:
            status = self._request_operation_status(operation_id)
            if bool(status.get("done", False)):
                response = status.get("response")
                if not isinstance(response, dict):
                    return []
                raw_data_base64 = str(response.get("rawData", "")).strip()
                if not raw_data_base64:
                    return []
                try:
                    xml_text = base64.b64decode(raw_data_base64).decode("utf-8", errors="replace")
                except Exception as exc:
                    raise RuntimeError(f"Failed to decode Yandex rawData: {exc}") from exc
                return self._extract_urls(xml_text, k)
            time.sleep(max(0.0, self.poll_interval_seconds))
        raise RuntimeError(f"Yandex search operation timeout after {self.max_poll_seconds} seconds")

    def healthcheck(self) -> None:
        urls = self._request_search("site:etu.ru test", 3)
        if not urls:
            raise RuntimeError("Yandex healthcheck returned no parseable links")

    def index(self, dump_or_db_path: str | None = None) -> None:
        return

    def search(self, query: str, k: int) -> list[SearchResult]:
        max_attempts = max(1, int(self.config.retries))
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                if self.sleep_seconds > 0:
                    time.sleep(self.sleep_seconds)
                urls = self._request_search(query, k)
                return [SearchResult(id=None, url=url, raw={"source": "yandex"}) for url in urls]
            except Exception as exc:
                last_error = exc
                if attempt + 1 >= max_attempts:
                    break
                error_text = str(exc).lower()
                if "transient status 429" in error_text:
                    backoff = self.rate_limit_backoff_seconds * (attempt + 1)
                else:
                    backoff = self.retry_backoff_seconds * (attempt + 1)
                if backoff > 0:
                    time.sleep(backoff)
        if last_error is not None:
            raise last_error
        return []
