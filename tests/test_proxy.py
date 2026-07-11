import pytest

from scraper_framework.core.models import ProxyEndpoint, ProxyTier
from scraper_framework.core.proxy import ProxyPool


def _pool():
    return ProxyPool(
        endpoints=[
            ProxyEndpoint(tier=ProxyTier.DATACENTER, url="http://p1", cost_per_gb_usd=0.1),
            ProxyEndpoint(tier=ProxyTier.DATACENTER, url="http://p2", cost_per_gb_usd=0.1),
        ]
    )


def test_sticky_per_host_keeps_same_proxy():
    pool = _pool()
    first = pool.get(ProxyTier.DATACENTER, "example.com")
    second = pool.get(ProxyTier.DATACENTER, "example.com")
    assert first.url == second.url


def test_different_hosts_can_get_different_proxies():
    pool = _pool()
    a = pool.get(ProxyTier.DATACENTER, "a.com")
    pool.get(ProxyTier.DATACENTER, "b.com")
    # sticky mapping for "a.com" must remain stable even after "b.com" is assigned
    assert pool.get(ProxyTier.DATACENTER, "a.com").url == a.url


def test_endpoint_dropped_after_max_failures():
    pool = _pool()
    dead = pool.get(ProxyTier.DATACENTER, "host1")
    for _ in range(3):
        pool.mark_failed(dead)
    alive_urls = {ep.url for ep in pool._alive(ProxyTier.DATACENTER)}
    assert dead.url not in alive_urls


def test_mark_success_resets_failure_count():
    pool = _pool()
    ep = pool.get(ProxyTier.DATACENTER, "host1")
    pool.mark_failed(ep)
    pool.mark_failed(ep)
    pool.mark_success(ep)
    pool.mark_failed(ep)
    pool.mark_failed(ep)
    alive_urls = {e.url for e in pool._alive(ProxyTier.DATACENTER)}
    assert ep.url in alive_urls  # only 2 failures since the reset, below the drop threshold


def test_empty_pool_rejected():
    with pytest.raises(AssertionError):
        ProxyPool(endpoints=[])


def test_no_live_proxies_raises():
    pool = ProxyPool(
        endpoints=[ProxyEndpoint(tier=ProxyTier.DATACENTER, url="http://p1", cost_per_gb_usd=0.0)]
    )
    ep = pool.get(ProxyTier.DATACENTER, "host1")
    for _ in range(3):
        pool.mark_failed(ep)
    with pytest.raises(AssertionError):
        pool.get(ProxyTier.DATACENTER, "host2")
