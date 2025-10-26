import re
import json
import os
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try Gemini for summaries; fall back to rule-based summary
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception:
    genai = None

# Try Playwright for scraping; fall back to mock
try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None


def extract_product_id_from_url(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"i\d{6,}", url)
    if m:
        return m.group(0)
    m = re.search(r"/product/([\w-]+)-(\d+)", url)
    if m:
        return m.group(2)
    return None


def mock_fetch_reviews(product_name: str, max_reviews: int = 20) -> List[Dict]:
    examples = [
        {"rating": 5, "text": f"Excellent {product_name}! Battery life is great and the screen is vivid."},
        {"rating": 4, "text": "Solid performance. Camera is good in daylight but average at night."},
        {"rating": 3, "text": "Okay for the price. Speakers are a bit weak."},
        {"rating": 2, "text": "Received late. Packaging was dented."},
        {"rating": 5, "text": "Super fast delivery and authentic product. Highly recommended!"},
    ]
    return examples[:max_reviews]


def scrape_daraz_reviews(product_url: str, max_reviews: int = 20) -> List[Dict]:
    if not product_url or sync_playwright is None:
        return []

    reviews: List[Dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ])
        context = browser.new_context(viewport={'width': 1366, 'height': 900})
        page = context.new_page()
        try:
            page.goto(product_url, timeout=120000, wait_until='domcontentloaded')
            page.wait_for_timeout(3000)

            # Try to navigate to reviews tab/section if available
            possible_tab_selectors = [
                "a[data-spm-anchor-id*='tab-reviews']",
                "a[href*='#reviews']",
                "#module_product_review a",
                "text=Ratings & Reviews",
            ]
            for sel in possible_tab_selectors:
                try:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        page.wait_for_timeout(1500)
                        break
                except Exception:
                    pass

            # Keep scrolling and try to click any "load more"/pagination until no new content is loaded
            last_height = 0
            stagnant_rounds = 0
            while True:
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)
                # Try clicking any load more buttons commonly used
                for sel in [
                    "button:has-text('Load More')",
                    "button:has-text('See More')",
                    "a:has-text('Load More')",
                    "a:has-text('See More')",
                    "button.load-more",
                    "button[data-qa-locator='view-more']",
                ]:
                    try:
                        btn = page.query_selector(sel)
                        if btn:
                            btn.click()
                            page.wait_for_timeout(1500)
                    except Exception:
                        pass
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    stagnant_rounds += 1
                else:
                    stagnant_rounds = 0
                last_height = new_height
                # break when we've had multiple stagnant rounds (no new content)
                if stagnant_rounds >= 3:
                    break

            candidate_blocks = []
            review_block_selectors = [
                "[data-qa-locator='review-item']",
                "div.review-item",
                "div.mod-reviews div.item",
                "div.c3yR0V",
                "div.c3XbGJ",
                "div.review",
            ]
            for sel in review_block_selectors:
                blocks = page.query_selector_all(sel)
                if blocks:
                    candidate_blocks = blocks
                    break

            if not candidate_blocks:
                # fallback: collect any elements that look like reviews via star icons + text length
                candidate_blocks = page.query_selector_all("text=/\d+ out of 5|★|\bstars?\b/i") or []

            for block in candidate_blocks:
                if len(reviews) >= max_reviews:
                    break
                try:
                    # Extract rating
                    rating = None
                    # aria-label like "4 out of 5"
                    star_el = block.query_selector("[aria-label*='out of 5'], [aria-label*='Out of 5']")
                    if star_el:
                        lab = (star_el.get_attribute("aria-label") or "")
                        m = re.search(r"(\d(?:\.\d)?)\s*out of\s*5", lab, re.I)
                        if m:
                            rating = float(m.group(1))
                    if rating is None:
                        # count filled stars
                        filled = block.query_selector_all(".star, .icon-star, .grade-star, .rating-star")
                        if filled:
                            rating = float(min(5, len(filled)))
                    if rating is None:
                        # try text content
                        txt = (block.inner_text() or "").strip()
                        m = re.search(r"(\d(?:\.\d)?)\s*/\s*5", txt)
                        if m:
                            rating = float(m.group(1))
                    # Extract text
                    text_el = None
                    for sel in [
                        "[data-qa-locator='review-item'] .content",
                        ".content",
                        ".review-content",
                        "p",
                        "div",
                    ]:
                        text_el = block.query_selector(sel)
                        if text_el and (text_el.inner_text() or "").strip():
                            break
                    text_val = (text_el.inner_text().strip() if text_el else (block.inner_text() or "").strip())
                    if not text_val:
                        continue
                    reviews.append({
                        "rating": rating if rating is not None else 0,
                        "text": text_val,
                    })
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            context.close()
            browser.close()

    # If max_reviews is very large, this effectively returns all collected
    return reviews[:max_reviews] if max_reviews else reviews


def summarize_reviews_llm(product_name: str, reviews: List[Dict]) -> str:
    if not reviews:
        return "No reviews available yet."
    bullets = [f"{r.get('rating','?')}★: {r.get('text','').strip()}" for r in reviews]
    prompt = f"""
You are a concise e-commerce review analyst. Given user reviews for {product_name}, produce:
1) One-line verdict with stars (e.g., 4.3/5)
2) Top 3 pros
3) Top 3 cons
4) Short buying advice in <= 25 words

Reviews:\n{chr(10).join(bullets)}
"""
    if genai is not None:
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except Exception:
            pass
    # Fallback heuristic summary
    ratings = [r.get("rating", 0) or 0 for r in reviews]
    avg = round(sum(ratings) / len(ratings), 1) if ratings else 0
    pros: List[str] = []
    cons: List[str] = []
    for r in reviews:
        t = (r.get("text") or "").lower()
        if any(k in t for k in ["great", "excellent", "good", "fast", "recommended", "authentic", "vivid", "battery"]):
            pros.append(r.get("text", ""))
        if any(k in t for k in ["late", "dented", "weak", "average", "bad", "poor", "noisy"]):
            cons.append(r.get("text", ""))
    pros = pros[:3]
    cons = cons[:3]
    advice = "Good overall value; check camera low-light and speaker needs before buying."
    lines = [
        f"Verdict: {avg}/5 ⭐",
        "Pros:",
        *([f"- {p}" for p in pros] or ["- —"]),
        "Cons:",
        *([f"- {c}" for c in cons] or ["- —"]),
        f"Advice: {advice}",
    ]
    return "\n".join(lines)


def analyze_product_reviews(product_name: str, product_url: str | None = None, max_reviews: int = 20) -> Tuple[List[Dict], str]:
    reviews: List[Dict] = []
    if product_url:
        try:
            reviews = scrape_daraz_reviews(product_url, max_reviews=max_reviews)
        except Exception:
            reviews = []
    if not reviews:
        reviews = mock_fetch_reviews(product_name, max_reviews=max_reviews)
    summary = summarize_reviews_llm(product_name, reviews)
    return reviews, summary


if __name__ == "__main__":
    name = "Samsung Galaxy S24 Ultra"
    reviews, summary = analyze_product_reviews(name)
    print(json.dumps(reviews, ensure_ascii=False, indent=2))
    print("\n--- SUMMARY ---\n")
    print(summary)


