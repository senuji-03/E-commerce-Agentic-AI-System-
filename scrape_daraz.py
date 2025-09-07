import json
import time
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright


def build_search_url(brand: str) -> str:
    query_params = {
        "q": brand,
        "_keyori": "ss",
        "from": "input",
    }
    return f"https://www.daraz.lk/catalog/?{urlencode(query_params)}"


def scrape_daraz_products(brand: str, threshold_str: str = "Rs. 400000"):
    url = build_search_url(brand)
    products_list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        page = context.new_page()

        try:
            print(f"Navigating to Daraz search for brand: {brand}...")
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            selectors_to_try = [
                "div[data-qa-locator='product-item']",
                ".gridItem--Yd0sa",
                "[data-qa-locator='product-item']",
                ".product-item",
                ".gridItem",
                "div.Bm3ON"
            ]

            product_cards = []
            for selector in selectors_to_try:
                cards = page.query_selector_all(selector)
                if cards:
                    product_cards = cards
                    break
                page.wait_for_timeout(1500)

            if not product_cards:
                for i in range(5):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2500)
                for selector in selectors_to_try:
                    cards = page.query_selector_all(selector)
                    if cards:
                        product_cards = cards
                        break

            if not product_cards:
                content = page.content()
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("No products found. Page content saved to debug_page.html")
                print("Page title:", page.title())
                return []

            for card in product_cards:
                try:
                    name_selectors = [
                        "a[data-qa-locator='product-name']",
                        "[data-qa-locator='product-name']",
                        ".title--wFj93",
                        "h3",
                        "a[title]"
                    ]

                    name = "No Name"
                    link = "#"
                    name_tag = None
                    for name_sel in name_selectors:
                        name_tag = card.query_selector(name_sel)
                        if name_tag:
                            name = name_tag.inner_text().strip()
                            link = name_tag.get_attribute("href") or "#"
                            break

                    price_selectors = [
                        "span[data-qa-locator='product-price']",
                        "[data-qa-locator='product-price']",
                        ".currency--GVKjl",
                        ".price",
                        "span.ooOxS"
                    ]

                    price = "No Price"
                    for price_sel in price_selectors:
                        price_tag = card.query_selector(price_sel)
                        if price_tag:
                            price = price_tag.inner_text().strip()
                            break

                    if link and link != "#":
                        if link.startswith("//"):
                            link = "https:" + link
                        elif link.startswith("/"):
                            link = "https://www.daraz.lk" + link

                    product = {
                        "name": name,
                        "price": price,
                        "url": link,
                        "threshold": threshold_str,
                        "brand": brand
                    }

                    products_list.append(product)

                except Exception:
                    continue

        except Exception as e:
            print(f"Error during scraping: {str(e)}")

        finally:
            context.close()
            browser.close()

    return products_list


def save_products_to_json(products, path: str = "daraz_products.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    print("Starting Daraz scraper...")
    brand = "Samsung"
    threshold = "Rs. 400000"
    products = scrape_daraz_products(brand, threshold)

    if products:
        save_products_to_json(products, "daraz_products.json")
        print(f"\n✅ Successfully scraped {len(products)} products!")
        print("Data saved to daraz_products.json")
        for i, product in enumerate(products[:3]):
            print(f"{i+1}. {product['name']} - {product['price']}")
    else:
        print("❌ No products were scraped. Check the debug output above.")