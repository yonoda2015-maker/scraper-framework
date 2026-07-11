"""Proxy pool: rotation, sticky sessions per host, and dropping dead endpoints.
Bandwidth-cost aware — never silently escalates to a pricier tier."""
from __future__ import annotations

from dataclasses import dataclass, field

from scraper_framework.core.models import ProxyEndpoint, ProxyTier

_MAX_FAILURES_BEFORE_DROP = 3
_MAX_POOL_SIZE = 10_000  # sanity ceiling; a real pool should never approach this


@dataclass
class ProxyPool:
    endpoints: list[ProxyEndpoint]
    _failure_counts: dict[str, int] = field(default_factory=dict, init=False)
    _sticky: dict[str, str] = field(default_factory=dict, init=False)  # host -> proxy url
    _cursor: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        assert len(self.endpoints) <= _MAX_POOL_SIZE, "proxy pool suspiciously large"
        assert len(self.endpoints) > 0, "proxy pool must not be empty"

    def _alive(self, tier: ProxyTier) -> list[ProxyEndpoint]:
        return [
            ep
            for ep in self.endpoints
            if ep.tier == tier
            and self._failure_counts.get(ep.url, 0) < _MAX_FAILURES_BEFORE_DROP
        ]

    def get(self, tier: ProxyTier, host: str) -> ProxyEndpoint:
        """Sticky per-host: same host keeps the same proxy until it's marked dead,
        so cookies/session state on the target site stay coherent."""
        sticky_url = self._sticky.get(host)
        if sticky_url is not None:
            for ep in self._alive(tier):
                if ep.url == sticky_url:
                    return ep

        alive = self._alive(tier)
        assert alive, f"no live proxies left for tier {tier}"
        self._cursor = (self._cursor + 1) % len(alive)
        chosen = alive[self._cursor]
        self._sticky[host] = chosen.url
        return chosen

    def mark_failed(self, endpoint: ProxyEndpoint) -> None:
        self._failure_counts[endpoint.url] = self._failure_counts.get(endpoint.url, 0) + 1

    def mark_success(self, endpoint: ProxyEndpoint) -> None:
        self._failure_counts[endpoint.url] = 0
