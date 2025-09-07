import json
import re
import google.generativeai as genai

# -------------------------------
# Setup Gemini API Key
# -------------------------------
api_key = "AIzaSyCjZUS1DVr0tmGnf3uAt-YVejrGCJ6UDS0"  # Replace with your actual Gemini API key
genai.configure(api_key=api_key)

# -------------------------------
# Load Products (Price Tracker)
# -------------------------------
try:
    with open("daraz_products.json", "r", encoding="utf-8") as f:
        products = json.load(f)
    print(f"Loaded {len(products)} products from daraz_products.json")
except FileNotFoundError:
    print("Error: daraz_products.json not found!")
    exit(1)
except json.JSONDecodeError:
    print("Error: Invalid JSON format in daraz_products.json!")
    exit(1)

# -------------------------------
# Helper function to parse price
# -------------------------------
def parse_price(price_str):
    """Extract numerical value from price string like 'Rs. 12,500' or 'Rs.12500'"""
    if not price_str or price_str == "No Price":
        return None
    
    # Remove currency symbols and extract numbers
    numbers = re.findall(r'[\d,]+', str(price_str))
    if numbers:
        try:
            return int(numbers[0].replace(',', ''))
        except ValueError:
            return None
    return None

# -------------------------------
# Price Tracker Agent
# -------------------------------
def check_prices(products):
    alerts = []
    valid_products = 0
    
    for i, product in enumerate(products, 1):
        name = product.get("name", "Unknown Product")
        price_str = product.get("price", "No Price")
        url = product.get("url", "#")
        threshold_str = product.get("threshold", "Rs. 400000")  # Default high threshold if not set
        
        # Skip products with no valid data
        if name == "No Name" or price_str == "No Price":
            continue
            
        valid_products += 1
        
        # Parse prices
        price = parse_price(price_str)
        threshold = parse_price(threshold_str)
        
        print(f"[{i:3d}] Product: {name[:60]}{'...' if len(name) > 60 else ''}")
        print(f"      Current Price: {price_str}")
        print(f"      Threshold: {threshold_str}")
        
        if price and threshold:
            print(f"      Parsed Price: Rs. {price:,} | Threshold: Rs. {threshold:,}")
            if price < threshold:
                alerts.append({
                    "name": name,
                    "current_price": price_str,
                    "threshold": threshold_str,
                    "url": url,
                    "savings": threshold - price
                })
                print(f"      🎉 PRICE ALERT: Below threshold by Rs. {threshold - price:,}!")
            else:
                print(f"      ℹ️  Above threshold by Rs. {price - threshold:,}")
        else:
            print(f"      ⚠️  Could not parse price data")
        
        print(f"      URL: {url[:60]}{'...' if len(url) > 60 else ''}")
        print("-" * 80)
    
    print(f"\nSummary: {valid_products} valid products processed, {len(alerts)} price alerts found.")
    return alerts

# -------------------------------
# LLM Agent (Gemini)
# -------------------------------
def llm_summary_alerts(alerts):
    if not alerts:
        return "🔍 No price alerts at the moment. All monitored products are currently above their price thresholds."
    
    # Create a detailed prompt
    alert_details = []
    for alert in alerts:
        alert_details.append(
            f"- {alert['name']} is now {alert['current_price']} "
            f"(threshold: {alert['threshold']}, savings: Rs. {alert['savings']:,})"
        )
    
    prompt = f"""
You are a helpful price tracking assistant. Please create a friendly and informative summary of these {len(alerts)} price alerts:

{chr(10).join(alert_details)}

Please:
1. Create an engaging summary highlighting the best deals
2. Mention total savings opportunities
3. Use emojis to make it more engaging
4. Keep it concise but informative
"""
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Fallback summary
        total_savings = sum(alert['savings'] for alert in alerts)
        return f"🎯 Found {len(alerts)} great deals with potential savings of Rs. {total_savings:,}! Check the details above for specific products."

# -------------------------------
# Main Execution
# -------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("🛒 DARAZ PRICE TRACKER AGENT")
    print("=" * 50)
    print()
    
    # Check for price alerts
    alerts = check_prices(products)
    
    print("\n" + "=" * 50)
    print("🤖 AI SUMMARY")
    print("=" * 50)
    
    # Get AI summary
    summary = llm_summary_alerts(alerts)
    print(summary)
    
    # Save alerts to file if any found
    if alerts:
        with open("price_alerts.json", "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=4)
        print(f"\n💾 Detailed alerts saved to price_alerts.json")
    
    print("\n" + "=" * 50)