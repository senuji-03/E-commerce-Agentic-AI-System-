import json
import time
from typing import List, Dict, Callable
from urllib.parse import urlencode

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None


Product = Dict[str, str]


def _normalize_price_str(price_text: str) -> str:
    if not price_text:
        return "No Price"
    # Keep original string; parse will be handled downstream
    return price_text.strip()


def _safe_launch(playwright):
    return playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
    )


def _scrape_daraz(brand: str, threshold_str: str, max_items: int = 40) -> List[Product]:
    if sync_playwright is None:
        return []
    products: List[Product] = []
    query_params = {"q": brand, "_keyori": "ss", "from": "input"}
    url = f"https://www.daraz.lk/catalog/?{urlencode(query_params)}"
    with sync_playwright() as p:
        browser = _safe_launch(p)
        context = browser.new_context(viewport={'width': 1600, 'height': 1000})
        page = context.new_page()
        try:
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(1200)
            selectors = [
                "div[data-qa-locator='product-item']",
                "div.Bm3ON",
                ".product-item",
            ]
            cards = []
            for sel in selectors:
                cards = page.query_selector_all(sel)
                if cards:
                    break
            if not cards:
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1000)
                for sel in selectors:
                    cards = page.query_selector_all(sel)
                    if cards:
                        break
            for card in cards:
                try:
                    name_el = card.query_selector("a[data-qa-locator='product-name'], [data-qa-locator='product-name'], .title--wFj93, h3, a[title]")
                    price_el = card.query_selector("span[data-qa-locator='product-price'], [data-qa-locator='product-price'], .currency--GVKjl, .price, span.ooOxS")
                    name = (name_el.inner_text().strip() if name_el else "No Name")
                    href = (name_el.get_attribute("href") if name_el else None) or "#"
                    if href.startswith("//"):
                        href = "https:" + href
                    elif href.startswith("/"):
                        href = "https://www.daraz.lk" + href
                    price = _normalize_price_str(price_el.inner_text() if price_el else "No Price")
                    products.append({
                        "name": name,
                        "price": price,
                        "url": href,
                        "threshold": threshold_str,
                        "brand": brand,
                        "source": "Daraz",
                    })
                    if len(products) >= max_items:
                        break
                except Exception:
                    continue
        finally:
            context.close()
            browser.close()
    return products


def _scrape_mysoftlogic(brand: str, threshold_str: str, max_items: int = 40) -> List[Product]:
    # Simple search page scrape; site structure may vary
    if sync_playwright is None:
        return []
    products: List[Product] = []
    url = f"https://www.mysoftlogic.lk/search?{urlencode({'q': brand})}"
    with sync_playwright() as p:
        browser = _safe_launch(p)
        context = browser.new_context(viewport={'width': 1600, 'height': 1000})
        page = context.new_page()
        try:
            page.goto(url, timeout=45000, wait_until='domcontentloaded')
            page.wait_for_timeout(1200)
            cards = page.query_selector_all(".product-grid .grid__item, .product-item, .card") or []
            for card in cards:
                try:
                    name_el = card.query_selector("a[href*='/products/'], .product-title a, a.card__heading")
                    price_el = card.query_selector(".price-item--regular, .price-item, .price")
                    name = (name_el.inner_text().strip() if name_el else "No Name")
                    href = (name_el.get_attribute('href') if name_el else "#")
                    if href and href.startswith("/"):
                        href = "https://www.mysoftlogic.lk" + href
                    price = _normalize_price_str(price_el.inner_text() if price_el else "No Price")
                    if name != "No Name" and href and href != "#":
                        products.append({
                            "name": name,
                            "price": price,
                            "url": href,
                            "threshold": threshold_str,
                            "brand": brand,
                            "source": "MySoftlogic",
                        })
                        if len(products) >= max_items:
                            break
                except Exception:
                    continue
        finally:
            context.close()
            browser.close()
    return products


def _scrape_singer(brand: str, threshold_str: str, max_items: int = 40) -> List[Product]:
    if sync_playwright is None:
        return []
    products: List[Product] = []
    url = f"https://www.singer.lk/search?{urlencode({'q': brand})}"
    with sync_playwright() as p:
        browser = _safe_launch(p)
        context = browser.new_context(viewport={'width': 1600, 'height': 1000})
        page = context.new_page()
        try:
            page.goto(url, timeout=45000, wait_until='domcontentloaded')
            page.wait_for_timeout(1200)
            cards = page.query_selector_all(".product-item, .product-grid .item, .product") or []
            for card in cards:
                try:
                    name_el = card.query_selector("a[href*='/products/'], .product-title a, a")
                    price_el = card.query_selector(".price, .price-box .price")
                    name = (name_el.inner_text().strip() if name_el else "No Name")
                    href = (name_el.get_attribute('href') if name_el else "#")
                    if href and href.startswith("/"):
                        href = "https://www.singer.lk" + href
                    price = _normalize_price_str(price_el.inner_text() if price_el else "No Price")
                    if name != "No Name" and href and href != "#":
                        products.append({
                            "name": name,
                            "price": price,
                            "url": href,
                            "threshold": threshold_str,
                            "brand": brand,
                            "source": "Singer",
                        })
                        if len(products) >= max_items:
                            break
                except Exception:
                    continue
        finally:
            context.close()
            browser.close()
    return products


def _scrape_buyabans(brand: str, threshold_str: str, max_items: int = 40) -> List[Product]:
    if sync_playwright is None:
        return []
    products: List[Product] = []
    url = f"https://buyabans.com/catalogsearch/result/?{urlencode({'q': brand})}"
    with sync_playwright() as p:
        browser = _safe_launch(p)
        context = browser.new_context(viewport={'width': 1600, 'height': 1000})
        page = context.new_page()
        try:
            page.goto(url, timeout=45000, wait_until='domcontentloaded')
            page.wait_for_timeout(1200)
            cards = page.query_selector_all(".product-item, .product, .item") or []
            for card in cards:
                try:
                    name_el = card.query_selector("a.product-item-link, a[href*='/smartphones'], a[href*='/product']")
                    price_el = card.query_selector("span.price, .price")
                    name = (name_el.inner_text().strip() if name_el else "No Name")
                    href = (name_el.get_attribute('href') if name_el else "#")
                    price = _normalize_price_str(price_el.inner_text() if price_el else "No Price")
                    if name != "No Name" and href and href != "#":
                        products.append({
                            "name": name,
                            "price": price,
                            "url": href,
                            "threshold": threshold_str,
                            "brand": brand,
                            "source": "Abans",
                        })
                        if len(products) >= max_items:
                            break
                except Exception:
                    continue
        finally:
            context.close()
            browser.close()
    return products


SCRAPERS: Dict[str, Callable[[str, str], List[Product]]] = {
    "Daraz": _scrape_daraz,
    "MySoftlogic": _scrape_mysoftlogic,
    "Singer": _scrape_singer,
    "Abans": _scrape_buyabans,
}


def scrape_all_sites(brand: str, threshold_str: str, max_per_site: int = 40) -> List[Product]:
    """Run all available scrapers and merge results. Fails gracefully per site."""
    all_products: List[Product] = []
    for source, fn in SCRAPERS.items():
        try:
            site_products = fn(brand, threshold_str, max_per_site)
            all_products.extend(site_products)
        except Exception:
            # Ignore individual site failures
            continue
    return all_products


def save_products_to_json(products: List[Product], path: str = "daraz_products.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)


