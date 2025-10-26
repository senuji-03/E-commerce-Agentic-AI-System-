from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import json
from typing import List, Dict
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

from scrape_daraz import save_products_to_json
from price_tracker import load_products_from_json, check_prices, llm_summary_alerts
from recommendation_agent import recommend_products, load_products_from_json as load_products_for_reco, filter_below_threshold_products
from review_agent import analyze_product_reviews
from compare_agent import compare_selected_phones
from enhanced_compare_agent import enhanced_compare_products
from scrape_daraz import scrape_daraz_products, scrape_daraz_laptops, scrape_daraz_headphones, scrape_daraz_cameras, scrape_daraz_smartwatches, scrape_daraz_speakers
from user_auth import UserAuth


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# Initialize user authentication
user_auth = UserAuth()


BRANDS = [
    "Samsung", "Xiaomi", "Apple", "Google", "Nokia", "Vivo", "Redmi", "Huawei"
]
LAPTOP_BRANDS = [
    "Dell", "ASUS", "HP", "Lenovo", "Apple", "Acer", "MSI"
]
HEADPHONE_BRANDS = [
    "Sony", "Bose", "Sennheiser", "JBL", "Audio-Technica", "Beats", "Skullcandy", 
    "Jabra", "Philips", "Logitech", "Razer", "HyperX", "SteelSeries", "Corsair"
]

CAMERA_BRANDS = [
    "Canon", "Nikon", "Sony", "Fujifilm", "Panasonic", "Olympus", "GoPro", "DJI", "Pentax"
]

SMARTWATCH_BRANDS = [
    "Apple", "Samsung", "Huawei", "Xiaomi", "Amazfit", "Garmin", "Fitbit", "Realme", "OnePlus", "OPPO"
]

SPEAKER_BRANDS = [
    "JBL", "Sony", "Bose", "Anker", "Marshall", "UE", "boAt", "Xiaomi", "Huawei", "Samsung", "Philips", "Logitech"
]


def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current logged in user data"""
    if 'user_id' in session:
        return user_auth.get_user_by_id(session['user_id'])
    return None


def parse_price_numeric(price_str: str) -> int | None:
    # Lazy import from price_tracker to avoid duplication
    from price_tracker import parse_price
    return parse_price(price_str)


def normalize_category(raw: str | None) -> str:
    cat = (raw or "phones").strip().lower()
    aliases = {
        "smartwatch": "smartwatches",
        "smart-watch": "smartwatches",
        "smart watch": "smartwatches",
        "smart-watches": "smartwatches",
        "smartwatches": "smartwatches",
        "watch": "smartwatches",
        "watches": "smartwatches",
        "camera": "cameras",
        "cameras": "cameras",
        "headphone": "headphones",
        "headphones": "headphones",
        "laptop": "laptops",
        "laptops": "laptops",
        "phone": "phones",
        "phones": "phones",
        "speaker": "speakers",
        "speakers": "speakers",
        "bluetooth speaker": "speakers",
        "bluetooth speakers": "speakers",
    }
    if cat in aliases:
        return aliases[cat]
    # Heuristic contains checks
    if ("smart" in cat and "watch" in cat):
        return "smartwatches"
    if "camera" in cat:
        return "cameras"
    if "headphone" in cat:
        return "headphones"
    if "speaker" in cat:
        return "speakers"
    if "laptop" in cat:
        return "laptops"
    if "phone" in cat:
        return "phones"
    return cat


@app.route("/")
def index():
    return render_template("launch.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        result = user_auth.login_user(username, password)
        
        if result["success"]:
            session['user_id'] = result['user_id']
            session['username'] = result['username']
            flash(result["message"], "success")
            return redirect(url_for('index'))
        else:
            flash(result["message"], "error")
    
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        # Basic validation
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")
        
        result = user_auth.register_user(username, email, password)
        
        if result["success"]:
            flash(result["message"], "success")
            return redirect(url_for('index'))
        else:
            flash(result["message"], "error")
    
    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('index'))


@app.route("/dashboard")
@login_required
def dashboard():
    category = normalize_category(request.args.get("category"))
    if category == "laptops":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_laptops.json")
        brands = LAPTOP_BRANDS
    elif category == "headphones":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_headphones.json")
        brands = HEADPHONE_BRANDS
    elif category == "cameras":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_cameras.json")
        brands = CAMERA_BRANDS
    elif category == "smartwatches":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_smartwatches.json")
        brands = SMARTWATCH_BRANDS
    elif category == "speakers":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_speakers.json")
        brands = SPEAKER_BRANDS
    else:
        data_path = os.path.join(os.path.dirname(__file__), "daraz_products.json")
        brands = BRANDS
    products = load_products_from_json(data_path)
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
        brands=brands,
        category=category,
        total_products=total_products,
        below_count=below_count,
        last_brand=last_brand,
        brand_counts=brand_counts,
        products=products,
    )


@app.route("/scrape", methods=["POST"])
@login_required
def scrape():
    category = normalize_category(request.form.get("category"))
    brand = request.form.get("brand") or ("Dell" if category == "laptops" else "Sony" if category == "headphones" else "Canon" if category == "cameras" else "Apple" if category == "smartwatches" else "JBL" if category == "speakers" else "Samsung")
    threshold_input = request.form.get("threshold") or ("Rs. 50000" if category == "headphones" else "Rs. 400000")
    # Normalize threshold to include Rs. prefix if numeric provided
    if threshold_input.isdigit():
        threshold_input = f"Rs. {int(threshold_input):,}".replace(",", "")

    if category == "laptops":
        # Daraz laptops category with brand filter, target 40 items per brand
        products = scrape_daraz_laptops(brand, threshold_input, max_items=40)
        save_path = os.path.join(os.path.dirname(__file__), "daraz_laptops.json")
    elif category == "headphones":
        # Daraz headphones category with brand filter, target 40 items per brand
        products = scrape_daraz_headphones(brand, threshold_input, max_items=40)
        save_path = os.path.join(os.path.dirname(__file__), "daraz_headphones.json")
    elif category == "cameras":
        # Daraz cameras category with brand filter, target 40 items per brand
        products = scrape_daraz_cameras(brand, threshold_input, max_items=40)
        save_path = os.path.join(os.path.dirname(__file__), "daraz_cameras.json")
    elif category == "smartwatches":
        # Daraz smartwatches category with brand filter, target 40 items per brand
        products = scrape_daraz_smartwatches(brand, threshold_input, max_items=40)
        save_path = os.path.join(os.path.dirname(__file__), "daraz_smartwatches.json")
    elif category == "speakers":
        # Daraz speakers category with brand filter, target 40 items per brand
        products = scrape_daraz_speakers(brand, threshold_input, max_items=40)
        save_path = os.path.join(os.path.dirname(__file__), "daraz_speakers.json")
    else:
        # Scrape Daraz for phones
        products = scrape_daraz_products(brand, threshold_input)
        save_path = os.path.join(os.path.dirname(__file__), "daraz_products.json")
    if not products:
        flash("No products scraped. Try another brand or try again.", "error")
        return redirect(url_for("dashboard"))

    save_products_to_json(products, save_path)
    if category == "laptops":
        flash(f"Scraped {len(products)} laptops.", "success")
        return redirect(url_for("tracker", category="laptops"))
    elif category == "headphones":
        flash(f"Scraped {len(products)} headphones.", "success")
        return redirect(url_for("tracker", category="headphones"))
    elif category == "cameras":
        flash(f"Scraped {len(products)} cameras.", "success")
        return redirect(url_for("tracker", category="cameras"))
    elif category == "smartwatches":
        flash(f"Scraped {len(products)} smartwatches.", "success")
        return redirect(url_for("tracker", category="smartwatches"))
    elif category == "speakers":
        flash(f"Scraped {len(products)} speakers.", "success")
        return redirect(url_for("tracker", category="speakers"))
    else:
        flash(f"Scraped {len(products)} products for {brand} across multiple sites.", "success")
        return redirect(url_for("tracker", category="phones"))


@app.route("/tracker")
@login_required
def tracker():
    category = normalize_category(request.args.get("category"))
    if category == "laptops":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_laptops.json")
    elif category == "headphones":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_headphones.json")
    elif category == "cameras":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_cameras.json")
    elif category == "smartwatches":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_smartwatches.json")
    elif category == "speakers":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_speakers.json")
    else:
        data_path = os.path.join(os.path.dirname(__file__), "daraz_products.json")
    products = load_products_from_json(data_path)
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

    return render_template("tracker.html", products=annotated, groups=groups, summary=summary, category=category)


@app.route("/recommendations", methods=["GET", "POST"])
@login_required
def recommendations():
    category = normalize_category(request.args.get("category") or request.form.get("category"))
    if category == "laptops":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_laptops.json")
    elif category == "headphones":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_headphones.json")
    elif category == "cameras":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_cameras.json")
    elif category == "smartwatches":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_smartwatches.json")
    elif category == "speakers":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_speakers.json")
    else:
        data_path = os.path.join(os.path.dirname(__file__), "daraz_products.json")
    all_products = load_products_for_reco(data_path)
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

    return render_template("recommendations.html", products=products, recs=recs, query=query_name, quick_picks=quick_picks, category=category)


@app.route("/reviews", methods=["GET", "POST"])
@login_required
def reviews():
    category = normalize_category(request.args.get("category") or request.form.get("category"))
    if category == "laptops":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_laptops.json")
    elif category == "headphones":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_headphones.json")
    elif category == "cameras":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_cameras.json")
    elif category == "smartwatches":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_smartwatches.json")
    elif category == "speakers":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_speakers.json")
    else:
        data_path = os.path.join(os.path.dirname(__file__), "daraz_products.json")
    products = load_products_for_reco(data_path)
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

    return render_template("reviews.html", products=products, query=product_query, chosen=chosen, reviews=reviews_list, summary=summary, category=category)


@app.route("/compare", methods=["GET", "POST"])
@login_required
def compare():
    category = normalize_category(request.args.get("category") or request.form.get("category"))
    if category == "laptops":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_laptops.json")
    elif category == "headphones":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_headphones.json")
    elif category == "cameras":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_cameras.json")
    elif category == "smartwatches":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_smartwatches.json")
    elif category == "speakers":
        data_path = os.path.join(os.path.dirname(__file__), "daraz_speakers.json")
    else:
        data_path = os.path.join(os.path.dirname(__file__), "daraz_products.json")
    products = load_products_for_reco(data_path)
    selected_urls: List[str] = []
    selected: List[Dict] = []
    priorities_raw = ""
    comparison = {"features": [], "summary": "", "highlights": []}
    enhanced_comparison = None

    if request.method == "POST":
        selected_urls = request.form.getlist("selected")
        priorities_raw = request.form.get("priorities") or ""
        priorities = [p.strip().lower() for p in priorities_raw.split(",") if p.strip()]
        # Map URLs to product dicts if present
        url_to_product = {p.get("url"): p for p in (products or [])}
        selected = [url_to_product.get(u, {"url": u, "name": u}) for u in selected_urls]
        
        # Use enhanced comparison if products are selected
        if selected and len(selected) > 0:
            try:
                enhanced_comparison = enhanced_compare_products(selected, priorities, category=category)
                flash("Comparison completed", "success")
            except Exception as e:
                flash(f"Enhanced comparison failed, using basic comparison: {str(e)}", "warning")
                comparison = compare_selected_phones(selected, priorities, category=category)
        else:
            comparison = compare_selected_phones(selected, priorities, category=category)

    return render_template("compare.html", 
                         products=products, 
                         selected=selected, 
                         comparison=comparison, 
                         enhanced_comparison=enhanced_comparison,
                         priorities=priorities_raw, 
                         category=category)


@app.route("/category/<category>")
@login_required
def category_hub(category: str):
    cat = normalize_category(category)
    if cat not in ("phones", "laptops", "headphones", "cameras", "smartwatches", "speakers"):
        cat = "phones"
    if cat == "laptops":
        brands = LAPTOP_BRANDS
    elif cat == "headphones":
        brands = HEADPHONE_BRANDS
    elif cat == "cameras":
        brands = CAMERA_BRANDS
    elif cat == "smartwatches":
        brands = SMARTWATCH_BRANDS
    elif cat == "speakers":
        brands = SPEAKER_BRANDS
    else:
        brands = BRANDS
    return render_template("category_hub.html", category=cat, brands=brands)


## Alerts feature removed


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


