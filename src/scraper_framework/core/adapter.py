"""Adapter protocol. Adding a new site = writing one class, not touching the engine."""
from __future__ import annotations

from typing import Protocol

from scraper_framework.core.models import FetchMethod, ProxyTier, ScrapedItem


class SiteAdapter(Protocol):
    """One adapter per source site. The engine only ever calls these three methods."""

    name: str

    def seed_urls(self) -> list[str]:
        """URLs to start the crawl from. Must be non-empty and finite."""
        ...

    def fetch_method(self) -> FetchMethod:
        """HTTP is the default; only ask for a browser if the page needs JS to render."""
        ...

    def proxy_tier(self) -> ProxyTier:
        """Cheapest tier that reliably works for this site. Don't default to residential."""
        ...

    def parse(self, url: str, html: str) -> list[ScrapedItem]:
        """Extract items from one page's HTML. Return [] if nothing found (not an error)."""
        ...
