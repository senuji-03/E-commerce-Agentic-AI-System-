import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

# -------------------------------
# Load Products
# -------------------------------
with open("daraz_products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

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
def recommend_products(product_name, products, top_n=5, max_price=None):
    """
    Recommend products similar to the given product_name.
    Optionally, filter by max_price.
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
        print("No products within the specified price range.")
        return []

    # Create a list of product names
    product_names = [p['name'] for p in filtered_products]

    # Include the query product as the first item
    corpus = [product_name] + product_names

    # Vectorize names using TF-IDF
    vectorizer = TfidfVectorizer().fit_transform(corpus)
    vectors = vectorizer.toarray()

    # Compute cosine similarity between query and all products
    similarity = cosine_similarity([vectors[0]], vectors[1:])[0]

    # Get top N similar products
    top_indices = similarity.argsort()[::-1][:top_n]
    recommendations = []
    for idx in top_indices:
        recommendations.append({
            "name": filtered_products[idx]["name"],
            "price": filtered_products[idx]["price"],
            "url": filtered_products[idx]["url"],
            "similarity_score": round(float(similarity[idx]), 2)
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
    recommended = recommend_products(query_product, products, top_n=5, max_price=max_price_limit)

    if recommended:
        print(f"\nTop {len(recommended)} recommendations for '{query_product}' under Rs. {max_price_limit:,}:\n")
        for i, rec in enumerate(recommended, 1):
            print(f"{i}. {rec['name']} - {rec['price']} | {rec['url']} | Similarity: {rec['similarity_score']}")
    else:
        print("No recommendations found within the specified price range.")
