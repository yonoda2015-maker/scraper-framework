"""Real network fetchers. Kept separate from the engine so tests inject a fake instead."""
from __future__ import annotations

import httpx

from scraper_framework.core.models import FetchMethod

_TIMEOUT_SECONDS = 30.0
_USER_AGENT = "scraper-framework-demo/0.1 (+https://github.com/)"
NO_PROXY = "direct://none"
"""Sentinel proxy URL meaning "fetch directly" — ProxyEndpoint.url must be non-empty
(see core/models.py), so an empty string isn't available to mean "no proxy"."""


async def http_fetch(url: str, method: FetchMethod, proxy_url: str) -> str:
    assert method == FetchMethod.HTTP, f"http_fetch cannot handle {method}"
    real_proxy = None if proxy_url == NO_PROXY else proxy_url
    async with httpx.AsyncClient(
        proxy=real_proxy,
        timeout=_TIMEOUT_SECONDS,
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def browser_fetch(url: str, method: FetchMethod, proxy_url: str) -> str:
    """Only imports Playwright when actually needed — most adapters never call this."""
    assert method == FetchMethod.BROWSER, f"browser_fetch cannot handle {method}"
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        launch_kwargs: dict[str, object] = {"headless": True}
        if proxy_url != NO_PROXY:
            launch_kwargs["proxy"] = {"server": proxy_url}
        browser = await pw.chromium.launch(**launch_kwargs)
        try:
            page = await browser.new_page(user_agent=_USER_AGENT)
            await page.goto(url, timeout=_TIMEOUT_SECONDS * 1000, wait_until="networkidle")
            return await page.content()
        finally:
            await browser.close()


async def dispatch_fetch(url: str, method: FetchMethod, proxy_url: str) -> str:
    """Single entry point the engine is wired to; routes to the right fetcher."""
    if method == FetchMethod.HTTP:
        return await http_fetch(url, method, proxy_url)
    return await browser_fetch(url, method, proxy_url)
