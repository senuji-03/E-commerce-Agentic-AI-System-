import json
import time
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright
import re
import random


# Simple responsible AI practices
def _add_delay():
    """Add small delay to be respectful to servers"""
    time.sleep(random.uniform(1, 2))


def _get_bot_user_agent():
    """Transparent user agent that identifies our bot"""
    return "EcomAIAgent/1.0 (Price Tracker Bot) Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


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
    
    # Add initial delay
    _add_delay()

    with sync_playwright() as p:
        bot_user_agent = _get_bot_user_agent()
        
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                f'--user-agent={bot_user_agent}'
            ]
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=bot_user_agent
        )

        page = context.new_page()

        try:
            print(f"Navigating to Daraz search for brand: {brand}...")
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            
            # Check if page loaded successfully
            if "daraz" not in page.url.lower():
                print("Warning: Redirected away from Daraz. This might be due to anti-bot measures.")
                return []

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

            for i, card in enumerate(product_cards):
                try:
                    # Add small delay between products
                    if i > 0:
                        _add_delay()
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
            print("This might be due to:")
            print("- Network connectivity issues")
            print("- Daraz website changes") 
            print("- Anti-bot protection measures")

        finally:
            context.close()
            browser.close()

    return products_list


def save_products_to_json(products, path: str = "daraz_products.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)


# ====== Laptops Category Scraper (Daraz) ======
def build_laptops_url(brand: str | None = None) -> str:
    if brand:
        q = f"{brand} laptop"
        return f"https://www.daraz.lk/catalog/?{urlencode({'q': q, '_keyori': 'ss', 'from': 'input'})}"
    return "https://www.daraz.lk/laptops/"


def _brand_regex(brand: str) -> re.Pattern:
    # Normalize common brand variants for better matching
    variants = {
        "asus": ["asus"],
        "hp": ["hp", "hewlett", "hewlett-packard"],
        "msi": ["msi"],
        "apple": ["apple", "macbook"],
        "dell": ["dell"],
        "lenovo": ["lenovo", "thinkpad", "ideapad", "yoga"],
        "acer": ["acer"],
    }
    key = brand.strip().lower()
    words = variants.get(key, [key])
    # Build regex with word boundaries for any of the variants
    pattern = r"(" + r"|".join([re.escape(w) for w in words]) + r")"
    return re.compile(pattern, re.IGNORECASE)


def scrape_daraz_laptops(brand: str | None = None, threshold_str: str = "Rs. 400000", max_items: int = 40):
    url = build_laptops_url(brand)
    products_list = []
    brand_pat = _brand_regex(brand) if brand else None
    seen_urls = set()

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
            print("Navigating to Daraz laptops category...")
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            selectors_to_try = [
                "div[data-qa-locator='product-item']",
                ".gridItem--Yd0sa",
                "[data-qa-locator='product-item']",
                ".product-item",
                ".gridItem",
                "div.Bm3ON"
            ]

            def collect_cards():
                for selector in selectors_to_try:
                    cards = page.query_selector_all(selector)
                    if cards:
                        return cards
                return []

            # Progressive scroll to load more items
            product_cards = collect_cards()
            last_height = 0
            stable_rounds = 0
            for _ in range(20):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)
                product_cards = collect_cards()
                height = page.evaluate("document.body.scrollHeight")
                if height == last_height:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                last_height = height
                if stable_rounds >= 3 or len(product_cards) >= max_items:
                    break

            if not product_cards:
                content = page.content()
                with open("debug_laptops_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("No laptops found. Page content saved to debug_laptops_page.html")
                print("Page title:", page.title())
                return []

            def harvest(cards):
                nonlocal products_list, seen_urls
                for card in cards:
                    if len(products_list) >= max_items:
                        break
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

                        # Optional brand filter by product name
                        # Require brand match if provided
                        if brand_pat and name and not brand_pat.search(name):
                            continue
                        # Nudge to laptops-only results
                        if name and not re.search(r"laptop|notebook|macbook", name, re.IGNORECASE):
                            continue

                        if link in seen_urls:
                            continue

                        product = {
                            "name": name,
                            "price": price,
                            "url": link,
                            "threshold": threshold_str,
                            "brand": brand or "Laptops",
                            "source": "Daraz",
                        }

                        products_list.append(product)
                        seen_urls.add(link)

                    except Exception:
                        continue

            harvest(product_cards)

            # Follow pagination if available until we reach max_items
            next_selectors = [
                "li.ant-pagination-next:not(.ant-pagination-disabled) a",
                "a[title='Next Page']",
                "a[aria-label='Next']",
            ]
            page_num = 1
            while len(products_list) < max_items and page_num < 8:
                next_btn = None
                for sel in next_selectors:
                    el = page.query_selector(sel)
                    if el:
                        next_btn = el
                        break
                if not next_btn:
                    break
                next_btn.click()
                page.wait_for_timeout(2000)
                # Scroll on the new page as well
                for _ in range(10):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(800)
                product_cards = collect_cards()
                harvest(product_cards)
                page_num += 1
                # removed unreachable duplicate harvesting block that referenced undefined 'card'

        except Exception as e:
            print(f"Error during laptops scraping: {str(e)}")

        finally:
            context.close()
            browser.close()

    return products_list


def save_laptops_to_json(products, path: str = "daraz_laptops.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)


# ====== Headphones Category Scraper (Daraz) ======
def build_headphones_url(brand: str | None = None) -> str:
    if brand:
        q = f"{brand} headphones"
        return f"https://www.daraz.lk/catalog/?{urlencode({'q': q, '_keyori': 'ss', 'from': 'input'})}"
    return "https://www.daraz.lk/headphones-earphones/"


def _headphones_brand_regex(brand: str) -> re.Pattern:
    # Normalize common headphone brand variants for better matching
    variants = {
        "sony": ["sony"],
        "bose": ["bose"],
        "sennheiser": ["sennheiser"],
        "jbl": ["jbl"],
        "audio-technica": ["audio-technica", "audio technica"],
        "beats": ["beats"],
        "skullcandy": ["skullcandy"],
        "jabra": ["jabra"],
        "philips": ["philips"],
        "logitech": ["logitech"],
        "razer": ["razer"],
        "hyperx": ["hyperx", "hyper x"],
        "steelseries": ["steelseries", "steel series"],
        "corsair": ["corsair"],
        "plantronics": ["plantronics"],
        "poly": ["poly"],
    }
    key = brand.strip().lower()
    words = variants.get(key, [key])
    # Build regex with word boundaries for any of the variants
    pattern = r"(" + r"|".join([re.escape(w) for w in words]) + r")"
    return re.compile(pattern, re.IGNORECASE)


def scrape_daraz_headphones(brand: str | None = None, threshold_str: str = "Rs. 50000", max_items: int = 40):
    url = build_headphones_url(brand)
    products_list = []
    brand_pat = _headphones_brand_regex(brand) if brand else None
    seen_urls = set()

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
            print("Navigating to Daraz headphones category...")
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            selectors_to_try = [
                "div[data-qa-locator='product-item']",
                ".gridItem--Yd0sa",
                "[data-qa-locator='product-item']",
                ".product-item",
                ".gridItem",
                "div.Bm3ON"
            ]

            def collect_cards():
                for selector in selectors_to_try:
                    cards = page.query_selector_all(selector)
                    if cards:
                        return cards
                return []

            # Progressive scroll to load more items
            product_cards = collect_cards()
            last_height = 0
            stable_rounds = 0
            for _ in range(20):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)
                product_cards = collect_cards()
                height = page.evaluate("document.body.scrollHeight")
                if height == last_height:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                last_height = height
                if stable_rounds >= 3 or len(product_cards) >= max_items:
                    break

            if not product_cards:
                content = page.content()
                with open("debug_headphones_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("No headphones found. Page content saved to debug_headphones_page.html")
                print("Page title:", page.title())
                return []

            def harvest(cards):
                nonlocal products_list, seen_urls
                for card in cards:
                    if len(products_list) >= max_items:
                        break
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

                        # Optional brand filter by product name
                        # Require brand match if provided
                        if brand_pat and name and not brand_pat.search(name):
                            continue
                        # Nudge to headphones-only results
                        if name and not re.search(r"headphone|earphone|headset|earbud|wireless|bluetooth", name, re.IGNORECASE):
                            continue

                        if link in seen_urls:
                            continue

                        product = {
                            "name": name,
                            "price": price,
                            "url": link,
                            "threshold": threshold_str,
                            "brand": brand or "Headphones",
                            "source": "Daraz",
                        }

                        products_list.append(product)
                        seen_urls.add(link)

                    except Exception:
                        continue

            harvest(product_cards)

            # Follow pagination if available until we reach max_items
            next_selectors = [
                "li.ant-pagination-next:not(.ant-pagination-disabled) a",
                "a[title='Next Page']",
                "a[aria-label='Next']",
            ]
            page_num = 1
            while len(products_list) < max_items and page_num < 8:
                next_btn = None
                for sel in next_selectors:
                    el = page.query_selector(sel)
                    if el:
                        next_btn = el
                        break
                if not next_btn:
                    break
                next_btn.click()
                page.wait_for_timeout(2000)
                # Scroll on the new page as well
                for _ in range(10):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(800)
                product_cards = collect_cards()
                harvest(product_cards)
                page_num += 1

        except Exception as e:
            print(f"Error during headphones scraping: {str(e)}")

        finally:
            context.close()
            browser.close()

    return products_list


def save_headphones_to_json(products, path: str = "daraz_headphones.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)


# ====== Cameras Category Scraper (Daraz) ======
def build_cameras_url(brand: str | None = None) -> str:
    if brand:
        q = f"{brand} camera"
        return f"https://www.daraz.lk/catalog/?{urlencode({'q': q, '_keyori': 'ss', 'from': 'input'})}"
    # Daraz cameras and photos main category covers cameras and accessories; we'll rely on name filter
    return "https://www.daraz.lk/cameras-photos/"


def _cameras_brand_regex(brand: str) -> re.Pattern:
    variants = {
        "canon": ["canon"],
        "nikon": ["nikon"],
        "sony": ["sony"],
        "fujifilm": ["fujifilm", "fuji"],
        "panasonic": ["panasonic", "lumix"],
        "olympus": ["olympus", "om-system", "om system"],
        "gopro": ["gopro", "hero"],
        "dji": ["dji"],
        "pentax": ["pentax", "ricoh"],
        "sigma": ["sigma"],
    }
    key = brand.strip().lower()
    words = variants.get(key, [key])
    pattern = r"(" + r"|".join([re.escape(w) for w in words]) + r")"
    return re.compile(pattern, re.IGNORECASE)


def scrape_daraz_cameras(brand: str | None = None, threshold_str: str = "Rs. 400000", max_items: int = 40):
    url = build_cameras_url(brand)
    products_list = []
    brand_pat = _cameras_brand_regex(brand) if brand else None
    seen_urls = set()

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
            print("Navigating to Daraz cameras category...")
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            selectors_to_try = [
                "div[data-qa-locator='product-item']",
                ".gridItem--Yd0sa",
                "[data-qa-locator='product-item']",
                ".product-item",
                ".gridItem",
                "div.Bm3ON"
            ]

            def collect_cards():
                for selector in selectors_to_try:
                    cards = page.query_selector_all(selector)
                    if cards:
                        return cards
                return []

            # Progressive scroll to load more items
            product_cards = collect_cards()
            last_height = 0
            stable_rounds = 0
            for _ in range(20):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)
                product_cards = collect_cards()
                height = page.evaluate("document.body.scrollHeight")
                if height == last_height:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                last_height = height
                if stable_rounds >= 3 or len(product_cards) >= max_items:
                    break

            if not product_cards:
                content = page.content()
                with open("debug_cameras_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("No cameras found. Page content saved to debug_cameras_page.html")
                print("Page title:", page.title())
                return []

            def harvest(cards):
                nonlocal products_list, seen_urls
                for card in cards:
                    if len(products_list) >= max_items:
                        break
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

                        # Optional brand filter
                        if brand_pat and name and not brand_pat.search(name):
                            continue
                        # Camera-only filter (avoid accessories when possible)
                        if name and not re.search(r"camera|dslr|mirrorless|point\s*and\s*shoot|instax|polaroid|lomo|gopro|hero", name, re.IGNORECASE):
                            continue

                        if link in seen_urls:
                            continue

                        product = {
                            "name": name,
                            "price": price,
                            "url": link,
                            "threshold": threshold_str,
                            "brand": brand or "Cameras",
                            "source": "Daraz",
                        }

                        products_list.append(product)
                        seen_urls.add(link)

                    except Exception:
                        continue

            harvest(product_cards)

            # Follow pagination if available until we reach max_items
            next_selectors = [
                "li.ant-pagination-next:not(.ant-pagination-disabled) a",
                "a[title='Next Page']",
                "a[aria-label='Next']",
            ]
            page_num = 1
            while len(products_list) < max_items and page_num < 8:
                next_btn = None
                for sel in next_selectors:
                    el = page.query_selector(sel)
                    if el:
                        next_btn = el
                        break
                if not next_btn:
                    break
                next_btn.click()
                page.wait_for_timeout(2000)
                for _ in range(10):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(800)
                product_cards = collect_cards()
                harvest(product_cards)
                page_num += 1

        except Exception as e:
            print(f"Error during cameras scraping: {str(e)}")

        finally:
            context.close()
            browser.close()

    return products_list


def save_cameras_to_json(products, path: str = "daraz_cameras.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)


# ====== Smartwatches Category Scraper (Daraz) ======
def build_smartwatches_url(brand: str | None = None) -> str:
    if brand:
        q = f"{brand} smartwatch"
        return f"https://www.daraz.lk/catalog/?{urlencode({'q': q, '_keyori': 'ss', 'from': 'input'})}"
    return "https://www.daraz.lk/smart-watches/"


def _smartwatches_brand_regex(brand: str) -> re.Pattern:
    variants = {
        "apple": ["apple", "watch"],
        "samsung": ["samsung", "galaxy watch"],
        "huawei": ["huawei"],
        "xiaomi": ["xiaomi", "mi", "redmi"],
        "amazfit": ["amazfit"],
        "garmin": ["garmin"],
        "fitbit": ["fitbit"],
        "realme": ["realme"],
        "oneplus": ["oneplus", "one plus"],
        "oppo": ["oppo"],
        "noise": ["noise"],
        "boat": ["boat", "boAt"],
        "lenovo": ["lenovo"],
    }
    key = brand.strip().lower()
    words = variants.get(key, [key])
    pattern = r"(" + r"|".join([re.escape(w) for w in words]) + r")"
    return re.compile(pattern, re.IGNORECASE)


def scrape_daraz_smartwatches(brand: str | None = None, threshold_str: str = "Rs. 400000", max_items: int = 40):
    url = build_smartwatches_url(brand)
    products_list = []
    brand_pat = _smartwatches_brand_regex(brand) if brand else None
    seen_urls = set()

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
            print("Navigating to Daraz smartwatches category...")
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            selectors_to_try = [
                "div[data-qa-locator='product-item']",
                ".gridItem--Yd0sa",
                "[data-qa-locator='product-item']",
                ".product-item",
                ".gridItem",
                "div.Bm3ON"
            ]

            def collect_cards():
                for selector in selectors_to_try:
                    cards = page.query_selector_all(selector)
                    if cards:
                        return cards
                return []

            product_cards = collect_cards()
            last_height = 0
            stable_rounds = 0
            for _ in range(20):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)
                product_cards = collect_cards()
                height = page.evaluate("document.body.scrollHeight")
                if height == last_height:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                last_height = height
                if stable_rounds >= 3 or len(product_cards) >= max_items:
                    break

            if not product_cards:
                content = page.content()
                with open("debug_smartwatches_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("No smartwatches found. Page content saved to debug_smartwatches_page.html")
                print("Page title:", page.title())
                return []

            def harvest(cards):
                nonlocal products_list, seen_urls
                for card in cards:
                    if len(products_list) >= max_items:
                        break
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

                        if brand_pat and name and not brand_pat.search(name):
                            continue
                        # Smartwatch-only filter
                        if name and not re.search(r"smart\s*watch|smartwatch|galaxy watch|apple watch|fitbit|amazfit|garmin", name, re.IGNORECASE):
                            continue

                        if link in seen_urls:
                            continue

                        product = {
                            "name": name,
                            "price": price,
                            "url": link,
                            "threshold": threshold_str,
                            "brand": brand or "Smartwatches",
                            "source": "Daraz",
                        }

                        products_list.append(product)
                        seen_urls.add(link)

                    except Exception:
                        continue

            harvest(product_cards)

            next_selectors = [
                "li.ant-pagination-next:not(.ant-pagination-disabled) a",
                "a[title='Next Page']",
                "a[aria-label='Next']",
            ]
            page_num = 1
            while len(products_list) < max_items and page_num < 8:
                next_btn = None
                for sel in next_selectors:
                    el = page.query_selector(sel)
                    if el:
                        next_btn = el
                        break
                if not next_btn:
                    break
                next_btn.click()
                page.wait_for_timeout(2000)
                for _ in range(10):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(800)
                product_cards = collect_cards()
                harvest(product_cards)
                page_num += 1

        except Exception as e:
            print(f"Error during smartwatches scraping: {str(e)}")

        finally:
            context.close()
            browser.close()

    return products_list


def save_smartwatches_to_json(products, path: str = "daraz_smartwatches.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)


# ====== Bluetooth Speakers Category Scraper (Daraz) ======
def build_speakers_url(brand: str | None = None) -> str:
    if brand:
        q = f"{brand} bluetooth speaker"
        return f"https://www.daraz.lk/catalog/?{urlencode({'q': q, '_keyori': 'ss', 'from': 'input'})}"
    # Daraz speakers category often mixes accessories; use name filter
    return "https://www.daraz.lk/audio-speakers/"


def _speakers_brand_regex(brand: str) -> re.Pattern:
    variants = {
        "jbl": ["jbl"],
        "sony": ["sony"],
        "bose": ["bose"],
        "anker": ["anker", "soundcore"],
        "marshall": ["marshall"],
        "ue": ["ultimate ears", "ue", "boom", "megaboom"],
        "boat": ["boat", "boAt"],
        "xiaomi": ["xiaomi", "mi", "redmi"],
        "huawei": ["huawei"],
        "logitech": ["logitech"],
        "philips": ["philips"],
        "samsung": ["samsung"],
    }
    key = brand.strip().lower()
    words = variants.get(key, [key])
    pattern = r"(" + r"|".join([re.escape(w) for w in words]) + r")"
    return re.compile(pattern, re.IGNORECASE)


def scrape_daraz_speakers(brand: str | None = None, threshold_str: str = "Rs. 400000", max_items: int = 40):
    url = build_speakers_url(brand)
    products_list = []
    brand_pat = _speakers_brand_regex(brand) if brand else None
    seen_urls = set()

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
            print("Navigating to Daraz speakers category...")
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            selectors_to_try = [
                "div[data-qa-locator='product-item']",
                ".gridItem--Yd0sa",
                "[data-qa-locator='product-item']",
                ".product-item",
                ".gridItem",
                "div.Bm3ON"
            ]

            def collect_cards():
                for selector in selectors_to_try:
                    cards = page.query_selector_all(selector)
                    if cards:
                        return cards
                return []

            product_cards = collect_cards()
            last_height = 0
            stable_rounds = 0
            for _ in range(20):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)
                product_cards = collect_cards()
                height = page.evaluate("document.body.scrollHeight")
                if height == last_height:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                last_height = height
                if stable_rounds >= 3 or len(product_cards) >= max_items:
                    break

            if not product_cards:
                content = page.content()
                with open("debug_speakers_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("No speakers found. Page content saved to debug_speakers_page.html")
                print("Page title:", page.title())
                return []

            def harvest(cards):
                nonlocal products_list, seen_urls
                for card in cards:
                    if len(products_list) >= max_items:
                        break
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

                        if brand_pat and name and not brand_pat.search(name):
                            continue
                        # Speaker-only filter: prefer items that mention speaker and likely bluetooth
                        if name and not re.search(r"speaker|sound\s*box|boom$|megaboom|flip|charge|soundcore", name, re.IGNORECASE):
                            continue

                        if link in seen_urls:
                            continue

                        product = {
                            "name": name,
                            "price": price,
                            "url": link,
                            "threshold": threshold_str,
                            "brand": brand or "Speakers",
                            "source": "Daraz",
                        }

                        products_list.append(product)
                        seen_urls.add(link)

                    except Exception:
                        continue

            harvest(product_cards)

            next_selectors = [
                "li.ant-pagination-next:not(.ant-pagination-disabled) a",
                "a[title='Next Page']",
                "a[aria-label='Next']",
            ]
            page_num = 1
            while len(products_list) < max_items and page_num < 8:
                next_btn = None
                for sel in next_selectors:
                    el = page.query_selector(sel)
                    if el:
                        next_btn = el
                        break
                if not next_btn:
                    break
                next_btn.click()
                page.wait_for_timeout(2000)
                for _ in range(10):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(800)
                product_cards = collect_cards()
                harvest(product_cards)
                page_num += 1

        except Exception as e:
            print(f"Error during speakers scraping: {str(e)}")

        finally:
            context.close()
            browser.close()

    return products_list


def save_speakers_to_json(products, path: str = "daraz_speakers.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    print("Starting Daraz scrapers...")
    brand = "Samsung"
    threshold = "Rs. 400000"

    # Phones-like search by brand
    phone_products = scrape_daraz_products(brand, threshold)
    if phone_products:
        save_products_to_json(phone_products, "daraz_products.json")
        print(f"\n✅ Phones: scraped {len(phone_products)} products -> daraz_products.json")
    else:
        print("❌ Phones: no products scraped.")

    # Laptops category scrape (up to 40)
    laptop_products = scrape_daraz_laptops(None, threshold, max_items=80)
    if laptop_products:
        save_laptops_to_json(laptop_products, "daraz_laptops.json")
        print(f"\n✅ Laptops: scraped {len(laptop_products)} products -> daraz_laptops.json")
    else:
        print("❌ Laptops: no products scraped.")

    # Headphones category scrape (up to 40)
    headphone_products = scrape_daraz_headphones(None, "Rs. 50000", max_items=80)
    if headphone_products:
        save_headphones_to_json(headphone_products, "daraz_headphones.json")
        print(f"\n✅ Headphones: scraped {len(headphone_products)} products -> daraz_headphones.json")
    else:
        print("❌ Headphones: no products scraped.")