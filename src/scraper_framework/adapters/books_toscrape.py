"""Adapter for books.toscrape.com — a site built specifically for scraping practice.
Demonstrates the pattern: static HTML, HTTP fetch, datacenter-tier proxy is plenty."""
from __future__ import annotations

from bs4 import BeautifulSoup

from scraper_framework.core.models import FetchMethod, ProxyTier, ScrapedItem

_MAX_PAGES = 50  # the whole catalog is ~50 pages; cap so a bug can't spider forever


class BooksToScrapeAdapter:
    name = "books_toscrape"

    def seed_urls(self) -> list[str]:
        base = "https://books.toscrape.com/catalogue/page-{}.html"
        return [base.format(n) for n in range(1, _MAX_PAGES + 1)]

    def fetch_method(self) -> FetchMethod:
        return FetchMethod.HTTP  # fully static, no JS rendering needed

    def proxy_tier(self) -> ProxyTier:
        return ProxyTier.DATACENTER  # no anti-bot on this site; don't overspend on residential

    def parse(self, url: str, html: str) -> list[ScrapedItem]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[ScrapedItem] = []
        for card in soup.select("article.product_pod"):
            link = card.select_one("h3 a")
            price_el = card.select_one("p.price_color")
            availability_el = card.select_one("p.instock.availability")
            if link is None or price_el is None:
                continue  # a malformed card is data, not a crash
            title = link.get("title", "").strip()
            href = link.get("href", "")
            dedup_key = href.rsplit("/", 2)[-2] if href else title
            items.append(
                ScrapedItem(
                    source=self.name,
                    url=url,
                    dedup_key=dedup_key,
                    fields={
                        "title": title,
                        "price_text": price_el.get_text(strip=True),
                        "in_stock": bool(
                            availability_el and "In stock" in availability_el.get_text()
                        ),
                    },
                )
            )
        return items
