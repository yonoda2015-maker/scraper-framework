"""Core data types. Frozen dataclasses + enums so invalid states can't be constructed."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProxyTier(Enum):
    DATACENTER = "datacenter"
    RESIDENTIAL = "residential"
    MOBILE = "mobile"


class FetchMethod(Enum):
    HTTP = "http"
    BROWSER = "browser"


@dataclass(frozen=True, slots=True)
class ProxyEndpoint:
    tier: ProxyTier
    url: str
    cost_per_gb_usd: float

    def __post_init__(self) -> None:
        assert self.url, "proxy url must not be empty"
        assert self.cost_per_gb_usd >= 0, "proxy cost cannot be negative"


@dataclass(frozen=True, slots=True)
class FetchRequest:
    url: str
    method: FetchMethod
    proxy_tier: ProxyTier
    max_retries: int = 3

    def __post_init__(self) -> None:
        assert self.url.startswith(("http://", "https://")), f"not a URL: {self.url!r}"
        assert 0 <= self.max_retries <= 10, "max_retries out of sane range"


@dataclass(frozen=True, slots=True)
class ScrapedItem:
    """One extracted record. `fields` holds adapter-specific data.

    `dedup_key` must be built by the adapter from stable source fields
    (e.g. a listing ID), not from content, so re-scraping unchanged pages
    is a no-op and content edits are still picked up as updates.
    """

    source: str
    url: str
    dedup_key: str
    fields: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert self.source, "source must not be empty"
        assert self.dedup_key, "dedup_key must not be empty"

    def content_hash(self) -> str:
        """Hash of `fields` to detect real content changes vs. a pure re-fetch."""
        payload = repr(sorted(self.fields.items())).encode("utf-8")
        return hashlib.blake2b(payload, digest_size=16).hexdigest()


class CrawlOutcome(Enum):
    OK = "ok"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    FETCH_FAILED = "fetch_failed"
    PARSE_FAILED = "parse_failed"


@dataclass(frozen=True, slots=True)
class CrawlResult:
    """`items_stored` holds only the items that were new or changed (a page can
    yield many items; unchanged ones are still a successful crawl, just with
    nothing new to report)."""

    url: str
    outcome: CrawlOutcome
    items_stored: tuple[ScrapedItem, ...] = ()
    error: str | None = None

    def __post_init__(self) -> None:
        if self.outcome in (CrawlOutcome.FETCH_FAILED, CrawlOutcome.PARSE_FAILED):
            assert self.error, "failure result must carry an error message"
