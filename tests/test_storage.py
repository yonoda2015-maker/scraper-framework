from scraper_framework.core.models import ScrapedItem
from scraper_framework.core.storage import Storage


def test_upsert_new_item_returns_true(tmp_db_path):
    storage = Storage(tmp_db_path)
    item = ScrapedItem(source="s", url="http://x", dedup_key="k1", fields={"a": 1})
    assert storage.upsert(item) is True
    assert storage.count() == 1
    storage.close()


def test_upsert_unchanged_item_returns_false(tmp_db_path):
    storage = Storage(tmp_db_path)
    item = ScrapedItem(source="s", url="http://x", dedup_key="k1", fields={"a": 1})
    storage.upsert(item)
    assert storage.upsert(item) is False
    assert storage.count() == 1
    storage.close()


def test_upsert_changed_content_returns_true_and_updates(tmp_db_path):
    storage = Storage(tmp_db_path)
    storage.upsert(ScrapedItem(source="s", url="http://x", dedup_key="k1", fields={"a": 1}))
    changed = ScrapedItem(source="s", url="http://x", dedup_key="k1", fields={"a": 2})
    assert storage.upsert(changed) is True
    assert storage.count() == 1  # still one row, same dedup_key, content updated
    storage.close()


def test_count_filters_by_source(tmp_db_path):
    storage = Storage(tmp_db_path)
    storage.upsert(ScrapedItem(source="a", url="http://x", dedup_key="k1"))
    storage.upsert(ScrapedItem(source="b", url="http://y", dedup_key="k2"))
    assert storage.count(source="a") == 1
    assert storage.count() == 2
    storage.close()
