from __future__ import annotations

import ipaddress
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from .schemas import APIError, ErrorCode, Freshness, Notice, NoticeResult, NoticeStatus, SourceType

DEFAULT_THRESHOLD = 86_400
TIMEOUT_SECONDS = 20.0


def _error(code: ErrorCode, message: str, retryable: bool, request_id: str | None = None) -> APIError:
    return APIError(code=code, message=message, retryable=retryable, request_id=request_id, details=None)


def _safe_public_https_url(raw_url: str) -> bool:
    try:
        candidate = raw_url if raw_url.startswith(("https://", "http://")) else f"https://{raw_url}"
        parsed = urlparse(candidate)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.lower().rstrip(".")
        if host in {"localhost", "localhost.localdomain"} or "." not in host:
            return False
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return False
        except ValueError:
            pass
        return True
    except (ValueError, TypeError):
        return False


def _parse_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _source_type(domain: str) -> SourceType:
    if domain.endswith(".gov") or domain.endswith(".gov.in") or domain.endswith(".nic.in"):
        return SourceType.official
    return SourceType.public


async def search_fetch(query: str, location: str = "India") -> NoticeResult:
    now = datetime.now(timezone.utc)
    threshold = int(os.getenv("NOTICE_FRESHNESS_THRESHOLD_SECONDS", str(DEFAULT_THRESHOLD)))
    api_key = os.getenv("TINYFISH_API_KEY", "").strip()
    if not api_key:
        return NoticeResult(
            status=NoticeStatus.provider_error,
            query=query,
            results=[],
            retrieved_at=now,
            freshness_threshold_seconds=threshold,
            error=_error(ErrorCode.dependency_unavailable, "TinyFish is not configured. Set TINYFISH_API_KEY on the backend.", False),
        )

    search_url = os.getenv("TINYFISH_SEARCH_URL", "https://api.search.tinyfish.ai").rstrip("/")
    fetch_url = os.getenv("TINYFISH_FETCH_URL", "https://api.fetch.tinyfish.ai").rstrip("/")
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False) as client:
            search_response = await client.get(
                search_url,
                params={"query": f"{query} official public notice {location}", "location": "IN", "language": "en"},
                headers=headers,
            )
            if search_response.status_code == 429:
                raise _ProviderFailure(ErrorCode.provider_rate_limited, "TinyFish rate limit reached.", True)
            if search_response.status_code >= 500:
                raise _ProviderFailure(ErrorCode.provider_unavailable, "TinyFish Search is temporarily unavailable.", True)
            if search_response.status_code >= 400:
                raise _ProviderFailure(ErrorCode.provider_unavailable, "TinyFish Search rejected the request. Check the backend API key/configuration.", False)
            search_payload = search_response.json()
            raw_results = search_payload.get("results", []) if isinstance(search_payload, dict) else []
            if not isinstance(raw_results, list):
                raise _ProviderFailure(ErrorCode.provider_invalid_response, "TinyFish Search returned an unexpected response.", False)

            candidates = []
            for item in raw_results:
                if not isinstance(item, dict):
                    continue
                raw_url = item.get("url")
                title = item.get("title")
                if isinstance(raw_url, str) and isinstance(title, str) and title.strip() and _safe_public_https_url(raw_url):
                    url = raw_url if raw_url.startswith("https://") else f"https://{raw_url}"
                    candidates.append((item, url))
                if len(candidates) >= 3:
                    break

            if not candidates:
                return NoticeResult(
                    status=NoticeStatus.no_match,
                    query=query,
                    results=[],
                    retrieved_at=datetime.now(timezone.utc),
                    freshness_threshold_seconds=threshold,
                    error=None,
                )

            fetch_response = await client.post(
                fetch_url,
                json={"urls": [url for _, url in candidates], "format": "markdown"},
                headers={**headers, "Content-Type": "application/json"},
            )
            if fetch_response.status_code == 429:
                raise _ProviderFailure(ErrorCode.provider_rate_limited, "TinyFish Fetch rate limit reached.", True)
            if fetch_response.status_code >= 500:
                raise _ProviderFailure(ErrorCode.provider_unavailable, "TinyFish Fetch is temporarily unavailable.", True)
            if fetch_response.status_code >= 400:
                raise _ProviderFailure(ErrorCode.provider_unavailable, "TinyFish Fetch rejected the request. Check backend configuration.", False)
            fetch_payload = fetch_response.json()
            fetched = fetch_payload.get("results", []) if isinstance(fetch_payload, dict) else []
            if not isinstance(fetched, list):
                raise _ProviderFailure(ErrorCode.provider_invalid_response, "TinyFish Fetch returned an unexpected response.", False)
            fetched_by_url = {
                str(item.get("url", "")).rstrip("/"): item
                for item in fetched if isinstance(item, dict) and isinstance(item.get("url"), str)
            }

            notices: list[Notice] = []
            saw_unknown_date = False
            for item, url in candidates:
                content = fetched_by_url.get(url.rstrip("/"))
                if not content:
                    continue
                domain = _domain(url)
                published = _parse_date(item.get("date") or item.get("published_at"))
                freshness = Freshness.unknown
                if published is not None:
                    age = (datetime.now(timezone.utc) - published).total_seconds()
                    freshness = Freshness.fresh if 0 <= age <= threshold else Freshness.stale
                if freshness != Freshness.fresh:
                    saw_unknown_date = True
                text = content.get("text") if isinstance(content.get("text"), str) else item.get("snippet")
                excerpt = " ".join(text.split())[:700] if isinstance(text, str) and text.strip() else None
                notices.append(Notice(
                    title=str(content.get("title") or item.get("title") or "Untitled public source")[:250],
                    source_url=url,
                    domain=domain,
                    excerpt=excerpt,
                    published_at=published,
                    retrieved_at=datetime.now(timezone.utc),
                    source_type=_source_type(domain),
                    freshness=freshness,
                    match_reason="Returned by TinyFish Search for the requested public-context query; relevance is contextual, not causal.",
                ))

            if not notices:
                raise _ProviderFailure(ErrorCode.provider_invalid_response, "TinyFish Fetch did not return usable pages.", False)
            final_status = NoticeStatus.stale if saw_unknown_date else NoticeStatus.success
            return NoticeResult(
                status=final_status,
                query=query,
                results=notices,
                retrieved_at=datetime.now(timezone.utc),
                freshness_threshold_seconds=threshold,
                error=None,
            )
    except _ProviderFailure as exc:
        return NoticeResult(
            status=NoticeStatus.provider_error,
            query=query,
            results=[],
            retrieved_at=datetime.now(timezone.utc),
            freshness_threshold_seconds=threshold,
            error=_error(exc.code, exc.message, exc.retryable),
        )
    except httpx.TimeoutException:
        return NoticeResult(
            status=NoticeStatus.provider_error,
            query=query,
            results=[],
            retrieved_at=datetime.now(timezone.utc),
            freshness_threshold_seconds=threshold,
            error=_error(ErrorCode.provider_timeout, "TinyFish did not respond before the timeout.", True),
        )
    except (httpx.HTTPError, ValueError, TypeError):
        return NoticeResult(
            status=NoticeStatus.provider_error,
            query=query,
            results=[],
            retrieved_at=datetime.now(timezone.utc),
            freshness_threshold_seconds=threshold,
            error=_error(ErrorCode.provider_invalid_response, "TinyFish returned an invalid response or the request failed.", True),
        )


class _ProviderFailure(Exception):
    def __init__(self, code: ErrorCode, message: str, retryable: bool):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
