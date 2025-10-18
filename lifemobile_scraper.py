import json
import time
from playwright.sync_api import sync_playwright

def scrape_lifemobile():
    url = "https://lifemobile.lk/product-category/mobile-phones/"  # Update if needed
    products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        print("Navigating to Life Mobile phones page...")
        page.goto(url, timeout=120000, wait_until="domcontentloaded")

        # Scroll to load products
        print("Scrolling to load products...")
        for _ in range(3):
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            time.sleep(3)

        # Use the correct CSS selector for product containers
        product_cards = page.query_selector_all("li.product")  # updated for WooCommerce lists
        print(f"Total product cards found: {len(product_cards)}")

        if not product_cards:
            print("No products found. Check the CSS selector.")
            browser.close()
            return []

        for i, card in enumerate(product_cards, 1):
            try:
                # Name
                name_tag = card.query_selector("h2.woocommerce-loop-product__title, h1.product_title.entry-title")
                name = name_tag.inner_text().strip() if name_tag else "No Name"

                # Price
                price_tag = card.query_selector("span.woocommerce-Price-amount, p.price")
                price = price_tag.inner_text().strip() if price_tag else "No Price"

                # URL
                link_tag = card.query_selector("a")
                link = link_tag.get_attribute("href") if link_tag else "#"

                products.append({
                    "name": name,
                    "price": price,
                    "url": link
                })

                print(f"{i}. {name} - {price} | {link}")

            except Exception as e:
                print(f"Error processing product {i}: {e}")
                continue

        browser.close()

    # Save to JSON
    if products:
        with open("lifemobile_products.json", "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=4)
        print(f"\n✅ Scraped {len(products)} products. Saved to lifemobile_products.json")

    return products

if __name__ == "__main__":
    scrape_lifemobile()
