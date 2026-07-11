"""Second adapter for quotes.toscrape.com — shows that adding a new source is
just one small file; the engine, storage, and proxy pool are untouched."""
from __future__ import annotations

import hashlib

from bs4 import BeautifulSoup

from scraper_framework.core.models import FetchMethod, ProxyTier, ScrapedItem

_MAX_PAGES = 10


class QuotesToScrapeAdapter:
    name = "quotes_toscrape"

    def seed_urls(self) -> list[str]:
        base = "https://quotes.toscrape.com/page/{}/"
        return [base.format(n) for n in range(1, _MAX_PAGES + 1)]

    def fetch_method(self) -> FetchMethod:
        return FetchMethod.HTTP

    def proxy_tier(self) -> ProxyTier:
        return ProxyTier.DATACENTER

    def parse(self, url: str, html: str) -> list[ScrapedItem]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[ScrapedItem] = []
        for block in soup.select("div.quote"):
            text_el = block.select_one("span.text")
            author_el = block.select_one("small.author")
            if text_el is None or author_el is None:
                continue
            text = text_el.get_text(strip=True)
            author = author_el.get_text(strip=True)
            # quotes.toscrape.com has no stable per-quote ID, so the key is derived
            # from content. Must use a deterministic hash, not builtin hash() — that
            # one is randomized per process (PYTHONHASHSEED) and would break
            # idempotency across separate runs.
            text_digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).hexdigest()
            dedup_key = f"{author}:{text_digest}"
            tags = [t.get_text(strip=True) for t in block.select("a.tag")]
            items.append(
                ScrapedItem(
                    source=self.name,
                    url=url,
                    dedup_key=dedup_key,
                    fields={"text": text, "author": author, "tags": tags},
                )
            )
        return items
