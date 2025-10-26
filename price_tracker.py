import json
import re
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -------------------------------
# Try importing Gemini SDK
# -------------------------------
try:
    import google.generativeai as genai
    # ✅ Setup Gemini API key from environment variable
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception:
    genai = None

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
# Price Tracker Agent
# -------------------------------
def check_prices(products: List[Dict]):
    alerts = []
    valid_products = 0
    
    for i, product in enumerate(products, 1):
        name = product.get("name", "Unknown Product")
        price_str = product.get("price", "No Price")
        url = product.get("url", "#")
        threshold_str = product.get("threshold", "Rs. 400000")
        
        if name == "No Name" or price_str == "No Price":
            continue
            
        valid_products += 1
        
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
                print(f"      ℹ  Above threshold by Rs. {price - threshold:,}")
        else:
            print(f"      ⚠  Could not parse price data")
        
        print(f"      URL: {url[:60]}{'...' if len(url) > 60 else ''}")
        print("-" * 80)
    
    print(f"\nSummary: {valid_products} valid products processed, {len(alerts)} price alerts found.")
    return alerts

# -------------------------------
# AI Summary with Gemini
# -------------------------------
def llm_summary_alerts(alerts: List[Dict]):
    if not alerts:
        return "🔍 No price alerts at the moment. All monitored products are currently above their price thresholds."
    
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
1. Highlight the best deals
2. Mention total savings opportunities
3. Use emojis 🎉🛒💰
4. Keep it concise but engaging
"""
    
    if genai is not None:
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
    
    total_savings = sum(alert['savings'] for alert in alerts)
    return f"🎯 Found {len(alerts)} great deals with potential savings of Rs. {total_savings:,}! Check the details above for specific products."

# -------------------------------
# Load products
# -------------------------------
def load_products_from_json(path: str = "daraz_products.json") -> List[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {path} not found!")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {path}!")
        return []

# -------------------------------
# Main Execution
# -------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("🛒 DARAZ PRICE TRACKER AGENT")
    print("=" * 50)
    print()
    
    products = load_products_from_json("daraz_products.json")
    if not products:
        print("No products to process.")
        raise SystemExit(1)
    
    alerts = check_prices(products)
    
    print("\n" + "=" * 50)
    print("🤖 AI SUMMARY")
    print("=" * 50)
    
    summary = llm_summary_alerts(alerts)
    print(summary)
    
    if alerts:
        with open("price_alerts.json", "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=4)
        print(f"\n💾 Detailed alerts saved to price_alerts.json")
    
    print("\n" + "=" * 50)
