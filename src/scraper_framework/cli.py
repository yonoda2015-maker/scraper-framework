"""CLI entry point: run one adapter end to end and print a summary."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from scraper_framework.adapters.books_toscrape import BooksToScrapeAdapter
from scraper_framework.adapters.quotes_toscrape import QuotesToScrapeAdapter
from scraper_framework.core.engine import CrawlEngine, EngineConfig
from scraper_framework.core.models import CrawlOutcome, ProxyEndpoint, ProxyTier
from scraper_framework.core.proxy import ProxyPool
from scraper_framework.core.storage import Storage
from scraper_framework.fetchers import NO_PROXY, dispatch_fetch

_ADAPTERS = {
    "books_toscrape": BooksToScrapeAdapter,
    "quotes_toscrape": QuotesToScrapeAdapter,
}


async def _run(adapter_name: str, db_path: Path, concurrency: int) -> None:
    adapter = _ADAPTERS[adapter_name]()
    storage = Storage(db_path)
    # No paid proxies configured for this demo run; a single direct "endpoint" is enough
    # for sites with no anti-bot measures (books.toscrape.com / quotes.toscrape.com).
    pool = ProxyPool(
        endpoints=[ProxyEndpoint(tier=ProxyTier.DATACENTER, url=NO_PROXY, cost_per_gb_usd=0.0)]
    )
    engine = CrawlEngine(
        adapter,
        storage,
        pool,
        fetcher=dispatch_fetch,
        config=EngineConfig(concurrency=concurrency),
    )
    try:
        results = await engine.run()
        stored_count = storage.count(source=adapter.name)
    finally:
        storage.close()

    counts: dict[CrawlOutcome, int] = {}
    for r in results:
        counts[r.outcome] = counts.get(r.outcome, 0) + 1
    print(f"Crawled {len(results)} URLs with '{adapter_name}':")
    for outcome, n in counts.items():
        print(f"  {outcome.value}: {n}")
    print(f"Stored {stored_count} total rows in {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="scraper-framework")
    parser.add_argument("adapter", choices=sorted(_ADAPTERS))
    parser.add_argument("--db", type=Path, default=Path("scraped.db"))
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(_run(args.adapter, args.db, args.concurrency))


if __name__ == "__main__":
    main()
