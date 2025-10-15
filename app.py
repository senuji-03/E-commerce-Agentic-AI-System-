from flask import Flask, render_template, request, redirect, url_for, flash
import os
import json
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from multi_scraper import scrape_all_sites, save_products_to_json
from price_tracker import load_products_from_json, check_prices, llm_summary_alerts
from recommendation_agent import recommend_products, load_products_from_json as load_products_for_reco, filter_below_threshold_products
from review_agent import analyze_product_reviews
from compare_agent import compare_selected_phones


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")


BRANDS = [
    "Samsung", "Xiaomi", "Apple", "Google", "Nokia", "Vivo", "Redmi", "Huawei"
]


def parse_price_numeric(price_str: str) -> int | None:
    # Lazy import from price_tracker to avoid duplication
    from price_tracker import parse_price
    return parse_price(price_str)


@app.route("/")
def index():
    products = load_products_from_json(os.path.join(os.path.dirname(__file__), "daraz_products.json"))
    total_products = len(products) if products else 0
    below_count = len(check_prices(products)) if products else 0
    last_brand = products[0].get("brand") if products else None
    # brand counts for simple chart
    brand_counts = {}
    for p in products or []:
        b = p.get("brand") or "Unknown"
        brand_counts[b] = brand_counts.get(b, 0) + 1
    return render_template(
        "index.html",
        brands=BRANDS,
        total_products=total_products,
        below_count=below_count,
        last_brand=last_brand,
        brand_counts=brand_counts,
        products=products,
    )


@app.route("/scrape", methods=["POST"])
def scrape():
    brand = request.form.get("brand") or "Samsung"
    threshold_input = request.form.get("threshold") or "Rs. 400000"
    # Normalize threshold to include Rs. prefix if numeric provided
    if threshold_input.isdigit():
        threshold_input = f"Rs. {int(threshold_input):,}".replace(",", "")

    # Scrape across multiple Sri Lankan retailers
    products = scrape_all_sites(brand, threshold_input)
    if not products:
        flash("No products scraped. Try another brand or try again.", "error")
        return redirect(url_for("index"))

    save_products_to_json(products, os.path.join(os.path.dirname(__file__), "daraz_products.json"))
    flash(f"Scraped {len(products)} products for {brand} across multiple sites.", "success")
    return redirect(url_for("tracker"))


@app.route("/tracker")
def tracker():
    products = load_products_from_json(os.path.join(os.path.dirname(__file__), "daraz_products.json"))
    alerts = check_prices(products) if products else []
    summary = llm_summary_alerts(alerts) if products else "🔍 No products tracked yet. Use the home page to scrape a brand first."
    alerts_by_url = {a["url"]: a for a in alerts}

    # Annotate products with below-threshold flag
    annotated: List[Dict] = []
    for p in products:
        url = p.get("url", "#")
        alert = alerts_by_url.get(url)
        annotated.append({
            **p,
            "below_threshold": bool(alert),
        })

    # Group by source website for the UI
    groups: Dict[str, List[Dict]] = {}
    for p in annotated:
        src = p.get("source") or "Daraz"
        groups.setdefault(src, []).append(p)

    return render_template("tracker.html", products=annotated, groups=groups, summary=summary)


@app.route("/recommendations", methods=["GET", "POST"])
def recommendations():
    all_products = load_products_for_reco(os.path.join(os.path.dirname(__file__), "daraz_products.json"))
    products = filter_below_threshold_products(all_products)
    recs: List[Dict] = []
    query_name = ""
    max_price = None
    quick_picks: List[str] = []

    if request.method == "POST":
        query_name = request.form.get("query") or ""
        max_price_raw = request.form.get("max_price") or ""
        below_names_raw = request.form.get("below_names") or ""
        if below_names_raw:
            quick_picks = [n for n in below_names_raw.split("||") if n]
        try:
            max_price = int(max_price_raw) if max_price_raw else None
        except ValueError:
            max_price = None

        if not query_name and products:
            query_name = products[0].get("name", "")
        if query_name:
            recs = recommend_products(query_name, products, top_n=5, max_price=max_price)

    return render_template("recommendations.html", products=products, recs=recs, query=query_name, quick_picks=quick_picks)


@app.route("/reviews", methods=["GET", "POST"])
def reviews():
    products = load_products_for_reco(os.path.join(os.path.dirname(__file__), "daraz_products.json"))
    product_query = ""
    chosen = None
    reviews_list: List[Dict] = []
    summary = ""

    if request.method == "POST":
        product_query = request.form.get("query") or ""
        if not product_query and products:
            product_query = products[0].get("name", "")
        if product_query:
            # pick the first matching product to get url if available
            for p in products or []:
                if product_query.lower() in (p.get("name", "").lower()):
                    chosen = p
                    break
            # Request all available reviews by passing a large max_reviews
            reviews_list, summary = analyze_product_reviews(product_query, (chosen or {}).get("url"), max_reviews=10000)

    return render_template("reviews.html", products=products, query=product_query, chosen=chosen, reviews=reviews_list, summary=summary)


@app.route("/compare", methods=["GET", "POST"])
def compare():
    products = load_products_for_reco(os.path.join(os.path.dirname(__file__), "daraz_products.json"))
    selected_urls: List[str] = []
    selected: List[Dict] = []
    priorities_raw = ""
    comparison = {"features": [], "summary": "", "highlights": []}

    if request.method == "POST":
        selected_urls = request.form.getlist("selected")
        priorities_raw = request.form.get("priorities") or ""
        priorities = [p.strip().lower() for p in priorities_raw.split(",") if p.strip()]
        # Map URLs to product dicts if present
        url_to_product = {p.get("url"): p for p in (products or [])}
        selected = [url_to_product.get(u, {"url": u, "name": u}) for u in selected_urls]
        comparison = compare_selected_phones(selected, priorities)

    return render_template("compare.html", products=products, selected=selected, comparison=comparison, priorities=priorities_raw)


## Alerts feature removed


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


