import os
import re
from typing import List, Dict, Tuple

try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception:
    genai = None


def extract_basic_specs(name: str, category: str = "phones") -> Dict[str, str]:
    """Heuristic spec extraction from product name text."""
    text = (name or "").lower()
    specs: Dict[str, str] = {}
    
    if category == "headphones":
        # Headphone-specific patterns
        # Driver size
        m = re.search(r"(\d{1,2})\s?mm\s?(?:driver|driver)", text)
        if m:
            specs["driver"] = f"{m.group(1)} mm"
        # Frequency response
        m2 = re.search(r"(\d{2,3})\s?hz\s?-\s?(\d{2,4})\s?hz", text)
        if m2:
            specs["frequency"] = f"{m2.group(1)}-{m2.group(2)} Hz"
        # Impedance
        m3 = re.search(r"(\d{2,3})\s?ohm", text)
        if m3:
            specs["impedance"] = f"{m3.group(1)} Ohm"
        # Battery life for wireless
        m4 = re.search(r"(\d{1,2})\s?h(?:our|r)?\s?(?:battery|playback)", text)
        if m4:
            specs["battery"] = f"{m4.group(1)} hours"
        # Noise cancellation
        if "noise" in text and "cancel" in text:
            specs["noise_cancellation"] = "Yes"
        elif "anc" in text:
            specs["noise_cancellation"] = "Yes"
        # Wireless/Bluetooth
        if "wireless" in text or "bluetooth" in text:
            specs["wireless"] = "Yes"
        elif "wired" in text:
            specs["wireless"] = "No"
    else:
        # Phone/Laptop patterns
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


def compare_selected_phones(products: List[Dict], user_priorities: List[str], category: str | None = None) -> Dict[str, object]:
    """Return a comparison table-like structure and an LLM summary when available."""
    # Normalize inputs
    normalized_priorities = [p.strip().lower() for p in (user_priorities or []) if p.strip()]
    # Canonical feature order based on category
    if category == "headphones":
        canonical = ["price", "driver", "frequency", "impedance", "battery", "wireless", "noise_cancellation", "brand", "source"]
    else:
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
        row.update(extract_basic_specs(row["name"], category or "phones"))
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
        if pr in {"battery", "camera", "ram", "storage", "driver", "frequency", "impedance"}:
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
    best_overall = ""
    if genai and rows:
        try:
            bullets = []
            for r in rows:
                if category == "headphones":
                    bullets.append(f"- {r['name']} | Price {r['price']} | Driver {r.get('driver','?')} | Frequency {r.get('frequency','?')} | Impedance {r.get('impedance','?')} | Battery {r.get('battery','?')} | Wireless {r.get('wireless','?')} | Noise Cancellation {r.get('noise_cancellation','?')} | Source {r.get('source','?')}")
                else:
                    bullets.append(f"- {r['name']} | Price {r['price']} | RAM {r.get('ram','?')} | Storage {r.get('storage','?')} | Camera {r.get('camera','?')} | Battery {r.get('battery','?')} | Source {r.get('source','?')}")
            domain = (category or "phones").lower()
            prompt = f"""
You are a helpful {domain} comparison assistant. Compare these items and produce:

1) Give a short verdict aligned to user priorities: {', '.join(normalized_priorities) or 'none specified'}.
2) List 3-6 key trade-offs (one line each), using only the available data; do NOT assume or invent missing specs.
3) Give a final recommendation per price/performance.
4) Provide a concise rationale that references the features you actually have, explaining why the winner is better.
5) Determine the winner by assigning points:
   - 1 point for strictly lower price (ignore if equal)
   - 1 point for strictly higher numeric specs (ignore if equal)
   Ignore any missing values when scoring. The item with the most points wins.
6) When giving the reason, only mention specific features if they are strictly better than the others. Do NOT mention a feature if it is equal or worse when writing the "Why".
7) On the last two lines, print exactly:
Best overall: <PRODUCT_NAME>
Why: <ONE_OR_TWO_SENTENCES_WITH_FEATURE-BASED_REASON>

Items:\n{chr(10).join(bullets)}
"""
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(prompt)
            summary = resp.text.strip()
            # Try to extract explicit best pick from last line
            try:
                for line in summary.splitlines()[::-1]:
                    m = re.search(r"Best overall:\s*(.+)", line, re.IGNORECASE)
                    if m:
                        best_overall = m.group(1).strip()
                        break
            except Exception:
                best_overall = ""
            # Try to extract reason line
            try:
                best_reason = ""
                for line in summary.splitlines()[::-1]:
                    rm = re.search(r"Why:\s*(.+)", line, re.IGNORECASE)
                    if rm:
                        best_reason = rm.group(1).strip()
                        break
            except Exception:
                best_reason = ""
        except Exception:
            summary = ""

    # Fallback heuristic best if model didn't provide one
    if not best_overall and rows:
        try:
            # Prefer best price if price in priorities, otherwise first item
            if "price" in normalized_priorities:
                values = []
                for idx, r in enumerate(rows):
                    m = re.findall(r"[\d,]+", r.get("price", ""))
                    v = int(m[0].replace(",", "")) if m else 10**12
                    values.append((v, idx))
                if values:
                    best_overall = rows[sorted(values)[0][1]]["name"]
            if not best_overall:
                best_overall = rows[0]["name"]
        except Exception:
            best_overall = rows[0]["name"]

    # Simple fallback reason if none extracted
    if 'best_reason' not in locals() or not best_reason:
        # Build a heuristic insight referencing concrete features
        try:
            best_idx = None
            for i, r in enumerate(rows):
                if r.get('name') == best_overall:
                    best_idx = i
                    break
            reason_bits: List[str] = []
            if best_idx is not None:
                best = rows[best_idx]
                # Price advantage (lower is better)
                def parse_price(text: str) -> int:
                    m = re.findall(r"[\d,]+", text or "")
                    return int(m[0].replace(",", "")) if m else 10**12
                best_price = parse_price(best.get('price', ''))
                others = [r for j, r in enumerate(rows) if j != best_idx]
                if others:
                    if all(best_price <= parse_price(o.get('price', '')) for o in others):
                        reason_bits.append("lowest price")
                # RAM/Storage advantage (higher is better)
                def parse_number(text: str) -> int:
                    m = re.findall(r"\d+", text or "")
                    return int(m[0]) if m else -1
                best_ram = parse_number(best.get('ram', ''))
                best_storage = parse_number(best.get('storage', ''))
                best_battery = parse_number(best.get('battery', ''))
                best_camera = parse_number(best.get('camera', ''))
                best_driver = parse_number(best.get('driver', ''))
                best_frequency = parse_number(best.get('frequency', ''))
                best_impedance = parse_number(best.get('impedance', ''))
                if others:
                    if best_ram >= 0 and all(best_ram >= parse_number(o.get('ram', '')) for o in others):
                        reason_bits.append("more RAM")
                    if best_storage >= 0 and all(best_storage >= parse_number(o.get('storage', '')) for o in others):
                        reason_bits.append("more storage")
                    if best_battery >= 0 and all(best_battery >= parse_number(o.get('battery', '')) for o in others):
                        reason_bits.append("bigger battery")
                    if best_camera >= 0 and all(best_camera >= parse_number(o.get('camera', '')) for o in others):
                        reason_bits.append("higher MP camera")
                    if best_driver >= 0 and all(best_driver >= parse_number(o.get('driver', '')) for o in others):
                        reason_bits.append("larger driver")
                    if best_frequency >= 0 and all(best_frequency >= parse_number(o.get('frequency', '')) for o in others):
                        reason_bits.append("better frequency response")
                    if best_impedance >= 0 and all(best_impedance >= parse_number(o.get('impedance', '')) for o in others):
                        reason_bits.append("higher impedance")
            # Assemble reason
            if reason_bits:
                if normalized_priorities:
                    best_reason = f"Best for {', '.join(normalized_priorities)} due to {', '.join(reason_bits)}."
                else:
                    best_reason = f"Best overall due to {', '.join(reason_bits)}."
            else:
                best_reason = f"Best matches priorities: {', '.join(normalized_priorities)}" if normalized_priorities else "Best balance of features and price."
        except Exception:
            best_reason = f"Best matches priorities: {', '.join(normalized_priorities)}" if normalized_priorities else "Best balance of features and price."

    return {"features": features, "summary": summary, "highlights": highlights, "headers": headers, "best": best_overall, "best_reason": best_reason}


