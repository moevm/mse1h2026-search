from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def canonicalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""

    parsed = urlsplit(raw)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"
    return urlunsplit((scheme, netloc, path, "", ""))


def to_doc_key(document_id: object, url: str | None) -> str:
    if document_id is not None and str(document_id).strip():
        return f"id:{str(document_id).strip()}"

    canonical_url = canonicalize_url(url or "")
    if canonical_url:
        return f"url:{canonical_url}"
    return ""
