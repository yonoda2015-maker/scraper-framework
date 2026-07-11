"""Crawl engine. Owns concurrency, backpressure, and retry. Adapters never touch these."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from scraper_framework.core.adapter import SiteAdapter
from scraper_framework.core.models import (
    CrawlOutcome,
    CrawlResult,
    FetchMethod,
    ScrapedItem,
)
from scraper_framework.core.proxy import ProxyPool
from scraper_framework.core.storage import Storage

logger = logging.getLogger(__name__)

_MAX_URLS_PER_RUN = 500_000  # hard ceiling — a runaway seed list must not hang forever
_MAX_RETRIES_HARD_CAP = 10

Fetcher = Callable[[str, FetchMethod, str], Awaitable[str]]
"""(url, method, proxy_url) -> html. Injected so tests don't hit the network."""


@dataclass
class EngineConfig:
    concurrency: int = 10
    retry_backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        assert 1 <= self.concurrency <= 1000, "concurrency out of sane range"
        assert self.retry_backoff_seconds >= 0, "backoff cannot be negative"


class CrawlEngine:
    def __init__(
        self,
        adapter: SiteAdapter,
        storage: Storage,
        proxy_pool: ProxyPool,
        fetcher: Fetcher,
        config: EngineConfig | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._adapter = adapter
        self._storage = storage
        self._proxies = proxy_pool
        self._fetch = fetcher
        self._config = config or EngineConfig()
        self._sleep = sleep  # injected so tests don't actually wait on backoff

    async def run(self) -> list[CrawlResult]:
        urls = self._adapter.seed_urls()
        assert urls, "adapter returned no seed URLs"
        assert len(urls) <= _MAX_URLS_PER_RUN, (
            f"seed list has {len(urls)} URLs, over the {_MAX_URLS_PER_RUN} safety ceiling"
        )

        semaphore = asyncio.Semaphore(self._config.concurrency)
        results = await asyncio.gather(*(self._crawl_one(url, semaphore) for url in urls))
        return list(results)

    async def _crawl_one(self, url: str, semaphore: asyncio.Semaphore) -> CrawlResult:
        async with semaphore:
            from urllib.parse import urlparse

            host = urlparse(url).netloc
            assert host, f"URL has no host: {url!r}"

            method = self._adapter.fetch_method()
            tier = self._adapter.proxy_tier()
            max_retries = min(3, _MAX_RETRIES_HARD_CAP)

            html: str | None = None
            last_error = ""
            for attempt in range(max_retries + 1):
                try:
                    proxy = self._proxies.get(tier, host)
                except AssertionError as exc:
                    # pool exhausted (every endpoint dropped) — a crawl-time condition,
                    # not a programming bug, so it must not escape as an uncaught error
                    last_error = str(exc)
                    break

                try:
                    html = await self._fetch(url, method, proxy.url)
                    self._proxies.mark_success(proxy)
                    break
                except Exception as exc:  # noqa: BLE001 - crawl errors are data, not bugs
                    last_error = str(exc)
                    self._proxies.mark_failed(proxy)
                    if attempt < max_retries:
                        await self._sleep(self._config.retry_backoff_seconds * (attempt + 1))

            if html is None:
                return CrawlResult(url=url, outcome=CrawlOutcome.FETCH_FAILED, error=last_error)

            try:
                items = self._adapter.parse(url, html)
            except Exception as exc:  # noqa: BLE001
                return CrawlResult(url=url, outcome=CrawlOutcome.PARSE_FAILED, error=str(exc))

            if not items:
                return CrawlResult(url=url, outcome=CrawlOutcome.SKIPPED_DUPLICATE)

            stored = tuple(item for item in items if self._storage.upsert(item))
            outcome = CrawlOutcome.OK if stored else CrawlOutcome.SKIPPED_DUPLICATE
            return CrawlResult(url=url, outcome=outcome, items_stored=stored)
