from scraper_framework.adapters.books_toscrape import BooksToScrapeAdapter
from scraper_framework.adapters.quotes_toscrape import QuotesToScrapeAdapter
from scraper_framework.core.models import FetchMethod, ProxyTier

_BOOKS_HTML = """
<html><body>
<article class="product_pod">
  <h3><a href="catalogue/a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light...</a></h3>
  <p class="price_color">£51.77</p>
  <p class="instock availability">In stock</p>
</article>
<article class="product_pod">
  <h3><a href="catalogue/soumission_998/index.html" title="Soumission">Soumission</a></h3>
  <p class="price_color">£50.10</p>
  <p class="instock availability">Out of stock</p>
</article>
</body></html>
"""

_QUOTES_HTML = """
<html><body>
<div class="quote">
  <span class="text">The world as we have created it is a process of our thinking.</span>
  <small class="author">Albert Einstein</small>
  <a class="tag">change</a>
  <a class="tag">deep-thoughts</a>
</div>
</body></html>
"""


def test_books_adapter_config():
    adapter = BooksToScrapeAdapter()
    urls = adapter.seed_urls()
    assert len(urls) == 50
    assert urls[0] == "https://books.toscrape.com/catalogue/page-1.html"
    assert adapter.fetch_method() == FetchMethod.HTTP
    assert adapter.proxy_tier() == ProxyTier.DATACENTER


def test_books_adapter_parses_items():
    items = BooksToScrapeAdapter().parse("http://x", _BOOKS_HTML)
    assert len(items) == 2
    assert items[0].fields["title"] == "A Light in the Attic"
    assert items[0].fields["price_text"] == "£51.77"
    assert items[0].fields["in_stock"] is True
    assert items[1].fields["in_stock"] is False
    assert items[0].dedup_key != items[1].dedup_key


def test_books_adapter_empty_page_returns_no_items():
    items = BooksToScrapeAdapter().parse("http://x", "<html><body></body></html>")
    assert items == []


def test_quotes_adapter_config():
    adapter = QuotesToScrapeAdapter()
    urls = adapter.seed_urls()
    assert len(urls) == 10
    assert urls[0] == "https://quotes.toscrape.com/page/1/"


def test_quotes_adapter_parses_items_with_tags():
    items = QuotesToScrapeAdapter().parse("http://x", _QUOTES_HTML)
    assert len(items) == 1
    assert items[0].fields["author"] == "Albert Einstein"
    assert items[0].fields["tags"] == ["change", "deep-thoughts"]
