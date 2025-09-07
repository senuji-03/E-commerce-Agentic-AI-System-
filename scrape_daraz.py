import json
import time
from playwright.sync_api import sync_playwright

def scrape_daraz_products():
    url = "https://www.daraz.lk/smartphones/"
    products_list = []
    
    with sync_playwright() as p:
        # Launch browser with more realistic settings
        browser = p.chromium.launch(
            headless=False,  # Try with headless=False first to see what's happening
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        # Create context with more realistic settings
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        try:
            # Navigate with longer timeout
            print("Navigating to Daraz...")
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            
            # Wait for initial content
            page.wait_for_timeout(5000)
            
            # Try multiple possible selectors for products
            selectors_to_try = [
                "div[data-qa-locator='product-item']",
                ".gridItem--Yd0sa",
                "[data-qa-locator='product-item']",
                ".product-item",
                ".gridItem",
                "div.Bm3ON"  # Alternative selector
            ]
            
            product_cards = []
            for selector in selectors_to_try:
                print(f"Trying selector: {selector}")
                cards = page.query_selector_all(selector)
                if cards:
                    print(f"Found {len(cards)} products with selector: {selector}")
                    product_cards = cards
                    break
                page.wait_for_timeout(2000)
            
            if not product_cards:
                print("No product cards found. Let's try scrolling first...")
                # Scroll to load content
                for i in range(5):
                    print(f"Scrolling... {i+1}/5")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(3000)
                
                # Try selectors again after scrolling
                for selector in selectors_to_try:
                    cards = page.query_selector_all(selector)
                    if cards:
                        print(f"Found {len(cards)} products after scrolling with: {selector}")
                        product_cards = cards
                        break
            
            if not product_cards:
                # Debug: Save page content to see what we're getting
                content = page.content()
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("No products found. Page content saved to debug_page.html")
                print("Page title:", page.title())
                return []
            
            print(f"Processing {len(product_cards)} product cards...")
            
            for i, card in enumerate(product_cards):
                try:
                    print(f"Processing product {i+1}/{len(product_cards)}")
                    
                    # Try multiple selectors for name
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
                    
                    # Try multiple selectors for price
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
                    
                    # Fix URL format
                    if link and link != "#":
                        if link.startswith("//"):
                            link = "https:" + link
                        elif link.startswith("/"):
                            link = "https://www.daraz.lk" + link
                    
                    product = {
                        "name": name,
                        "price": price,
                        "url": link,
                        "threshold": "Rs. 400000"
                    }
                    
                    products_list.append(product)
                    print(f"Added: {name[:50]}... - {price}")
                    
                except Exception as e:
                    print(f"Error processing product {i+1}: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
        
        finally:
            context.close()
            browser.close()
    
    return products_list

# Run the scraper
if __name__ == "__main__":
    print("Starting Daraz scraper...")
    products = scrape_daraz_products()
    
    if products:
        # Save to JSON
        with open("daraz_products.json", "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=4)
        print(f"\n✅ Successfully scraped {len(products)} products!")
        print("Data saved to daraz_products.json")
        
        # Show first few products
        print("\nFirst 3 products:")
        for i, product in enumerate(products[:3]):
            print(f"{i+1}. {product['name']} - {product['price']}")
    else:
        print("❌ No products were scraped. Check the debug output above.")


        