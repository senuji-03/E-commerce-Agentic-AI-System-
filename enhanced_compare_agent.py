import os
import re
import json
from typing import List, Dict, Tuple, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception:
    genai = None

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None


def scrape_product_details(product_url: str, max_retries: int = 3) -> Dict[str, any]:
    """
    Scrape detailed product information from Daraz product page
    Returns comprehensive product details including specs, reviews, and features
    """
    if not product_url or sync_playwright is None:
        return {}
    
    product_details = {
        "url": product_url,
        "name": "",
        "price": "",
        "original_price": "",
        "rating": 0.0,
        "review_count": 0,
        "specifications": {},
        "features": [],
        "reviews_summary": "",
        "images": [],
        "availability": "",
        "seller": "",
        "warranty": "",
        "shipping": "",
        "description": ""
    }
    
    for attempt in range(max_retries):
        try:
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
                context = browser.new_context(viewport={'width': 1366, 'height': 900})
                page = context.new_page()
                
                try:
                    page.goto(product_url, timeout=30000, wait_until='domcontentloaded')
                    page.wait_for_timeout(3000)
                    
                    # Extract product name
                    name_selectors = [
                        "h1[data-qa-locator='product-title']",
                        ".pdp-product-name",
                        "h1.pdp-product-name",
                        ".product-title",
                        "h1"
                    ]
                    for selector in name_selectors:
                        try:
                            name_element = page.query_selector(selector)
                            if name_element:
                                product_details["name"] = name_element.inner_text().strip()
                                break
                        except:
                            continue
                    
                    # Extract price information
                    price_selectors = [
                        ".pdp-price-current",
                        ".pdp-price",
                        "[data-qa-locator='product-price']",
                        ".price-current"
                    ]
                    for selector in price_selectors:
                        try:
                            price_element = page.query_selector(selector)
                            if price_element:
                                product_details["price"] = price_element.inner_text().strip()
                                break
                        except:
                            continue
                    
                    # Extract original price
                    original_price_selectors = [
                        ".pdp-price-original",
                        ".price-original",
                        ".pdp-price-old"
                    ]
                    for selector in original_price_selectors:
                        try:
                            original_price_element = page.query_selector(selector)
                            if original_price_element:
                                product_details["original_price"] = original_price_element.inner_text().strip()
                                break
                        except:
                            continue
                    
                    # Extract rating and review count
                    try:
                        rating_element = page.query_selector(".pdp-review-summary__score, .rating-score, .review-score")
                        if rating_element:
                            rating_text = rating_element.inner_text().strip()
                            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                            if rating_match:
                                product_details["rating"] = float(rating_match.group(1))
                        
                        review_count_element = page.query_selector(".pdp-review-summary__count, .review-count, .rating-count")
                        if review_count_element:
                            review_text = review_count_element.inner_text().strip()
                            review_match = re.search(r'(\d+)', review_text)
                            if review_match:
                                product_details["review_count"] = int(review_match.group(1))
                    except:
                        pass
                    
                    # Extract specifications
                    try:
                        spec_sections = page.query_selector_all(".pdp-product-detail, .product-specs, .specifications")
                        for section in spec_sections:
                            spec_items = section.query_selector_all("tr, .spec-item, .spec-row")
                            for item in spec_items:
                                try:
                                    text = item.inner_text().strip()
                                    if ':' in text:
                                        key, value = text.split(':', 1)
                                        product_details["specifications"][key.strip()] = value.strip()
                                except:
                                    continue
                    except:
                        pass
                    
                    # Extract features
                    try:
                        feature_elements = page.query_selector_all(".pdp-product-highlights li, .features li, .product-features li")
                        for element in feature_elements:
                            feature_text = element.inner_text().strip()
                            if feature_text:
                                product_details["features"].append(feature_text)
                    except:
                        pass
                    
                    # Extract product images
                    try:
                        image_elements = page.query_selector_all(".pdp-product-image img, .product-image img, .gallery img")
                        for img in image_elements:
                            src = img.get_attribute("src") or img.get_attribute("data-src")
                            if src and src.startswith("http"):
                                product_details["images"].append(src)
                    except:
                        pass
                    
                    # Extract availability
                    try:
                        availability_element = page.query_selector(".pdp-product-availability, .availability, .stock-status")
                        if availability_element:
                            product_details["availability"] = availability_element.inner_text().strip()
                    except:
                        pass
                    
                    # Extract seller information
                    try:
                        seller_element = page.query_selector(".pdp-seller-name, .seller-name, .store-name")
                        if seller_element:
                            product_details["seller"] = seller_element.inner_text().strip()
                    except:
                        pass
                    
                    # Extract warranty information
                    try:
                        warranty_element = page.query_selector(".warranty, .guarantee, .pdp-warranty")
                        if warranty_element:
                            product_details["warranty"] = warranty_element.inner_text().strip()
                    except:
                        pass
                    
                    # Extract shipping information
                    try:
                        shipping_element = page.query_selector(".shipping-info, .delivery-info, .pdp-shipping")
                        if shipping_element:
                            product_details["shipping"] = shipping_element.inner_text().strip()
                    except:
                        pass
                    
                    # Extract product description
                    try:
                        desc_element = page.query_selector(".pdp-product-description, .product-description, .description")
                        if desc_element:
                            product_details["description"] = desc_element.inner_text().strip()
                    except:
                        pass
                    
                    # Extract recent reviews for AI analysis
                    try:
                        reviews = []
                        review_elements = page.query_selector_all(".review-item, .pdp-review-item, .review")
                        for review_element in review_elements[:10]:  # Limit to 10 reviews
                            try:
                                rating_elem = review_element.query_selector(".rating, .stars, .review-rating")
                                rating = 0
                                if rating_elem:
                                    rating_text = rating_elem.inner_text().strip()
                                    rating_match = re.search(r'(\d+)', rating_text)
                                    if rating_match:
                                        rating = int(rating_match.group(1))
                                
                                text_elem = review_element.query_selector(".review-text, .review-content, .content")
                                text = ""
                                if text_elem:
                                    text = text_elem.inner_text().strip()
                                
                                if text:
                                    reviews.append({"rating": rating, "text": text})
                            except:
                                continue
                        
                        if reviews:
                            product_details["reviews"] = reviews
                    except:
                        pass
                    
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    print(f"Scraping attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        print(f"All scraping attempts failed for {product_url}")
                finally:
                    context.close()
                    browser.close()
                    
        except Exception as e:
            print(f"Browser setup failed on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                print(f"All browser attempts failed for {product_url}")
    
    return product_details


def generate_ai_comparison_analysis(products_details: List[Dict], user_priorities: List[str], category: str) -> Dict[str, any]:
    """
    Generate comprehensive AI analysis using Gemini for product comparison
    """
    if not genai or not products_details:
        return {"summary": "AI analysis unavailable", "recommendations": [], "insights": []}
    
    # Prepare product data for AI analysis
    product_summaries = []
    for i, product in enumerate(products_details, 1):
        summary = f"""
Product {i}: {product.get('name', 'Unknown')}
- Price: {product.get('price', 'N/A')} (Original: {product.get('original_price', 'N/A')})
- Warranty: {product.get('warranty', 'Not specified')}
- Shipping: {product.get('shipping', 'Not specified')}

Key Specifications:
"""
        for spec, value in product.get('specifications', {}).items():
            summary += f"- {spec}: {value}\n"
        
        summary += f"\nKey Features:\n"
        for feature in product.get('features', [])[:5]:  # Top 5 features
            summary += f"- {feature}\n"
        
        if product.get('reviews'):
            summary += f"\nRecent Reviews Summary:\n"
            for review in product.get('reviews', [])[:3]:  # Top 3 reviews
                summary += f"- {review.get('rating', 0)}★: {review.get('text', '')[:100]}...\n"
        
        product_summaries.append(summary)
    
    # Create comprehensive prompt for Gemini
    prompt = f"""
You are an expert e-commerce analyst comparing {category} products. Analyze these products comprehensively:

{chr(10).join(product_summaries)}

User Priorities: {', '.join(user_priorities) if user_priorities else 'No specific priorities mentioned'}

Provide a detailed analysis including:

1. EXECUTIVE SUMMARY (2-3 sentences)
   - Overall market position and value proposition of each product

2. DETAILED COMPARISON
   - Price analysis (value for money, discounts, price positioning)
   - Feature comparison (unique features, missing features, feature quality)
   - Technical specifications comparison

3. STRENGTHS & WEAKNESSES
   - For each product, list 3 key strengths and 2 main weaknesses
   - Base this on actual specifications and features, not assumptions

4. USER PRIORITY ALIGNMENT
   - How well each product matches the user's stated priorities
   - Specific examples of how each product serves the priorities

5. RECOMMENDATIONS
   - Best overall choice with detailed reasoning
   - Best value for money choice
   - Best for specific use cases (if applicable)
   - Any products to avoid and why

6. BUYING ADVICE
   - What to consider before purchasing
   - Alternative options if none are suitable

7. FINAL VERDICT
   - Clear winner with 2-3 sentence justification
   - Confidence level in recommendation (High/Medium/Low)
   - Key factors that influenced the decision

Format your response clearly with headers and bullet points for easy reading.
"""
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        ai_analysis = response.text.strip()
        
        # Extract structured insights
        insights = {
            "executive_summary": "",
            "detailed_comparison": "",
            "strengths_weaknesses": "",
            "priority_alignment": "",
            "recommendations": "",
            "buying_advice": "",
            "final_verdict": ""
        }
        
        # Parse the response into sections
        sections = ai_analysis.split('\n')
        current_section = None
        
        for line in sections:
            line = line.strip()
            if line.startswith('1.') or 'EXECUTIVE SUMMARY' in line.upper():
                current_section = 'executive_summary'
            elif line.startswith('2.') or 'DETAILED COMPARISON' in line.upper():
                current_section = 'detailed_comparison'
            elif line.startswith('3.') or 'STRENGTHS' in line.upper():
                current_section = 'strengths_weaknesses'
            elif line.startswith('4.') or 'PRIORITY ALIGNMENT' in line.upper():
                current_section = 'priority_alignment'
            elif line.startswith('5.') or 'RECOMMENDATIONS' in line.upper():
                current_section = 'recommendations'
            elif line.startswith('6.') or 'BUYING ADVICE' in line.upper():
                current_section = 'buying_advice'
            elif line.startswith('7.') or 'FINAL VERDICT' in line.upper():
                current_section = 'final_verdict'
            
            if current_section and line:
                insights[current_section] += line + '\n'
        
        return {
            "full_analysis": ai_analysis,
            "insights": insights,
            "confidence": "High" if "high" in ai_analysis.lower() else "Medium" if "medium" in ai_analysis.lower() else "Low"
        }
        
    except Exception as e:
        print(f"AI analysis failed: {str(e)}")
        return {
            "summary": f"AI analysis failed: {str(e)}",
            "recommendations": [],
            "insights": {}
        }


def generate_best_option_recommendation(products_details: List[Dict], user_priorities: List[str], category: str) -> Dict[str, any]:
    """
    Generate a clear best option recommendation with concise explanation using Gemini AI
    """
    if not genai or not products_details:
        return {
            "product_name": products_details[0].get('name', 'Unknown') if products_details else 'No products',
            "explanation": "AI analysis unavailable",
            "confidence": "Low"
        }
    
    # Prepare concise product summary for best option analysis
    product_summaries = []
    for i, product in enumerate(products_details, 1):
        summary = f"""
Product {i}: {product.get('name', 'Unknown')}
- Price: {product.get('price', 'N/A')}
- Key Specs: {', '.join([f"{k}: {v}" for k, v in list(product.get('specifications', {}).items())[:3]])}
"""
        product_summaries.append(summary)
    
    # Create focused prompt for best option selection
    prompt = f"""
You are an expert e-commerce consultant. Based on the following {category} products, select the BEST OPTION and provide a concise explanation.

Products:
{chr(10).join(product_summaries)}

User Priorities: {', '.join(user_priorities) if user_priorities else 'No specific priorities mentioned'}

Your task:
1. Select the BEST OVERALL product from the list
2. Provide a SHORT explanation (2-3 sentences max) explaining why it's the best choice
3. Consider: price value, specifications, features, and user priorities

Format your response as:
BEST OPTION: [Product Name]
REASON: [2-3 sentence explanation focusing on the key advantages]

Be specific about what makes this product better than the others. Reference actual features, prices, or specifications when possible.
"""
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        ai_response = response.text.strip()
        
        # Parse the response to extract best option and reason
        best_option = "Unknown"
        explanation = "Analysis unavailable"
        confidence = "Medium"
        
        lines = ai_response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('BEST OPTION:') or line.startswith('Best Option:'):
                best_option = line.split(':', 1)[1].strip() if ':' in line else line
            elif line.startswith('REASON:') or line.startswith('Reason:'):
                explanation = line.split(':', 1)[1].strip() if ':' in line else line
        
        # If parsing failed, try to extract from the text
        if best_option == "Unknown":
            for product in products_details:
                if product.get('name', '').lower() in ai_response.lower():
                    best_option = product.get('name', 'Unknown')
                    break
        
        # Determine confidence based on response quality
        if len(explanation) > 50 and any(word in explanation.lower() for word in ['better', 'best', 'superior', 'advantage', 'excellent']):
            confidence = "High"
        elif len(explanation) > 20:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        return {
            "product_name": best_option,
            "explanation": explanation,
            "confidence": confidence,
            "full_response": ai_response
        }
        
    except Exception as e:
        print(f"Best option analysis failed: {str(e)}")
        # Fallback to heuristic selection
        if products_details:
            # Simple heuristic: prefer higher rated, lower priced products
            best_product = max(products_details, key=lambda p: (
                float(p.get('rating', 0)) * 0.7 +  # 70% weight on rating
                (1.0 / max(1, float(re.findall(r'[\d,]+', p.get('price', '0'))[0].replace(',', '')) if re.findall(r'[\d,]+', p.get('price', '0')) else 1)) * 0.3  # 30% weight on price (lower is better)
            ))
            return {
                "product_name": best_product.get('name', 'Unknown'),
                "explanation": f"Selected based on rating ({best_product.get('rating', 0)}/5) and price value. This product offers the best balance of quality and affordability.",
                "confidence": "Medium",
                "full_response": "Heuristic selection used due to AI analysis failure"
            }
        else:
            return {
                "product_name": "No products available",
                "explanation": "No products to compare",
                "confidence": "Low",
                "full_response": "No products available for comparison"
            }


def enhanced_compare_products(products: List[Dict], user_priorities: List[str], category: str) -> Dict[str, any]:
    """
    Enhanced product comparison with detailed scraping and AI analysis
    """
    print(f"🔍 Starting enhanced comparison for {len(products)} products...")
    
    # Scrape detailed information for each product
    detailed_products = []
    for i, product in enumerate(products, 1):
        print(f"📊 Scraping details for product {i}/{len(products)}: {product.get('name', 'Unknown')}")
        detailed_info = scrape_product_details(product.get('url', ''))
        
        # Merge with original product data
        enhanced_product = {**product, **detailed_info}
        detailed_products.append(enhanced_product)
    
    # Generate AI analysis
    print("🤖 Generating AI analysis...")
    ai_analysis = generate_ai_comparison_analysis(detailed_products, user_priorities, category)
    
    # Create comparison matrix
    comparison_matrix = []
    for product in detailed_products:
        row = {
            "name": product.get('name', 'Unknown'),
            "price": product.get('price', 'N/A'),
            "original_price": product.get('original_price', ''),
            "rating": product.get('rating', 0),
            "review_count": product.get('review_count', 0),
            "seller": product.get('seller', 'Unknown'),
            "availability": product.get('availability', 'Unknown'),
            "warranty": product.get('warranty', 'Not specified'),
            "shipping": product.get('shipping', 'Not specified'),
            "url": product.get('url', '#'),
            "specifications": product.get('specifications', {}),
            "features": product.get('features', []),
            "images": product.get('images', [])
        }
        comparison_matrix.append(row)
    
    # Generate best option recommendation
    best_option = generate_best_option_recommendation(detailed_products, user_priorities, category)
    
    return {
        "products": detailed_products,
        "comparison_matrix": comparison_matrix,
        "ai_analysis": ai_analysis,
        "best_option": best_option,
        "user_priorities": user_priorities,
        "category": category,
        "scraping_success": len([p for p in detailed_products if p.get('name')]) / len(products) if products else 0
    }


if __name__ == "__main__":
    # Test the enhanced comparison
    test_products = [
        {
            "name": "Samsung Galaxy S24 Ultra",
            "url": "https://www.daraz.lk/products/samsung-galaxy-s24-ultra-i1234567890.html",
            "price": "Rs. 250,000"
        }
    ]
    
    result = enhanced_compare_products(test_products, ["price", "camera", "battery"], "phones")
    print(json.dumps(result, indent=2, ensure_ascii=False))
