import os
import re
from typing import List, Dict, Tuple

try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception:
    genai = None


def extract_basic_specs(name: str) -> Dict[str, str]:
    """Heuristic spec extraction from product name text."""
    text = (name or "").lower()
    specs: Dict[str, str] = {}
    # RAM/Storage patterns
    m = re.search(r"(\d{1,2})\s?gb\s?(?:ram)?", text)
    if m:
        specs["ram"] = f"{m.group(1)} GB"
    m2 = re.search(r"(\d{2,4})\s?gb\s?(?:storage|rom)?", text)
    if m2:
        specs["storage"] = f"{m2.group(1)} GB"
    # Camera megapixels
    m3 = re.search(r"(\d{2,3})\s?mp", text)
    if m3:
        specs["camera"] = f"{m3.group(1)} MP"
    # Battery mah
    m4 = re.search(r"(\d{3,5})\s?mah", text)
    if m4:
        specs["battery"] = f"{m4.group(1)} mAh"
    # Display inches
    m5 = re.search(r"(\d(?:\.\d)?)\s?in(?:ch|)", text)
    if m5:
        specs["display"] = f"{m5.group(1)} in"
    return specs


def compare_selected_phones(products: List[Dict], user_priorities: List[str]) -> Dict[str, object]:
    """Return a comparison table-like structure and an LLM summary when available."""
    # Normalize inputs
    normalized_priorities = [p.strip().lower() for p in (user_priorities or []) if p.strip()]
    # Canonical feature order
    canonical = ["price", "ram", "storage", "camera", "battery", "display", "brand", "source"]

    # Extract specs per product
    rows: List[Dict[str, str]] = []
    for p in products or []:
        row = {
            "name": p.get("name", "Unknown"),
            "price": p.get("price", "No Price"),
            "brand": p.get("brand", ""),
            "source": p.get("source", ""),
            "url": p.get("url", "#"),
        }
        row.update(extract_basic_specs(row["name"]))
        rows.append(row)

    # Determine highlights based on user priorities
    highlights: List[str] = []
    for pr in normalized_priorities:
        if pr in {"price"}:
            # lower is better
            try:
                values = []
                for idx, r in enumerate(rows):
                    m = re.findall(r"[\d,]+", r.get("price", ""))
                    v = int(m[0].replace(",", "")) if m else 10**12
                    values.append((v, idx))
                if values:
                    best_idx = sorted(values)[0][1]
                    highlights.append(f"Best price: {rows[best_idx]['name']} ({rows[best_idx]['price']})")
            except Exception:
                pass
        if pr in {"battery", "camera", "ram", "storage"}:
            key = pr
            try:
                def score(val: str) -> int:
                    m = re.findall(r"\d+", val or "")
                    return int(m[0]) if m else -1
                values = []
                for idx, r in enumerate(rows):
                    values.append((score(r.get(key, "")), idx))
                if values:
                    best_idx = sorted(values, reverse=True)[0][1]
                    pretty = rows[best_idx].get(key, "")
                    if pretty:
                        highlights.append(f"Best {key}: {rows[best_idx]['name']} ({pretty})")
            except Exception:
                pass

    # Build features matrix
    features: List[Dict[str, str]] = []
    headers = ["Feature"] + [r["name"] for r in rows]
    for key in canonical:
        line = {"Feature": key.capitalize()}
        for r in rows:
            line[r["name"]] = r.get(key, "—")
        features.append(line)

    # LLM summary if available
    summary = ""
    if genai and rows:
        try:
            bullets = []
            for r in rows:
                bullets.append(f"- {r['name']} | Price {r['price']} | RAM {r.get('ram','?')} | Storage {r.get('storage','?')} | Camera {r.get('camera','?')} | Battery {r.get('battery','?')} | Source {r.get('source','?')}")
            prompt = f"""
You are a helpful phone comparison assistant. Compare these phones and produce:
1) A short verdict about which phone fits which user priorities ({', '.join(normalized_priorities) or 'none specified'}).
2) Key trade-offs in one-liners.
3) A final recommendation per price/performance.

Phones:\n{chr(10).join(bullets)}
"""
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(prompt)
            summary = resp.text.strip()
        except Exception:
            summary = ""

    return {"features": features, "summary": summary, "highlights": highlights, "headers": headers}


