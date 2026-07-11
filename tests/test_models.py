import pytest

from scraper_framework.core.models import (
    CrawlOutcome,
    CrawlResult,
    FetchMethod,
    FetchRequest,
    ProxyEndpoint,
    ProxyTier,
    ScrapedItem,
)


def test_scraped_item_requires_source_and_dedup_key():
    with pytest.raises(AssertionError):
        ScrapedItem(source="", url="http://x", dedup_key="k")
    with pytest.raises(AssertionError):
        ScrapedItem(source="s", url="http://x", dedup_key="")


def test_content_hash_stable_for_same_fields_different_order():
    a = ScrapedItem(source="s", url="http://x", dedup_key="k", fields={"a": 1, "b": 2})
    b = ScrapedItem(source="s", url="http://x", dedup_key="k", fields={"b": 2, "a": 1})
    assert a.content_hash() == b.content_hash()


def test_content_hash_changes_with_fields():
    a = ScrapedItem(source="s", url="http://x", dedup_key="k", fields={"a": 1})
    b = ScrapedItem(source="s", url="http://x", dedup_key="k", fields={"a": 2})
    assert a.content_hash() != b.content_hash()


def test_fetch_request_rejects_non_url():
    with pytest.raises(AssertionError):
        FetchRequest(url="not-a-url", method=FetchMethod.HTTP, proxy_tier=ProxyTier.DATACENTER)


def test_fetch_request_rejects_out_of_range_retries():
    with pytest.raises(AssertionError):
        FetchRequest(
            url="http://x",
            method=FetchMethod.HTTP,
            proxy_tier=ProxyTier.DATACENTER,
            max_retries=11,
        )


def test_proxy_endpoint_rejects_negative_cost():
    with pytest.raises(AssertionError):
        ProxyEndpoint(tier=ProxyTier.DATACENTER, url="http://p", cost_per_gb_usd=-1.0)


def test_failure_result_must_carry_error():
    with pytest.raises(AssertionError):
        CrawlResult(url="http://x", outcome=CrawlOutcome.FETCH_FAILED, error=None)
    # this must not raise
    CrawlResult(url="http://x", outcome=CrawlOutcome.FETCH_FAILED, error="boom")
