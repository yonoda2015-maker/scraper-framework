"""SQLite storage with idempotent upsert. Re-running a crawl must be a safe no-op
for unchanged items and a clean update for changed ones."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from scraper_framework.core.models import ScrapedItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    source TEXT NOT NULL,
    dedup_key TEXT NOT NULL,
    url TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    fields_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source, dedup_key)
);
"""


class Storage:
    """Not thread-safe across processes writing the same file concurrently beyond
    what SQLite's own locking provides — fine for a single crawl worker."""

    def __init__(self, db_path: Path) -> None:
        assert db_path.parent.exists(), f"parent dir missing: {db_path.parent}"
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def upsert(self, item: ScrapedItem) -> bool:
        """Returns True if this was a new record or the content changed, False if
        it was an identical re-fetch (a no-op re-send should not count as new)."""
        import json

        content_hash = item.content_hash()
        cur = self._conn.execute(
            "SELECT content_hash FROM items WHERE source = ? AND dedup_key = ?",
            (item.source, item.dedup_key),
        )
        row = cur.fetchone()
        if row is not None and row[0] == content_hash:
            self._conn.execute(
                "UPDATE items SET last_seen_at = datetime('now') "
                "WHERE source = ? AND dedup_key = ?",
                (item.source, item.dedup_key),
            )
            self._conn.commit()
            return False

        self._conn.execute(
            """
            INSERT INTO items (source, dedup_key, url, content_hash, fields_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source, dedup_key) DO UPDATE SET
                url = excluded.url,
                content_hash = excluded.content_hash,
                fields_json = excluded.fields_json,
                last_seen_at = datetime('now')
            """,
            (item.source, item.dedup_key, item.url, content_hash, json.dumps(item.fields)),
        )
        self._conn.commit()
        return True

    def count(self, source: str | None = None) -> int:
        if source is None:
            cur = self._conn.execute("SELECT COUNT(*) FROM items")
        else:
            cur = self._conn.execute("SELECT COUNT(*) FROM items WHERE source = ?", (source,))
        return cur.fetchone()[0]

    def close(self) -> None:
        self._conn.close()
