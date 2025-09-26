import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import List, Dict

def load_products_from_json(path: str = "daraz_products.json") -> List[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []
def filter_below_threshold_products(products: List[Dict]) -> List[Dict]:
    filtered: List[Dict] = []
    for p in products or []:
        price_val = parse_price(p.get('price'))
        threshold_val = parse_price(p.get('threshold'))
        if price_val is not None and threshold_val is not None and price_val < threshold_val:
            filtered.append(p)
    return filtered


# -------------------------------
# Helper function to parse price
# -------------------------------
def parse_price(price_str):
    """Extract numerical value from price string like 'Rs. 12,500' or 'Rs.12500'"""
    if not price_str or price_str == "No Price":
        return None
    numbers = re.findall(r'[\d,]+', str(price_str))
    if numbers:
        try:
            return int(numbers[0].replace(',', ''))
        except ValueError:
            return None
    return None

# -------------------------------
# Recommendation Agent
# -------------------------------
def recommend_products(product_name: str, products: List[Dict], top_n: int = 5, max_price: int | None = None):
    """
    Recommend products using a composite score:
    - name similarity (TF-IDF cosine)
    - brand match bonus
    - price proximity bonus (if max_price provided)
    """
    if not products:
        print("No products available for recommendations.")
        return []

    # Filter by max_price if specified
    filtered_products = []
    for p in products:
        price_val = parse_price(p['price'])
        if max_price is None or (price_val is not None and price_val <= max_price):
            filtered_products.append(p)

    if not filtered_products:
        print("No products within the specified price range." if max_price is not None else "No products available.")
        return []

    # Create a list of product names
    product_names = [p['name'] for p in filtered_products]

    # Include the query product as the first item
    corpus = [product_name] + product_names

    # Vectorize names using TF-IDF
    vectorizer = TfidfVectorizer().fit_transform(corpus)
    vectors = vectorizer.toarray()

    # Compute cosine similarity between query and all products
    name_similarity = cosine_similarity([vectors[0]], vectors[1:])[0]

    # Extract brand from names heuristically (first token or within known brands)
    known_brands = {"samsung","xiaomi","apple","google","nokia","vivo","redmi","huawei","oneplus","realme","oppo","infinix"}
    q_lower = product_name.lower()
    q_brand = next((b for b in known_brands if b in q_lower), (q_lower.split()[0] if q_lower else ""))

    scores: List[float] = []
    for idx, p in enumerate(filtered_products):
        base = float(name_similarity[idx])
        # brand bonus
        p_name_lower = (p.get("name") or "").lower()
        p_brand = next((b for b in known_brands if b in p_name_lower), (p_name_lower.split()[0] if p_name_lower else ""))
        brand_bonus = 0.1 if q_brand and p_brand and q_brand == p_brand else 0.0
        # price proximity bonus (closer to max_price without exceeding)
        price_bonus = 0.0
        if max_price is not None:
            p_price = parse_price(p.get("price"))
            if p_price is not None and p_price <= max_price:
                # normalize proximity: closer to max_price gets slight boost
                proximity = 1.0 - (max(0, max_price - p_price) / max(max_price, 1))
                price_bonus = 0.1 * proximity
        scores.append(base + brand_bonus + price_bonus)

    top_indices = sorted(range(len(filtered_products)), key=lambda i: scores[i], reverse=True)[:top_n]
    recommendations = []
    for idx in top_indices:
        recommendations.append({
            "name": filtered_products[idx]["name"],
            "price": filtered_products[idx]["price"],
            "url": filtered_products[idx]["url"],
            "similarity_score": round(float(name_similarity[idx]), 2),
            "composite_score": round(float(scores[idx]), 2)
        })

    return recommendations

# -------------------------------
# Main Execution
# -------------------------------
if __name__ == "__main__":
    print("🛒 DARAZ RECOMMENDATION AGENT (PRICE-AWARE)")
    print("="*50)

    # Example: Recommend products similar to "Samsung Galaxy S24 Ultra"
    query_product = "Samsung Galaxy S24 Ultra"
    max_price_limit = 300000  # Optional: only recommend products under Rs. 300,000
    products = load_products_from_json("daraz_products.json")
    recommended = recommend_products(query_product, products, top_n=5, max_price=max_price_limit)

    if recommended:
        print(f"\nTop {len(recommended)} recommendations for '{query_product}' under Rs. {max_price_limit:,}:\n")
        for i, rec in enumerate(recommended, 1):
            print(f"{i}. {rec['name']} - {rec['price']} | {rec['url']} | Similarity: {rec['similarity_score']}")
    else:
        print("No recommendations found within the specified price range.")
