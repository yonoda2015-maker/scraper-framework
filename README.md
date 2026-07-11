# scraper-framework

A small, adapter-pattern web scraping framework: adding a new source site means
writing one class, not touching the crawl engine, storage, or proxy pool.

Built as a portfolio piece modeled on real-world scraping job specs (multi-site
crawling, proxy rotation with cost awareness, idempotent storage, retry/backoff).
Two example adapters target [books.toscrape.com](https://books.toscrape.com) and
[quotes.toscrape.com](https://quotes.toscrape.com) — sites built specifically for
scraping practice, so the demo has no ToS or legal gray area.

## Architecture

```
src/scraper_framework/
  core/
    models.py    # frozen dataclasses + enums — invalid states can't be constructed
    adapter.py   # SiteAdapter protocol — the only thing a new site needs to implement
    engine.py    # CrawlEngine — concurrency, retry/backoff, proxy handling
    storage.py   # SQLite upsert — idempotent by (source, dedup_key) + content hash
    proxy.py     # ProxyPool — sticky-per-host rotation, drops dead endpoints
  adapters/
    books_toscrape.py
    quotes_toscrape.py
  fetchers.py    # real HTTP/browser fetchers (only file that touches the network)
  cli.py         # `scraper-framework <adapter>` entry point
tests/           # no network calls — Fetcher and sleep are injected fakes
```

**Design choices, and why:**

- **Idempotent storage, not just dedup.** `Storage.upsert()` hashes an item's fields
  and only writes when the hash changed. Re-running a crawl is always safe — it
  never double-counts unchanged data, but still picks up real edits.
- **`dedup_key` vs. content hash are deliberately separate.** `dedup_key` must come
  from a stable source-side identifier (a listing slug, a quote+author pair), never
  from content — otherwise editing a record's content would look like a new record
  instead of an update to the same one.
- **Dependency-injected fetcher and sleep.** `CrawlEngine` takes a `Fetcher` callable
  and a `sleep` callable instead of calling `httpx`/`asyncio.sleep` directly. Tests
  inject fakes, so the suite runs in milliseconds with zero network access and zero
  real backoff delay.
- **Frozen dataclasses + enums over loose dicts/strings.** `ProxyTier`, `FetchMethod`,
  and `CrawlOutcome` are enums; `ScrapedItem`/`FetchRequest`/`ProxyEndpoint`/`CrawlResult`
  are frozen with `__post_init__` assertions. Most invalid states (empty dedup key,
  negative cost, out-of-range retry count) simply cannot be constructed.
- **Hard ceilings on unbounded loops.** Seed lists are capped at `_MAX_URLS_PER_RUN`,
  retries at `_MAX_RETRIES_HARD_CAP`, proxy pool size at `_MAX_POOL_SIZE` — a bad
  adapter or config can't make a run hang or grow without bound.
- **Proxy-pool exhaustion is a crawl-time condition, not a crash.** If every endpoint
  for a tier has been dropped for excessive failures, `_crawl_one` reports
  `FETCH_FAILED` for that URL instead of letting the pool's internal assertion
  propagate as an uncaught error mid-run.

## Adding a new adapter

Implement the three-method `SiteAdapter` protocol and register it in `cli.py`:

```python
class MySiteAdapter:
    name = "my_site"

    def seed_urls(self) -> list[str]:
        return [f"https://example.com/page/{n}" for n in range(1, 11)]

    def fetch_method(self) -> FetchMethod:
        return FetchMethod.HTTP  # or BROWSER if the page needs JS to render

    def proxy_tier(self) -> ProxyTier:
        return ProxyTier.DATACENTER  # cheapest tier that reliably works

    def parse(self, url: str, html: str) -> list[ScrapedItem]:
        # return [] if nothing found — that's a normal outcome, not an error
        ...
```

Nothing in `core/` changes.

## Install & run

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest tests/ -q          # 27 tests, no network access
.venv/bin/pip install -e ".[browser]"          # only needed for BROWSER-method adapters
.venv/bin/scraper-framework books_toscrape --db out.db
.venv/bin/scraper-framework quotes_toscrape --db out.db
```

## Status

Two working adapters, 27 passing unit tests (engine, storage, proxy pool, models,
adapter parsing), SQLite storage, sticky-rotation proxy pool, CLI. Not yet wired to
a real proxy vendor or a distributed queue — the design leaves room for both without
touching adapter code.
